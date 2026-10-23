"""
Transcript download endpoint — generates a zip archive with all transcript files.
"""

import json
import os
import tempfile
import zipfile
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

import reflector.auth as auth
from reflector.db.meetings import meetings_controller
from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import transcripts_controller
from reflector.logger import logger
from reflector.storage import get_source_storage, get_transcripts_storage

router = APIRouter()


@router.get(
    "/transcripts/{transcript_id}/download/zip",
    operation_id="transcript_download_zip",
)
async def transcript_download_zip(
    transcript_id: str,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    user_id = user["sub"]
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    if not transcripts_controller.user_can_mutate(transcript, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    recording = None
    if transcript.recording_id:
        recording = await recordings_controller.get_by_id(transcript.recording_id)

    meeting = None
    if transcript.meeting_id:
        meeting = await meetings_controller.get_by_id(transcript.meeting_id)

    truncated_id = str(transcript.id).split("-")[0]

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, f"transcript_{truncated_id}.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Transcript audio
            if transcript.audio_location == "storage" and not transcript.audio_deleted:
                try:
                    storage = get_transcripts_storage()
                    data = await storage.get_file(transcript.storage_audio_path)
                    audio_path = os.path.join(tmpdir, "audio.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(data)
                    zf.write(audio_path, "audio.mp3")
                except Exception as e:
                    logger.warning(
                        "Failed to download transcript audio for zip",
                        exc_info=e,
                        transcript_id=transcript.id,
                    )
            elif (
                not transcript.audio_deleted
                and hasattr(transcript, "audio_mp3_filename")
                and transcript.audio_mp3_filename
                and transcript.audio_mp3_filename.exists()
            ):
                zf.write(str(transcript.audio_mp3_filename), "audio.mp3")

            # Recording tracks (multitrack)
            if recording and recording.track_keys:
                try:
                    source_storage = get_source_storage(
                        "daily" if recording.track_keys else None
                    )
                except Exception:
                    source_storage = get_transcripts_storage()

                for i, key in enumerate(recording.track_keys):
                    try:
                        data = await source_storage.get_file(
                            key, bucket=recording.bucket_name
                        )
                        filename = os.path.basename(key) or f"track_{i}"
                        track_path = os.path.join(tmpdir, f"track_{i}")
                        with open(track_path, "wb") as f:
                            f.write(data)
                        zf.write(track_path, f"tracks/{filename}")
                    except Exception as e:
                        logger.warning(
                            "Failed to download track for zip",
                            exc_info=e,
                            track_key=key,
                        )

            # Cloud video
            if meeting and meeting.daily_composed_video_s3_key:
                try:
                    source_storage = get_source_storage("daily")
                    data = await source_storage.get_file(
                        meeting.daily_composed_video_s3_key
                    )
                    video_path = os.path.join(tmpdir, "cloud_video.mp4")
                    with open(video_path, "wb") as f:
                        f.write(data)
                    zf.write(video_path, "cloud_video.mp4")
                except Exception as e:
                    logger.warning(
                        "Failed to download cloud video for zip",
                        exc_info=e,
                        s3_key=meeting.daily_composed_video_s3_key,
                    )

            # Metadata JSON
            metadata = {
                "id": transcript.id,
                "title": transcript.title,
                "created_at": (
                    transcript.created_at.isoformat() if transcript.created_at else None
                ),
                "duration": transcript.duration,
                "source_language": transcript.source_language,
                "target_language": transcript.target_language,
                "short_summary": transcript.short_summary,
                "long_summary": transcript.long_summary,
                "topics": (
                    [t.model_dump() for t in transcript.topics]
                    if transcript.topics
                    else []
                ),
                "participants": (
                    [p.model_dump() for p in transcript.participants]
                    if transcript.participants
                    else []
                ),
                "action_items": transcript.action_items,
                "webvtt": transcript.webvtt,
                "recording_id": transcript.recording_id,
                "meeting_id": transcript.meeting_id,
            }
            meta_path = os.path.join(tmpdir, "metadata.json")
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
            zf.write(meta_path, "metadata.json")

        # Read zip into memory before tmpdir is cleaned up
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

    def iter_zip():
        offset = 0
        chunk_size = 64 * 1024
        while offset < len(zip_bytes):
            yield zip_bytes[offset : offset + chunk_size]
            offset += chunk_size

    return StreamingResponse(
        iter_zip(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=transcript_{truncated_id}.zip"
        },
    )
