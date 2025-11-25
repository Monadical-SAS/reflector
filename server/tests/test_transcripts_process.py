import asyncio
import time
from unittest.mock import patch

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


@pytest.mark.usefixtures("setup_database")
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


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_whereby_recording_uses_file_pipeline(client):
    """Test that Whereby recordings (bucket_name but no track_keys) use file pipeline"""
    from datetime import datetime, timezone

    from reflector.db.recordings import Recording, recordings_controller
    from reflector.db.transcripts import transcripts_controller

    # Create transcript with Whereby recording (has bucket_name, no track_keys)
    transcript = await transcripts_controller.add(
        "",
        source_kind="room",
        source_language="en",
        target_language="en",
        user_id="test-user",
        share_mode="public",
    )

    recording = await recordings_controller.create(
        Recording(
            bucket_name="whereby-bucket",
            object_key="test-recording.mp4",  # gitleaks:allow
            meeting_id="test-meeting",
            recorded_at=datetime.now(timezone.utc),
            track_keys=None,  # Whereby recordings have no track_keys
        )
    )

    await transcripts_controller.update(
        transcript, {"recording_id": recording.id, "status": "uploaded"}
    )

    with (
        patch(
            "reflector.views.transcripts_process.task_pipeline_file_process"
        ) as mock_file_pipeline,
        patch(
            "reflector.views.transcripts_process.task_pipeline_multitrack_process"
        ) as mock_multitrack_pipeline,
    ):
        response = await client.post(f"/transcripts/{transcript.id}/process")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Whereby recordings should use file pipeline
        mock_file_pipeline.delay.assert_called_once_with(transcript_id=transcript.id)
        mock_multitrack_pipeline.delay.assert_not_called()


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_dailyco_recording_uses_multitrack_pipeline(client):
    """Test that Daily.co recordings (bucket_name + track_keys) use multitrack pipeline"""
    from datetime import datetime, timezone

    from reflector.db.recordings import Recording, recordings_controller
    from reflector.db.transcripts import transcripts_controller

    # Create transcript with Daily.co multitrack recording
    transcript = await transcripts_controller.add(
        "",
        source_kind="room",
        source_language="en",
        target_language="en",
        user_id="test-user",
        share_mode="public",
    )

    track_keys = [
        "recordings/test-room/track1.webm",
        "recordings/test-room/track2.webm",
    ]
    recording = await recordings_controller.create(
        Recording(
            bucket_name="daily-bucket",
            object_key="recordings/test-room",
            meeting_id="test-meeting",
            track_keys=track_keys,
            recorded_at=datetime.now(timezone.utc),
        )
    )

    await transcripts_controller.update(
        transcript, {"recording_id": recording.id, "status": "uploaded"}
    )

    with (
        patch(
            "reflector.views.transcripts_process.task_pipeline_file_process"
        ) as mock_file_pipeline,
        patch(
            "reflector.views.transcripts_process.task_pipeline_multitrack_process"
        ) as mock_multitrack_pipeline,
    ):
        response = await client.post(f"/transcripts/{transcript.id}/process")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Daily.co multitrack recordings should use multitrack pipeline
        mock_multitrack_pipeline.delay.assert_called_once_with(
            transcript_id=transcript.id,
            bucket_name="daily-bucket",
            track_keys=track_keys,
        )
        mock_file_pipeline.delay.assert_not_called()
