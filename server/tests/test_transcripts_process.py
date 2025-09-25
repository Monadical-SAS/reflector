import os

import pytest
from httpx import ASGITransport, AsyncClient

# Set environment for TaskIQ to use InMemoryBroker
os.environ["ENVIRONMENT"] = "pytest"


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


@pytest.fixture
async def taskiq_broker():
    from reflector.worker.app import taskiq_broker

    # Broker is already initialized as InMemoryBroker due to ENVIRONMENT=pytest
    await taskiq_broker.startup()
    yield taskiq_broker
    await taskiq_broker.shutdown()


@pytest.mark.asyncio
async def test_transcript_process(
    tmpdir,
    dummy_llm,
    dummy_processors,
    dummy_file_transcript,
    dummy_file_diarization,
    dummy_storage,
    client,
    taskiq_broker,
    db_session,
):
    print("IN TEST", db_session)
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

    # Wait for all tasks to complete since we're using InMemoryBroker
    await taskiq_broker.wait_all()

    # Ensure it's finished ok
    resp = await client.get(f"/transcripts/{tid}")
    assert resp.status_code == 200
    print(resp.json())
    assert resp.json()["status"] in ("ended", "error")

    # restart the processing
    response = await client.post(
        f"/transcripts/{tid}/process",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Wait for all tasks to complete since we're using InMemoryBroker
    await taskiq_broker.wait_all()

    # Ensure it's finished ok
    resp = await client.get(f"/transcripts/{tid}")
    assert resp.status_code == 200
    print(resp.json())
    assert resp.json()["status"] in ("ended", "error")

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
