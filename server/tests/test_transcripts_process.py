import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def app_lifespan():
    from asgi_lifespan import LifespanManager

    from reflector.app import app

    async with LifespanManager(app) as manager:
        yield manager.app


@pytest.fixture
async def client(app_lifespan):
    yield AsyncClient(
        transport=ASGITransport(app=app_lifespan),
        base_url="http://test/v1",
    )


@pytest.mark.usefixtures("celery_session_app")
@pytest.mark.usefixtures("celery_session_worker")
@pytest.mark.asyncio
async def test_transcript_process(
    tmpdir,
    dummy_llm,
    dummy_processors,
    dummy_file_transcript,
    dummy_file_diarization,
    dummy_storage,
    client,
):
    # create a transcript
    response = await client.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["status"] == "idle"
    tid = response.json()["id"]

    # upload mp3
    response = await client.post(
        f"/transcripts/{tid}/record/upload?chunk_number=0&total_chunks=1",
        files={
            "chunk": (
                "test_short.wav",
                open("tests/records/test_short.wav", "rb"),
                "audio/mpeg",
            ),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # wait for processing to finish (max 1 minute)
    timeout_seconds = 60
    start_time = time.monotonic()
    while (time.monotonic() - start_time) < timeout_seconds:
        # fetch the transcript and check if it is ended
        resp = await client.get(f"/transcripts/{tid}")
        assert resp.status_code == 200
        if resp.json()["status"] in ("ended", "error"):
            break
        await asyncio.sleep(1)
    else:
        pytest.fail(f"Initial processing timed out after {timeout_seconds} seconds")

    # restart the processing
    response = await client.post(
        f"/transcripts/{tid}/process",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    await asyncio.sleep(2)

    # wait for processing to finish (max 1 minute)
    timeout_seconds = 60
    start_time = time.monotonic()
    while (time.monotonic() - start_time) < timeout_seconds:
        # fetch the transcript and check if it is ended
        resp = await client.get(f"/transcripts/{tid}")
        assert resp.status_code == 200
        if resp.json()["status"] in ("ended", "error"):
            break
        await asyncio.sleep(1)
    else:
        pytest.fail(f"Restart processing timed out after {timeout_seconds} seconds")

    # check the transcript is ended
    transcript = resp.json()
    assert transcript["status"] == "ended"
    assert transcript["short_summary"] == "LLM SHORT SUMMARY"
    assert transcript["title"] == "Llm Title"

    # check topics and transcript
    response = await client.get(f"/transcripts/{tid}/topics")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "Hello world. How are you today?" in response.json()[0]["transcript"]
