import shutil
from pathlib import Path

import pytest


@pytest.fixture
async def fake_transcript(tmpdir, client):
    from reflector.settings import settings
    from reflector.views.transcripts import transcripts_controller

    settings.DATA_DIR = Path(tmpdir)

    # create a transcript
    response = await client.post("/transcripts", json={"name": "Test audio download"})
    assert response.status_code == 200
    tid = response.json()["id"]

    transcript = await transcripts_controller.get_by_id(tid)
    assert transcript is not None

    await transcripts_controller.update(transcript, {"status": "ended"})

    # manually copy a file at the expected location
    audio_filename = transcript.audio_mp3_filename
    path = Path(__file__).parent / "records" / "test_mathieu_hello.mp3"
    audio_filename.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, audio_filename)
    yield transcript


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url_suffix,content_type",
    [
        ["/mp3", "audio/mpeg"],
    ],
)
async def test_transcript_audio_download(
    fake_transcript, url_suffix, content_type, client
):
    response = await client.get(f"/transcripts/{fake_transcript.id}/audio{url_suffix}")
    assert response.status_code == 200
    assert response.headers["content-type"] == content_type

    # test get 404
    response = await client.get(
        f"/transcripts/{fake_transcript.id}XXX/audio{url_suffix}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url_suffix,content_type",
    [
        ["/mp3", "audio/mpeg"],
    ],
)
async def test_transcript_audio_download_head(
    fake_transcript, url_suffix, content_type, client
):
    response = await client.head(f"/transcripts/{fake_transcript.id}/audio{url_suffix}")
    assert response.status_code == 200
    assert response.headers["content-type"] == content_type

    # test head 404
    response = await client.head(
        f"/transcripts/{fake_transcript.id}XXX/audio{url_suffix}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url_suffix,content_type",
    [
        ["/mp3", "audio/mpeg"],
    ],
)
async def test_transcript_audio_download_range(
    fake_transcript, url_suffix, content_type, client
):
    response = await client.get(
        f"/transcripts/{fake_transcript.id}/audio{url_suffix}",
        headers={"range": "bytes=0-100"},
    )
    assert response.status_code == 206
    assert response.headers["content-type"] == content_type
    assert response.headers["content-range"].startswith("bytes 0-100/")
    assert response.headers["content-length"] == "101"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url_suffix,content_type",
    [
        ["/mp3", "audio/mpeg"],
    ],
)
async def test_transcript_audio_download_range_with_seek(
    fake_transcript, url_suffix, content_type, client
):
    response = await client.get(
        f"/transcripts/{fake_transcript.id}/audio{url_suffix}",
        headers={"range": "bytes=100-"},
    )
    assert response.status_code == 206
    assert response.headers["content-type"] == content_type
    assert response.headers["content-range"].startswith("bytes 100-")


@pytest.mark.asyncio
async def test_transcript_delete_with_audio(fake_transcript, client):
    response = await client.delete(f"/transcripts/{fake_transcript.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    response = await client.get(f"/transcripts/{fake_transcript.id}")
    assert response.status_code == 404
