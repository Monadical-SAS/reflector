"""Integration tests for multitrack CLI processing functionality"""

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.db.transcripts import SourceKind, TranscriptTopic
from reflector.tools.cli_multitrack import process_multitrack_cli


class TestMultitrackCLI:
    """Integration tests for multitrack CLI processing"""

    @pytest.mark.asyncio
    async def test_process_single_track(self):
        """Test processing a single track through multitrack mode"""
        s3_urls = ["s3://test-bucket/track1.webm"]

        with (
            patch("reflector.db.get_database") as mock_get_db,
            patch(
                "reflector.tools.cli_multitrack.get_transcripts_storage"
            ) as mock_get_storage,
            patch(
                "reflector.services.multitrack.transcripts_controller"
            ) as mock_controller,
            patch(
                "reflector.services.multitrack.task_pipeline_multitrack_process"
            ) as mock_task,
            patch(
                "reflector.tools.cli_multitrack.validate_s3_objects",
                new_callable=AsyncMock,
            ) as mock_validate,
            patch(
                "reflector.tools.cli_multitrack.extract_result_from_entry",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            # Mock database
            mock_db = MagicMock()
            mock_db.connect = AsyncMock()
            mock_db.disconnect = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock storage
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage

            # Mock validation (success) - async function returns None
            mock_validate.return_value = None

            # Mock transcript creation
            mock_transcript = MagicMock()
            mock_transcript.id = "test-transcript-123"
            mock_transcript.topics = [
                TranscriptTopic(
                    id="topic1",
                    title="Test Topic",
                    summary="Test summary",
                    timestamp=0.0,
                    words=[
                        {"text": "hello", "start": 0.0, "end": 0.5, "speaker": 0},
                        {"text": "world", "start": 0.5, "end": 1.0, "speaker": 0},
                    ],
                )
            ]
            mock_controller.add = AsyncMock(return_value=mock_transcript)
            mock_controller.get_by_id = AsyncMock(return_value=mock_transcript)

            # Mock task execution
            mock_result = MagicMock()
            mock_result.ready.return_value = True
            mock_result.failed.return_value = False
            mock_result.state = "SUCCESS"
            mock_result.id = "task-123"
            mock_task.delay.return_value = mock_result

            # Test with output to temp file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False
            ) as f:
                output_path = f.name

            try:
                await process_multitrack_cli(
                    s3_urls,
                    source_language="en",
                    target_language="en",
                    output_path=output_path,
                )

                # Verify transcript was created correctly
                mock_controller.add.assert_called_once_with(
                    "Multitrack (1 track)",
                    source_kind=SourceKind.FILE,
                    source_language="en",
                    target_language="en",
                    user_id=None,
                )

                # Verify task was called with correct parameters
                mock_task.delay.assert_called_once_with(
                    transcript_id="test-transcript-123",
                    bucket_name="test-bucket",
                    track_keys=["track1.webm"],
                )

                # Verify extract was called
                mock_extract.assert_called_once_with("test-transcript-123", output_path)
            finally:
                pass

    @pytest.mark.asyncio
    async def test_process_multiple_tracks(self):
        """Test processing multiple tracks"""
        s3_urls = [
            "s3://test-bucket/track1.webm",
            "s3://test-bucket/track2.webm",
            "s3://test-bucket/track3.webm",
        ]

        with (
            patch("reflector.db.get_database") as mock_get_db,
            patch(
                "reflector.tools.cli_multitrack.get_transcripts_storage"
            ) as mock_get_storage,
            patch(
                "reflector.services.multitrack.transcripts_controller"
            ) as mock_controller,
            patch(
                "reflector.services.multitrack.task_pipeline_multitrack_process"
            ) as mock_task,
            patch(
                "reflector.tools.cli_multitrack.validate_s3_objects",
                new_callable=AsyncMock,
            ) as mock_validate,
            patch(
                "reflector.tools.cli_multitrack.extract_result_from_entry",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            # Setup mocks
            mock_db = MagicMock()
            mock_db.connect = AsyncMock()
            mock_db.disconnect = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            mock_validate.return_value = None

            mock_transcript = MagicMock()
            mock_transcript.id = "test-transcript-456"
            mock_transcript.topics = [
                TranscriptTopic(
                    id="topic1",
                    title="Test Topic",
                    summary="Test summary",
                    timestamp=0.0,
                    words=[
                        {"text": "speaker", "start": 0.0, "end": 0.5, "speaker": 0},
                        {"text": "one", "start": 0.5, "end": 1.0, "speaker": 0},
                        {"text": "speaker", "start": 1.0, "end": 1.5, "speaker": 1},
                        {"text": "two", "start": 1.5, "end": 2.0, "speaker": 1},
                        {"text": "speaker", "start": 2.0, "end": 2.5, "speaker": 2},
                        {"text": "three", "start": 2.5, "end": 3.0, "speaker": 2},
                    ],
                )
            ]
            mock_controller.add = AsyncMock(return_value=mock_transcript)
            mock_controller.get_by_id = AsyncMock(return_value=mock_transcript)

            mock_result = MagicMock()
            mock_result.ready.return_value = True
            mock_result.failed.return_value = False
            mock_result.state = "SUCCESS"
            mock_result.id = "task-456"
            mock_task.delay.return_value = mock_result

            await process_multitrack_cli(
                s3_urls,
                source_language="en",
                target_language="en",
                output_path=None,  # Output to stdout
            )

            # Verify transcript creation
            mock_controller.add.assert_called_once_with(
                "Multitrack (3 tracks)",
                source_kind=SourceKind.FILE,
                source_language="en",
                target_language="en",
                user_id=None,
            )

            # Verify task was called with all track keys
            mock_task.delay.assert_called_once_with(
                transcript_id="test-transcript-456",
                bucket_name="test-bucket",
                track_keys=["track1.webm", "track2.webm", "track3.webm"],
            )

    @pytest.mark.asyncio
    async def test_process_invalid_urls(self):
        """Test that invalid S3 URLs raise appropriate errors"""
        s3_urls = [
            "s3://valid-bucket/track1.webm",
            "http://not-s3.com/track2.webm",  # Invalid URL
        ]

        # No database mocking needed - error happens before database connection
        with pytest.raises(
            ValueError, match="Invalid S3 URL 'http://not-s3.com/track2.webm'"
        ):
            await process_multitrack_cli(
                s3_urls,
                source_language="en",
                target_language="en",
            )

    @pytest.mark.asyncio
    async def test_process_empty_list(self):
        """Test that empty URL list raises error"""
        with pytest.raises(ValueError, match="At least one track required"):
            await process_multitrack_cli(
                [],  # Empty list
                source_language="en",
                target_language="en",
            )

    @pytest.mark.asyncio
    async def test_process_missing_objects(self):
        """Test that missing S3 objects are caught during validation"""
        s3_urls = ["s3://test-bucket/missing.webm"]

        with (
            patch("reflector.db.get_database") as mock_get_db,
            patch(
                "reflector.tools.cli_multitrack.get_transcripts_storage"
            ) as mock_get_storage,
            patch(
                "reflector.tools.cli_multitrack.validate_s3_objects",
                new_callable=AsyncMock,
            ) as mock_validate,
            patch(
                "reflector.tools.cli_multitrack.extract_result_from_entry",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_db = MagicMock()
            mock_db.connect = AsyncMock()
            mock_db.disconnect = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage

            # Simulate validation failure
            mock_validate.side_effect = ValueError(
                "S3 object not found: s3://test-bucket/missing.webm"
            )

            with pytest.raises(ValueError, match="S3 object not found"):
                await process_multitrack_cli(
                    s3_urls,
                    source_language="en",
                    target_language="en",
                )

    @pytest.mark.asyncio
    async def test_pipeline_task_failure(self):
        """Test handling of pipeline task failure"""
        s3_urls = ["s3://test-bucket/track1.webm"]

        with (
            patch("reflector.db.get_database") as mock_get_db,
            patch(
                "reflector.tools.cli_multitrack.get_transcripts_storage"
            ) as mock_get_storage,
            patch(
                "reflector.services.multitrack.transcripts_controller"
            ) as mock_controller,
            patch(
                "reflector.services.multitrack.task_pipeline_multitrack_process"
            ) as mock_task,
            patch(
                "reflector.tools.cli_multitrack.validate_s3_objects",
                new_callable=AsyncMock,
            ) as mock_validate,
            patch(
                "reflector.tools.cli_multitrack.extract_result_from_entry",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_db = MagicMock()
            mock_db.connect = AsyncMock()
            mock_db.disconnect = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            mock_validate.return_value = None

            mock_transcript = MagicMock()
            mock_transcript.id = "test-transcript-fail"
            mock_controller.add = AsyncMock(return_value=mock_transcript)

            # Simulate task failure
            mock_result = MagicMock()
            mock_result.ready.return_value = True
            mock_result.failed.return_value = True
            mock_result.info = "Pipeline processing error: Audio format not supported"
            mock_task.delay.return_value = mock_result

            with pytest.raises(RuntimeError, match="Multitrack pipeline failed"):
                await process_multitrack_cli(
                    s3_urls,
                    source_language="en",
                    target_language="en",
                )

    @pytest.mark.asyncio
    async def test_track_order_preserved(self):
        """Test that track order is preserved through pipeline submission"""
        s3_urls = [
            "s3://test-bucket/alice.webm",
            "s3://test-bucket/bob.webm",
            "s3://test-bucket/charlie.webm",
        ]

        with (
            patch("reflector.db.get_database") as mock_get_db,
            patch(
                "reflector.tools.cli_multitrack.get_transcripts_storage"
            ) as mock_get_storage,
            patch(
                "reflector.services.multitrack.transcripts_controller"
            ) as mock_controller,
            patch(
                "reflector.services.multitrack.task_pipeline_multitrack_process"
            ) as mock_task,
            patch(
                "reflector.tools.cli_multitrack.validate_s3_objects",
                new_callable=AsyncMock,
            ) as mock_validate,
            patch(
                "reflector.tools.cli_multitrack.extract_result_from_entry",
                new_callable=AsyncMock,
            ) as mock_extract,
        ):
            mock_db = MagicMock()
            mock_db.connect = AsyncMock()
            mock_db.disconnect = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            mock_validate.return_value = None

            # Create transcript with speaker assignments matching track order
            mock_transcript = MagicMock()
            mock_transcript.id = "test-transcript-speakers"
            mock_transcript.topics = [
                TranscriptTopic(
                    id="topic1",
                    title="Test Topic",
                    summary="Test summary",
                    timestamp=0.0,
                    words=[
                        {
                            "text": "alice",
                            "start": 0.0,
                            "end": 0.5,
                            "speaker": 0,
                        },  # Track 0
                        {"text": "speaking", "start": 0.5, "end": 1.0, "speaker": 0},
                        {
                            "text": "bob",
                            "start": 1.0,
                            "end": 1.5,
                            "speaker": 1,
                        },  # Track 1
                        {"text": "responding", "start": 1.5, "end": 2.0, "speaker": 1},
                        {
                            "text": "charlie",
                            "start": 2.0,
                            "end": 2.5,
                            "speaker": 2,
                        },  # Track 2
                        {
                            "text": "interrupting",
                            "start": 2.5,
                            "end": 3.0,
                            "speaker": 2,
                        },
                    ],
                )
            ]
            mock_controller.add = AsyncMock(return_value=mock_transcript)
            mock_controller.get_by_id = AsyncMock(return_value=mock_transcript)

            mock_result = MagicMock()
            mock_result.ready.return_value = True
            mock_result.failed.return_value = False
            mock_task.delay.return_value = mock_result

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False
            ) as f:
                output_path = f.name

            try:
                await process_multitrack_cli(
                    s3_urls,
                    source_language="en",
                    target_language="en",
                    output_path=output_path,
                )

                # Verify track order preserved in task call
                mock_task.delay.assert_called_once_with(
                    transcript_id="test-transcript-speakers",
                    bucket_name="test-bucket",
                    track_keys=[
                        "alice.webm",
                        "bob.webm",
                        "charlie.webm",
                    ],  # Order matters!
                )

                # Verify extract was called
                mock_extract.assert_called_once_with(
                    "test-transcript-speakers", output_path
                )

            finally:
                pass
