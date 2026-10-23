"""
Transcript downloads: list of files with direct links, and a streamed zip.
"""

import asyncio
import json
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, AsyncIterator, Literal, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.meetings import Meeting, meetings_controller
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.transcripts import Transcript, transcripts_controller
from reflector.logger import logger
from reflector.settings import settings
from reflector.storage import get_source_storage, get_transcripts_storage
from reflector.storage.base import Storage
from reflector.utils.daily import parse_daily_track_filename
from reflector.utils.livekit import parse_livekit_track_filepath
from reflector.utils.transcript_formats import (
    topics_to_webvtt_named,
    transcript_to_text,
)

router = APIRouter()

TOKEN_AUDIENCE = "transcript-download"
TOKEN_ALGORITHM = "HS256"
LINK_EXPIRES = timedelta(minutes=15)
LOCAL_CHUNK_SIZE = 1024 * 1024

DAILY_TRACK_LABELS = {
    "cam-audio": "Camera audio",
    "cam-video": "Camera video",
    "screen-audio": "Screen audio",
    "screen-video": "Screen video",
}
LIVEKIT_TRACK_LABELS = {".ogg": "Audio", ".webm": "Video"}

EntryKind = Literal["text", "subtitles", "summary", "audio", "cloud_video", "track"]


class DownloadEntry(BaseModel):
    id: str
    kind: EntryKind
    label: str
    participant_name: str | None = None
    filename: str
    size: int | None = None
    url: str


class TranscriptDownloads(BaseModel):
    entries: list[DownloadEntry]
    zip_url: str


@dataclass
class _Source:
    id: str
    kind: EntryKind
    label: str
    filename: str
    zip_path: str
    participant_name: str | None = None
    size: int | None = None
    storage: Storage | None = None
    key: str | None = None
    bucket: str | None = None
    local_path: Path | None = None
    content: bytes | None = None
    media_type: str = "application/octet-stream"
    sort_key: tuple = ()

    def __post_init__(self):
        if self.content is not None:
            self.size = len(self.content)


def _create_token(transcript_id: str, user_id: str | None) -> str:
    payload = {
        "aud": TOKEN_AUDIENCE,
        "tid": transcript_id,
        "uid": user_id,
        "exp": datetime.now(timezone.utc) + LINK_EXPIRES,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=TOKEN_ALGORITHM)


def _read_token(token: str, transcript_id: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[TOKEN_ALGORITHM],
            audience=TOKEN_AUDIENCE,
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("tid") != transcript_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload.get("uid")


def _summary(transcript: Transcript, is_member: bool) -> dict:
    topics = []
    for topic in transcript.topics or []:
        item = {
            "title": topic.title,
            "summary": topic.summary,
            "timestamp": topic.timestamp,
            "duration": topic.duration,
            "transcript": topic.transcript,
        }
        if is_member:
            item = {"id": topic.id, **item}
        topics.append(item)

    participants = []
    for participant in transcript.participants or []:
        item = {"speaker": participant.speaker, "name": participant.name}
        if is_member:
            item = {"id": participant.id, "user_id": participant.user_id, **item}
        participants.append(item)

    data = {
        "title": transcript.title,
        "created_at": (
            transcript.created_at.isoformat() if transcript.created_at else None
        ),
        "duration": transcript.duration,
        "source_language": transcript.source_language,
        "target_language": transcript.target_language,
        "short_summary": transcript.short_summary,
        "long_summary": transcript.long_summary,
        "action_items": transcript.action_items,
        "topics": topics,
        "participants": participants,
    }
    if is_member:
        data = {
            "id": transcript.id,
            "recording_id": transcript.recording_id,
            "meeting_id": transcript.meeting_id,
            "room_id": transcript.room_id,
            **data,
        }
    return data


async def _object_size(storage: Storage, key: str, bucket: str | None) -> int | None:
    try:
        objects = await storage.list_objects_with_size(key, bucket=bucket)
    except Exception as e:
        logger.warning("Failed to read object size", exc_info=e, key=key)
        return None
    return next((size for k, size in objects if k == key), None)


def _recording_platform(recording: Recording, meeting: Meeting | None) -> str:
    if meeting:
        return meeting.platform
    return "livekit" if recording.object_key.startswith("livekit/") else "daily"


async def _track_sources(
    transcript: Transcript, recording: Recording, platform: str
) -> list[_Source]:
    storage = get_source_storage(platform)
    bucket = recording.bucket_name or None
    prefix = os.path.dirname(recording.track_keys[0]) + "/"
    try:
        objects = await storage.list_objects_with_size(prefix, bucket=bucket)
    except Exception as e:
        logger.warning("Failed to list recording tracks", exc_info=e, prefix=prefix)
        return []

    participants = {p.id: p for p in transcript.participants or []}
    recording_start_ts = None
    if platform != "livekit":
        try:
            recording_start_ts = parse_daily_track_filename(
                recording.track_keys[0]
            ).recording_start_ts
        except ValueError:
            pass

    sources = []
    for key, size in objects:
        basename = os.path.basename(key)
        ext = os.path.splitext(basename)[1]
        if platform == "livekit":
            label = LIVEKIT_TRACK_LABELS.get(ext)
            if not label:
                continue
            type_order = list(LIVEKIT_TRACK_LABELS).index(ext)
            try:
                participant_id = parse_livekit_track_filepath(key).participant_identity
            except ValueError:
                participant_id = None
        else:
            try:
                parsed = parse_daily_track_filename(key)
            except ValueError:
                continue
            if recording_start_ts and parsed.recording_start_ts != recording_start_ts:
                continue
            label = DAILY_TRACK_LABELS[parsed.track_type]
            type_order = list(DAILY_TRACK_LABELS).index(parsed.track_type)
            participant_id = parsed.participant_id

        participant = participants.get(participant_id)
        filename = basename if ext else f"{basename}.webm"
        sources.append(
            _Source(
                id=f"track-{basename}",
                kind="track",
                label=label,
                filename=filename,
                zip_path=f"tracks/{filename}",
                participant_name=participant.name if participant else None,
                size=size,
                storage=storage,
                key=key,
                bucket=bucket,
                sort_key=(
                    participant is None,
                    participant.speaker if participant else 0,
                    participant_id or "",
                    type_order,
                    basename,
                ),
            )
        )
    return sorted(sources, key=lambda s: s.sort_key)


async def _collect_sources(transcript: Transcript, is_member: bool) -> list[_Source]:
    recording = None
    if transcript.recording_id:
        recording = await recordings_controller.get_by_id(transcript.recording_id)
    is_multitrack = recording is not None and recording.is_multitrack

    sources = []
    if transcript.topics:
        sources.append(
            _Source(
                id="text",
                kind="text",
                label="Transcript text",
                filename="transcript.txt",
                zip_path="transcript.txt",
                content=transcript_to_text(
                    transcript.topics, transcript.participants, is_multitrack
                ).encode(),
                media_type="text/plain; charset=utf-8",
            )
        )
        sources.append(
            _Source(
                id="subtitles",
                kind="subtitles",
                label="Subtitles",
                filename="subtitles.vtt",
                zip_path="subtitles.vtt",
                content=topics_to_webvtt_named(
                    transcript.topics, transcript.participants, is_multitrack
                ).encode(),
                media_type="text/vtt; charset=utf-8",
            )
        )
    sources.append(
        _Source(
            id="summary",
            kind="summary",
            label="Summary and topics",
            filename="summary.json",
            zip_path="summary.json",
            content=json.dumps(
                _summary(transcript, is_member), indent=2, default=str
            ).encode(),
            media_type="application/json",
        )
    )

    if not transcript.audio_deleted:
        audio = _Source(
            id="audio",
            kind="audio",
            label="Mixed audio",
            filename="audio.mp3",
            zip_path="audio.mp3",
            media_type="audio/mpeg",
        )
        if transcript.audio_location == "storage":
            audio.storage = get_transcripts_storage()
            audio.key = transcript.storage_audio_path
            audio.size = await _object_size(audio.storage, audio.key, None)
            sources.append(audio)
        elif transcript.audio_mp3_filename.exists():
            audio.local_path = transcript.audio_mp3_filename
            audio.size = audio.local_path.stat().st_size
            sources.append(audio)

    if not is_member:
        return sources

    meeting = None
    if transcript.meeting_id:
        meeting = await meetings_controller.get_by_id(transcript.meeting_id)

    if meeting and meeting.daily_composed_video_s3_key:
        storage = get_source_storage("daily")
        key = meeting.daily_composed_video_s3_key
        sources.append(
            _Source(
                id="cloud_video",
                kind="cloud_video",
                label="Cloud video (composed)",
                filename="cloud_video.mp4",
                zip_path="cloud_video.mp4",
                size=await _object_size(storage, key, None),
                storage=storage,
                key=key,
                media_type="video/mp4",
            )
        )

    if recording and recording.track_keys:
        platform = _recording_platform(recording, meeting)
        sources.extend(await _track_sources(transcript, recording, platform))

    return sources


async def _source_url(
    request: Request, transcript_id: str, source: _Source, token: str
) -> str:
    if source.storage is not None:
        return await source.storage.get_file_url(
            source.key,
            operation="get_object",
            expires_in=int(LINK_EXPIRES.total_seconds()),
            bucket=source.bucket,
            extra_params={
                "ResponseContentDisposition": (
                    f'attachment; filename="{source.filename}"'
                ),
            },
        )
    path = request.app.url_path_for(
        "transcript_download_file", transcript_id=transcript_id, entry_id=source.id
    )
    return f"{path}?token={token}"


async def _load_with_token(
    transcript_id: str, token: str
) -> tuple[Transcript, list[_Source]]:
    user_id = _read_token(token, transcript_id)
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    sources = await _collect_sources(transcript, is_member=user_id is not None)
    return transcript, sources


async def _read_local(path: Path) -> AsyncIterator[bytes]:
    with open(path, "rb") as f:
        while chunk := await asyncio.to_thread(f.read, LOCAL_CHUNK_SIZE):
            yield chunk


async def _read_content(content: bytes) -> AsyncIterator[bytes]:
    yield content


def _read_source(source: _Source) -> AsyncIterator[bytes]:
    if source.content is not None:
        return _read_content(source.content)
    if source.local_path is not None:
        return _read_local(source.local_path)
    return source.storage.iter_file(source.key, bucket=source.bucket)


class _ZipOutput:
    """Non-seekable sink, so zipfile writes data descriptors after each member."""

    def __init__(self):
        self._chunks: list[bytes] = []

    def write(self, data) -> int:
        self._chunks.append(bytes(data))
        return len(data)

    def flush(self):
        pass

    def drain(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


async def stream_zip(
    members: list[tuple[str, AsyncIterator[bytes]]],
) -> AsyncIterator[bytes]:
    output = _ZipOutput()
    zf = zipfile.ZipFile(output, "w", zipfile.ZIP_STORED, allowZip64=True)
    date_time = datetime.now().timetuple()[:6]
    for name, chunks in members:
        info = zipfile.ZipInfo(name, date_time=date_time)
        info.compress_type = zipfile.ZIP_STORED
        with zf.open(info, "w", force_zip64=True) as member:
            async for chunk in chunks:
                member.write(chunk)
                if data := output.drain():
                    yield data
        if data := output.drain():
            yield data
    zf.close()
    yield output.drain()


@router.get(
    "/transcripts/{transcript_id}/downloads",
    operation_id="transcript_get_downloads",
    response_model=TranscriptDownloads,
)
async def transcript_get_downloads(
    request: Request,
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    sources = await _collect_sources(transcript, is_member=user_id is not None)
    token = _create_token(transcript.id, user_id)

    entries = [
        DownloadEntry(
            id=source.id,
            kind=source.kind,
            label=source.label,
            participant_name=source.participant_name,
            filename=source.filename,
            size=source.size,
            url=await _source_url(request, transcript.id, source, token),
        )
        for source in sources
    ]
    zip_path = request.app.url_path_for(
        "transcript_download_zip", transcript_id=transcript.id
    )
    return TranscriptDownloads(entries=entries, zip_url=f"{zip_path}?token={token}")


@router.get(
    "/transcripts/{transcript_id}/download/file/{entry_id}",
    operation_id="transcript_download_file",
)
async def transcript_download_file(
    request: Request, transcript_id: str, entry_id: str, token: str
):
    _, sources = await _load_with_token(transcript_id, token)
    source = next((s for s in sources if s.id == entry_id), None)
    if source is None:
        raise HTTPException(status_code=404, detail="File not found")

    if source.content is not None:
        return Response(
            content=source.content,
            media_type=source.media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{source.filename}"'
            },
        )
    if source.local_path is not None:
        return FileResponse(
            source.local_path, media_type=source.media_type, filename=source.filename
        )
    return RedirectResponse(await _source_url(request, transcript_id, source, token))


@router.get(
    "/transcripts/{transcript_id}/download/zip",
    operation_id="transcript_download_zip",
)
async def transcript_download_zip(
    transcript_id: str,
    token: str,
    ids: Annotated[list[str], Query(min_length=1)],
):
    transcript, sources = await _load_with_token(transcript_id, token)
    by_id = {s.id: s for s in sources}
    if any(entry_id not in by_id for entry_id in ids):
        raise HTTPException(status_code=403, detail="File not available")

    wanted = set(ids)
    members = [(s.zip_path, _read_source(s)) for s in sources if s.id in wanted]

    async def body():
        try:
            async for chunk in stream_zip(members):
                yield chunk
        except Exception as e:
            logger.error("Zip stream failed", exc_info=e, transcript_id=transcript.id)
            raise

    truncated_id = str(transcript.id).split("-")[0]
    return StreamingResponse(
        body(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="transcript_{truncated_id}.zip"'
            )
        },
    )
