import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.usefixtures("setup_database")
@pytest.mark.usefixtures("celery_session_app")
@pytest.mark.usefixtures("celery_session_worker")
@pytest.mark.asyncio
async def test_transcript_process(
    tmpdir,
    dummy_llm,
    dummy_processors,
    dummy_diarization,
    dummy_storage,
):
    from reflector.app import app

    ac = AsyncClient(app=app, base_url="http://test/v1")

    # create a transcript
    response = await ac.post("/transcripts", json={"name": "test"})
    assert response.status_code == 200
    assert response.json()["status"] == "idle"
    tid = response.json()["id"]

    # upload mp3
    response = await ac.post(
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

    # wait for processing to finish
    while True:
        # fetch the transcript and check if it is ended
        resp = await ac.get(f"/transcripts/{tid}")
        assert resp.status_code == 200
        if resp.json()["status"] in ("ended", "error"):
            break
        await asyncio.sleep(1)

    # restart the processing
    response = await ac.post(
        f"/transcripts/{tid}/process",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # wait for processing to finish
    while True:
        # fetch the transcript and check if it is ended
        resp = await ac.get(f"/transcripts/{tid}")
        assert resp.status_code == 200
        if resp.json()["status"] in ("ended", "error"):
            break
        await asyncio.sleep(1)

    # check the transcript is ended
    transcript = resp.json()
    assert transcript["status"] == "ended"
    assert transcript["short_summary"] == "LLM SHORT SUMMARY"
    assert transcript["title"] == "LLM Title"

    # check topics and transcript
    response = await ac.get(f"/transcripts/{tid}/topics")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "want to share" in response.json()[0]["transcript"]
