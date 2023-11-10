import pytest
import shutil
from httpx import AsyncClient
from pathlib import Path


@pytest.fixture
async def fake_transcript(tmpdir):
    from reflector.settings import settings
    from reflector.app import app
    from reflector.views.transcripts import transcripts_controller

    settings.DATA_DIR = Path(tmpdir)

    # create a transcript
    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.post("/transcripts", json={"name": "Test audio download"})
    assert response.status_code == 200
    tid = response.json()["id"]

    transcript = await transcripts_controller.get_by_id(tid)
    assert transcript is not None

    await transcripts_controller.update(transcript, {"status": "finished"})

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
async def test_transcript_audio_download(fake_transcript, url_suffix, content_type):
    from reflector.app import app

    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.get(f"/transcripts/{fake_transcript.id}/audio{url_suffix}")
    assert response.status_code == 200
    assert response.headers["content-type"] == content_type

    # test get 404
    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.get(f"/transcripts/{fake_transcript.id}XXX/audio{url_suffix}")
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url_suffix,content_type",
    [
        ["/mp3", "audio/mpeg"],
    ],
)
async def test_transcript_audio_download_head(
    fake_transcript, url_suffix, content_type
):
    from reflector.app import app

    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.head(f"/transcripts/{fake_transcript.id}/audio{url_suffix}")
    assert response.status_code == 200
    assert response.headers["content-type"] == content_type

    # test head 404
    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.head(f"/transcripts/{fake_transcript.id}XXX/audio{url_suffix}")
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url_suffix,content_type",
    [
        ["/mp3", "audio/mpeg"],
    ],
)
async def test_transcript_audio_download_range(
    fake_transcript, url_suffix, content_type
):
    from reflector.app import app

    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.get(
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
    fake_transcript, url_suffix, content_type
):
    from reflector.app import app

    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.get(
        f"/transcripts/{fake_transcript.id}/audio{url_suffix}",
        headers={"range": "bytes=100-"},
    )
    assert response.status_code == 206
    assert response.headers["content-type"] == content_type
    assert response.headers["content-range"].startswith("bytes 100-")


@pytest.mark.asyncio
async def test_transcript_audio_download_waveform(fake_transcript):
    from reflector.app import app

    ac = AsyncClient(app=app, base_url="http://test/v1")
    response = await ac.get(f"/transcripts/{fake_transcript.id}/audio/waveform")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert isinstance(response.json()["data"], list)
    assert len(response.json()["data"]) >= 255
