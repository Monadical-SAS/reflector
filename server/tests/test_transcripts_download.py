import io
import zipfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import jwt
import pytest

from reflector.db import get_database
from reflector.db.meetings import meetings
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.transcripts import (
    SourceKind,
    TranscriptParticipant,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Word
from reflector.settings import settings
from reflector.storage.base import Storage
from reflector.views.transcripts_download import stream_zip

ALICE = "12f0b87c-97d4-4dd3-a65c-cee1f854a79c"
BOB = "5a1d6e2b-0c3f-4b8e-9a7d-2e4f6b8c0d1e"
REC_TS = "1763152299562"
OTHER_REC_TS = "1763159999999"
FOLDER = "domain/room-20251114"
CLOUD_VIDEO_KEY = "domain/cloud/video.mp4"


def _track(participant, track_type, rec_ts=REC_TS):
    return f"{FOLDER}/{rec_ts}-{participant}-{track_type}-1763152314582"


class FakeStorage(Storage):
    def __init__(self, objects):
        super().__init__()
        self.objects = objects
        self.presigned = []

    async def _list_objects_with_size(self, prefix="", *, bucket=None):
        return [(k, len(v)) for k, v in self.objects.items() if k.startswith(prefix)]

    async def _get_file_url(
        self,
        filename,
        operation="get_object",
        expires_in=3600,
        *,
        bucket=None,
        extra_params=None,
    ):
        self.presigned.append((filename, bucket, extra_params))
        return f"https://s3.test/{bucket}/{filename}?signature=x"

    async def _iter_file(self, filename, *, bucket=None):
        data = self.objects[filename]
        for i in range(0, len(data), 4):
            yield data[i : i + 4]


@pytest.fixture
def source_storage():
    storage = FakeStorage(
        {
            _track(ALICE, "cam-audio"): b"alice-audio",
            _track(ALICE, "cam-video"): b"alice-video",
            _track(ALICE, "screen-video"): b"alice-screen",
            _track(BOB, "cam-audio"): b"bob-audio",
            _track(BOB, "cam-audio", OTHER_REC_TS): b"other-recording",
            f"{FOLDER}/manifest.json": b"{}",
            CLOUD_VIDEO_KEY: b"cloud-video",
        }
    )
    with patch(
        "reflector.views.transcripts_download.get_source_storage",
        return_value=storage,
    ):
        yield storage


@pytest.fixture
def transcripts_storage():
    storage = FakeStorage({})
    with patch(
        "reflector.views.transcripts_download.get_transcripts_storage",
        return_value=storage,
    ):
        yield storage


async def _add_topic(transcript):
    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Topic 1",
            summary="Topic 1 summary",
            timestamp=0,
            transcript="Hello world",
            words=[
                Word(text="Hello", start=0, end=1, speaker=0),
                Word(text=" world", start=1, end=2, speaker=0),
            ],
        ),
    )


async def _room_transcript(share_mode="semi-private", user_id="randomuserid"):
    meeting_id = "meeting-download-test"
    now = datetime.now(timezone.utc)
    await get_database().execute(
        meetings.insert().values(
            id=meeting_id,
            room_name="room-20251114",
            room_url="https://example.com/room",
            host_room_url="https://example.com/room-host",
            start_date=now,
            end_date=now + timedelta(hours=1),
            platform="daily",
            daily_composed_video_s3_key=CLOUD_VIDEO_KEY,
        )
    )
    recording = await recordings_controller.create(
        Recording(
            bucket_name="daily-bucket",
            object_key=FOLDER,
            recorded_at=now,
            meeting_id=meeting_id,
            track_keys=[_track(ALICE, "cam-audio"), _track(BOB, "cam-audio")],
        )
    )
    transcript = await transcripts_controller.add(
        name="Room meeting",
        source_kind=SourceKind.ROOM,
        user_id=user_id,
        share_mode=share_mode,
        recording_id=recording.id,
        meeting_id=meeting_id,
    )
    await transcripts_controller.update(
        transcript,
        {"audio_location": "storage", "short_summary": "Short", "title": "Weekly"},
    )
    await transcripts_controller.upsert_participant(
        transcript, TranscriptParticipant(id=ALICE, speaker=0, name="Alice")
    )
    await transcripts_controller.upsert_participant(
        transcript,
        TranscriptParticipant(id=BOB, speaker=1, name="Bob", user_id="bob-user"),
    )
    await _add_topic(transcript)
    return await transcripts_controller.get_by_id(transcript.id)


def _by_kind(entries, kind):
    return [e for e in entries if e["kind"] == kind]


def _token(url):
    return parse_qs(urlparse(url).query)["token"][0]


async def _get_downloads(client, transcript):
    response = await client.get(f"/transcripts/{transcript.id}/downloads")
    assert response.status_code == 200, response.text
    return response.json()


async def _download(client, url):
    parsed = urlparse(url)
    path = parsed.path.removeprefix("/v1")
    return await client.get(f"{path}?{parsed.query}")


@pytest.mark.asyncio
async def test_downloads_member_lists_everything(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    data = await _get_downloads(client, transcript)
    entries = data["entries"]

    assert [e["kind"] for e in entries[:5]] == [
        "text",
        "subtitles",
        "summary",
        "audio",
        "cloud_video",
    ]
    tracks = _by_kind(entries, "track")
    assert [(t["participant_name"], t["label"], t["size"]) for t in tracks] == [
        ("Alice", "Camera audio", len(b"alice-audio")),
        ("Alice", "Camera video", len(b"alice-video")),
        ("Alice", "Screen video", len(b"alice-screen")),
        ("Bob", "Camera audio", len(b"bob-audio")),
    ]
    assert all(t["filename"].endswith(".webm") for t in tracks)
    assert _by_kind(entries, "cloud_video")[0]["size"] == len(b"cloud-video")

    presigned_keys = {key for key, _, _ in source_storage.presigned}
    assert _track(ALICE, "screen-video") in presigned_keys
    assert f"{FOLDER}/manifest.json" not in presigned_keys
    assert _track(BOB, "cam-audio", OTHER_REC_TS) not in presigned_keys
    for _, _, extra in source_storage.presigned:
        assert extra["ResponseContentDisposition"].startswith("attachment")

    assert _token(data["zip_url"])


@pytest.mark.asyncio
async def test_downloads_guest_on_public_gets_reduced_list(
    client, source_storage, transcripts_storage
):
    transcript = await _room_transcript(share_mode="public")
    data = await _get_downloads(client, transcript)

    assert [e["kind"] for e in data["entries"]] == [
        "text",
        "subtitles",
        "summary",
        "audio",
    ]
    body = str(data)
    for secret in (ALICE, BOB, transcript.recording_id, transcript.meeting_id, FOLDER):
        assert secret not in body
    assert source_storage.presigned == []


@pytest.mark.asyncio
async def test_downloads_guest_on_semi_private_forbidden(
    client, source_storage, transcripts_storage
):
    transcript = await _room_transcript(share_mode="semi-private")
    response = await client.get(f"/transcripts/{transcript.id}/downloads")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_downloads_private_non_owner_forbidden(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript(share_mode="private")
    response = await client.get(f"/transcripts/{transcript.id}/downloads")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_downloads_file_upload_lists_audio_only(
    authenticated_client, client, fake_transcript_with_topics
):
    data = await _get_downloads(client, fake_transcript_with_topics)
    assert [e["kind"] for e in data["entries"]] == [
        "text",
        "subtitles",
        "summary",
        "audio",
    ]
    audio = await _download(client, _by_kind(data["entries"], "audio")[0]["url"])
    assert audio.status_code == 200
    assert audio.headers["content-disposition"].startswith("attachment")


@pytest.mark.asyncio
async def test_downloads_hides_deleted_audio(
    authenticated_client, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    await transcripts_controller.update(transcript, {"audio_deleted": True})
    data = await _get_downloads(client, transcript)
    assert _by_kind(data["entries"], "audio") == []


def _collect_keys(value, keys):
    if isinstance(value, dict):
        for k, v in value.items():
            keys.add(k)
            _collect_keys(v, keys)
    elif isinstance(value, list):
        for v in value:
            _collect_keys(v, keys)
    return keys


ID_FIELDS = {"id", "user_id", "recording_id", "meeting_id", "room_id"}


@pytest.mark.asyncio
async def test_summary_for_guest_has_no_ids(
    client, source_storage, transcripts_storage
):
    transcript = await _room_transcript(share_mode="public")
    data = await _get_downloads(client, transcript)
    response = await _download(client, _by_kind(data["entries"], "summary")[0]["url"])

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment")
    summary = response.json()
    assert summary["title"] == "Weekly"
    assert [p["name"] for p in summary["participants"]] == ["Alice", "Bob"]
    assert _collect_keys(summary, set()) & ID_FIELDS == set()


@pytest.mark.asyncio
async def test_summary_for_member_has_ids(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    data = await _get_downloads(client, transcript)
    response = await _download(client, _by_kind(data["entries"], "summary")[0]["url"])

    summary = response.json()
    assert summary["id"] == transcript.id
    assert summary["recording_id"] == transcript.recording_id
    assert summary["meeting_id"] == transcript.meeting_id
    assert summary["participants"][1]["user_id"] == "bob-user"


@pytest.mark.asyncio
async def test_text_and_subtitles_download(client, source_storage, transcripts_storage):
    transcript = await _room_transcript(share_mode="public")
    data = await _get_downloads(client, transcript)

    text = await _download(client, _by_kind(data["entries"], "text")[0]["url"])
    assert text.status_code == 200
    assert "Hello world" in text.text
    assert text.headers["content-disposition"].startswith("attachment")

    vtt = await _download(client, _by_kind(data["entries"], "subtitles")[0]["url"])
    assert vtt.status_code == 200
    assert vtt.text.startswith("WEBVTT")


@pytest.mark.asyncio
async def test_file_download_rejects_bad_token(
    client, source_storage, transcripts_storage
):
    transcript = await _room_transcript(share_mode="public")
    response = await client.get(
        f"/transcripts/{transcript.id}/download/file/text?token=garbage"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_file_download_rejects_token_for_other_transcript(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    other = await transcripts_controller.add(
        name="Other",
        source_kind=SourceKind.FILE,
        user_id="randomuserid2",
        share_mode="private",
    )
    data = await _get_downloads(client, transcript)
    token = _token(data["zip_url"])
    response = await client.get(
        f"/transcripts/{other.id}/download/file/text?token={token}"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_download_token_is_not_a_login_token(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    data = await _get_downloads(client, transcript)
    payload = jwt.decode(_token(data["zip_url"]), options={"verify_signature": False})
    assert "sub" not in payload
    assert payload["aud"] == "transcript-download"


def _zip_url(data, *ids):
    return data["zip_url"] + "".join(f"&ids={i}" for i in ids)


def _entry_id(entries, kind, label, participant):
    for e in entries:
        if (
            e["kind"] == kind
            and e["label"] == label
            and e["participant_name"] == participant
        ):
            return e["id"]
    raise AssertionError(f"no entry {kind} {label} {participant}")


@pytest.mark.asyncio
async def test_zip_contains_selected_files(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    data = await _get_downloads(client, transcript)
    screen = _entry_id(data["entries"], "track", "Screen video", "Alice")

    response = await _download(client, _zip_url(data, "summary", "cloud_video", screen))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"].startswith("attachment")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert names[0] == "summary.json"
        assert zf.read("cloud_video.mp4") == b"cloud-video"
        track_names = [n for n in names if n.startswith("tracks/")]
        assert len(track_names) == 1
        assert zf.read(track_names[0]) == b"alice-screen"


@pytest.mark.asyncio
async def test_zip_guest_cannot_request_track(
    client, source_storage, transcripts_storage
):
    transcript = await _room_transcript(share_mode="public")
    data = await _get_downloads(client, transcript)
    track_id = "track-" + _track(ALICE, "cam-audio").rsplit("/", 1)[1]
    response = await _download(client, _zip_url(data, "summary", track_id))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_zip_rejects_unknown_id(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    data = await _get_downloads(client, transcript)
    response = await _download(client, _zip_url(data, "summary", "nope"))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_zip_requires_ids(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    data = await _get_downloads(client, transcript)
    response = await _download(client, data["zip_url"])
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_zip_rejects_expired_token(
    authenticated_client2, client, source_storage, transcripts_storage
):
    transcript = await _room_transcript()
    token = jwt.encode(
        {
            "aud": "transcript-download",
            "tid": transcript.id,
            "uid": "randomuserid2",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    response = await client.get(
        f"/transcripts/{transcript.id}/download/zip?token={token}&ids=summary"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stream_zip_yields_before_reading_next_member():
    second_started = False

    async def first():
        for _ in range(4):
            yield b"x" * 100_000

    async def second():
        nonlocal second_started
        second_started = True
        yield b"y"

    stream = stream_zip([("a.bin", first()), ("b.bin", second())])
    chunk = await anext(stream)

    assert chunk
    assert second_started is False

    rest = [c async for c in stream]
    with zipfile.ZipFile(io.BytesIO(chunk + b"".join(rest))) as zf:
        assert zf.testzip() is None
        assert zf.read("a.bin") == b"x" * 400_000
        assert zf.read("b.bin") == b"y"
