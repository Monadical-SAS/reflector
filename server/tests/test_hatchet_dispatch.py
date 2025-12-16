"""
Tests for Hatchet workflow dispatch and routing logic.

These tests verify:
1. Routing to Hatchet when HATCHET_ENABLED=True
2. Replay logic for failed workflows
3. Force flag to cancel and restart
4. Validation prevents concurrent workflows
"""

from unittest.mock import AsyncMock, patch

import pytest

from reflector.db.transcripts import Transcript


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_hatchet_validation_blocks_running_workflow():
    """Test that validation blocks reprocessing when workflow is running."""
    from reflector.services.transcript_process import (
        ValidationAlreadyScheduled,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="processing",
        source_kind="room",
        workflow_run_id="running-workflow-123",
    )

    with patch("reflector.services.transcript_process.settings") as mock_settings:
        mock_settings.HATCHET_ENABLED = True

        with patch("reflector.hatchet.client.HatchetClientManager") as mock_hatchet:
            mock_hatchet.get_workflow_run_status = AsyncMock(return_value="RUNNING")

            with patch(
                "reflector.services.transcript_process.task_is_scheduled_or_active"
            ) as mock_celery_check:
                mock_celery_check.return_value = False

                result = await validate_transcript_for_processing(mock_transcript)

            assert isinstance(result, ValidationAlreadyScheduled)
            assert "running" in result.detail.lower()


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_hatchet_validation_blocks_queued_workflow():
    """Test that validation blocks reprocessing when workflow is queued."""
    from reflector.services.transcript_process import (
        ValidationAlreadyScheduled,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="processing",
        source_kind="room",
        workflow_run_id="queued-workflow-123",
    )

    with patch("reflector.services.transcript_process.settings") as mock_settings:
        mock_settings.HATCHET_ENABLED = True

        with patch("reflector.hatchet.client.HatchetClientManager") as mock_hatchet:
            mock_hatchet.get_workflow_run_status = AsyncMock(return_value="QUEUED")

            with patch(
                "reflector.services.transcript_process.task_is_scheduled_or_active"
            ) as mock_celery_check:
                mock_celery_check.return_value = False

                result = await validate_transcript_for_processing(mock_transcript)

            assert isinstance(result, ValidationAlreadyScheduled)


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_hatchet_validation_allows_failed_workflow():
    """Test that validation allows reprocessing when workflow has failed."""
    from reflector.services.transcript_process import (
        ValidationOk,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="error",
        source_kind="room",
        workflow_run_id="failed-workflow-123",
        recording_id="test-recording-id",
    )

    with patch("reflector.services.transcript_process.settings") as mock_settings:
        mock_settings.HATCHET_ENABLED = True

        with patch("reflector.hatchet.client.HatchetClientManager") as mock_hatchet:
            mock_hatchet.get_workflow_run_status = AsyncMock(return_value="FAILED")

            with patch(
                "reflector.services.transcript_process.task_is_scheduled_or_active"
            ) as mock_celery_check:
                mock_celery_check.return_value = False

                result = await validate_transcript_for_processing(mock_transcript)

            assert isinstance(result, ValidationOk)
            assert result.transcript_id == "test-transcript-id"


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_hatchet_validation_allows_completed_workflow():
    """Test that validation allows reprocessing when workflow has completed."""
    from reflector.services.transcript_process import (
        ValidationOk,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="ended",
        source_kind="room",
        workflow_run_id="completed-workflow-123",
        recording_id="test-recording-id",
    )

    with patch("reflector.services.transcript_process.settings") as mock_settings:
        mock_settings.HATCHET_ENABLED = True

        with patch("reflector.hatchet.client.HatchetClientManager") as mock_hatchet:
            mock_hatchet.get_workflow_run_status = AsyncMock(return_value="COMPLETED")

            with patch(
                "reflector.services.transcript_process.task_is_scheduled_or_active"
            ) as mock_celery_check:
                mock_celery_check.return_value = False

                result = await validate_transcript_for_processing(mock_transcript)

            assert isinstance(result, ValidationOk)


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_hatchet_validation_allows_when_status_check_fails():
    """Test that validation allows reprocessing when status check fails (workflow might be gone)."""
    from reflector.services.transcript_process import (
        ValidationOk,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="error",
        source_kind="room",
        workflow_run_id="old-workflow-123",
        recording_id="test-recording-id",
    )

    with patch("reflector.services.transcript_process.settings") as mock_settings:
        mock_settings.HATCHET_ENABLED = True

        with patch("reflector.hatchet.client.HatchetClientManager") as mock_hatchet:
            # Status check fails (workflow might be deleted)
            mock_hatchet.get_workflow_run_status = AsyncMock(
                side_effect=Exception("Workflow not found")
            )

            with patch(
                "reflector.services.transcript_process.task_is_scheduled_or_active"
            ) as mock_celery_check:
                mock_celery_check.return_value = False

                result = await validate_transcript_for_processing(mock_transcript)

            # Should allow processing when we can't get status
            assert isinstance(result, ValidationOk)


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_hatchet_validation_skipped_when_no_workflow_id():
    """Test that Hatchet validation is skipped when transcript has no workflow_run_id."""
    from reflector.services.transcript_process import (
        ValidationOk,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="uploaded",
        source_kind="room",
        workflow_run_id=None,  # No workflow yet
        recording_id="test-recording-id",
    )

    with patch("reflector.services.transcript_process.settings") as mock_settings:
        mock_settings.HATCHET_ENABLED = True

        with patch("reflector.hatchet.client.HatchetClientManager") as mock_hatchet:
            # Should not be called
            mock_hatchet.get_workflow_run_status = AsyncMock()

            with patch(
                "reflector.services.transcript_process.task_is_scheduled_or_active"
            ) as mock_celery_check:
                mock_celery_check.return_value = False

                result = await validate_transcript_for_processing(mock_transcript)

            # Should not check Hatchet status
            mock_hatchet.get_workflow_run_status.assert_not_called()
            assert isinstance(result, ValidationOk)


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_hatchet_validation_skipped_when_disabled():
    """Test that Hatchet validation is skipped when HATCHET_ENABLED is False."""
    from reflector.services.transcript_process import (
        ValidationOk,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="uploaded",
        source_kind="room",
        workflow_run_id="some-workflow-123",
        recording_id="test-recording-id",
    )

    with patch("reflector.services.transcript_process.settings") as mock_settings:
        mock_settings.HATCHET_ENABLED = False  # Hatchet disabled

        with patch(
            "reflector.services.transcript_process.task_is_scheduled_or_active"
        ) as mock_celery_check:
            mock_celery_check.return_value = False

            result = await validate_transcript_for_processing(mock_transcript)

        # Should not check Hatchet at all
        assert isinstance(result, ValidationOk)


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_validation_locked_transcript():
    """Test that validation rejects locked transcripts."""
    from reflector.services.transcript_process import (
        ValidationLocked,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="ended",
        source_kind="room",
        locked=True,
    )

    result = await validate_transcript_for_processing(mock_transcript)

    assert isinstance(result, ValidationLocked)
    assert "locked" in result.detail.lower()


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_validation_idle_transcript():
    """Test that validation rejects idle transcripts (not ready)."""
    from reflector.services.transcript_process import (
        ValidationNotReady,
        validate_transcript_for_processing,
    )

    mock_transcript = Transcript(
        id="test-transcript-id",
        name="Test",
        status="idle",
        source_kind="room",
    )

    result = await validate_transcript_for_processing(mock_transcript)

    assert isinstance(result, ValidationNotReady)
    assert "not ready" in result.detail.lower()


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_prepare_multitrack_config():
    """Test preparing multitrack processing config."""
    from reflector.db.recordings import Recording
    from reflector.services.transcript_process import (
        MultitrackProcessingConfig,
        ValidationOk,
        prepare_transcript_processing,
    )

    validation = ValidationOk(
        recording_id="test-recording-id",
        transcript_id="test-transcript-id",
    )

    mock_recording = Recording(
        id="test-recording-id",
        bucket_name="test-bucket",
        object_key="recordings/test",
        recorded_at="2024-01-01T00:00:00Z",
        track_keys=["track1.webm", "track2.webm"],
    )

    with patch(
        "reflector.services.transcript_process.recordings_controller"
    ) as mock_rc:
        mock_rc.get_by_id = AsyncMock(return_value=mock_recording)

        result = await prepare_transcript_processing(validation)

    assert isinstance(result, MultitrackProcessingConfig)
    assert result.bucket_name == "test-bucket"
    assert result.track_keys == ["track1.webm", "track2.webm"]
    assert result.transcript_id == "test-transcript-id"
    assert result.room_id == "test-room"


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
async def test_prepare_file_config():
    """Test preparing file processing config (no track keys)."""
    from reflector.db.recordings import Recording
    from reflector.services.transcript_process import (
        FileProcessingConfig,
        ValidationOk,
        prepare_transcript_processing,
    )

    validation = ValidationOk(
        recording_id="test-recording-id",
        transcript_id="test-transcript-id",
    )

    mock_recording = Recording(
        id="test-recording-id",
        bucket_name="test-bucket",
        object_key="recordings/test.mp4",
        recorded_at="2024-01-01T00:00:00Z",
        track_keys=None,  # No track keys = file pipeline
    )

    with patch(
        "reflector.services.transcript_process.recordings_controller"
    ) as mock_rc:
        mock_rc.get_by_id = AsyncMock(return_value=mock_recording)

        result = await prepare_transcript_processing(validation)

    assert isinstance(result, FileProcessingConfig)
    assert result.transcript_id == "test-transcript-id"
