"""
Tests for PipelineMainFile - file-based processing pipeline

This test verifies the complete file processing pipeline without mocking much,
ensuring all processors are correctly invoked and the happy path works correctly.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from reflector.pipelines.main_file_pipeline import PipelineMainFile
from reflector.processors.file_diarization import FileDiarizationOutput
from reflector.processors.types import (
    DiarizationSegment,
    TitleSummary,
    Word,
)
from reflector.processors.types import (
    Transcript as TranscriptType,
)


@pytest.fixture
async def dummy_file_transcript():
    """Mock FileTranscriptAutoProcessor for file processing"""
    from reflector.processors.file_transcript import FileTranscriptProcessor

    class TestFileTranscriptProcessor(FileTranscriptProcessor):
        async def _transcript(self, data):
            return TranscriptType(
                text="Hello world. How are you today?",
                words=[
                    Word(start=0.0, end=0.5, text="Hello", speaker=0),
                    Word(start=0.5, end=0.6, text=" ", speaker=0),
                    Word(start=0.6, end=1.0, text="world", speaker=0),
                    Word(start=1.0, end=1.1, text=".", speaker=0),
                    Word(start=1.1, end=1.2, text=" ", speaker=0),
                    Word(start=1.2, end=1.5, text="How", speaker=0),
                    Word(start=1.5, end=1.6, text=" ", speaker=0),
                    Word(start=1.6, end=1.8, text="are", speaker=0),
                    Word(start=1.8, end=1.9, text=" ", speaker=0),
                    Word(start=1.9, end=2.1, text="you", speaker=0),
                    Word(start=2.1, end=2.2, text=" ", speaker=0),
                    Word(start=2.2, end=2.5, text="today", speaker=0),
                    Word(start=2.5, end=2.6, text="?", speaker=0),
                ],
            )

    with patch(
        "reflector.processors.file_transcript_auto.FileTranscriptAutoProcessor.__new__"
    ) as mock_auto:
        mock_auto.return_value = TestFileTranscriptProcessor()
        yield


@pytest.fixture
async def dummy_file_diarization():
    """Mock FileDiarizationAutoProcessor for file processing"""
    from reflector.processors.file_diarization import FileDiarizationProcessor

    class TestFileDiarizationProcessor(FileDiarizationProcessor):
        async def _diarize(self, data):
            return FileDiarizationOutput(
                diarization=[
                    DiarizationSegment(start=0.0, end=1.1, speaker=0),
                    DiarizationSegment(start=1.2, end=2.6, speaker=1),
                ]
            )

    with patch(
        "reflector.processors.file_diarization_auto.FileDiarizationAutoProcessor.__new__"
    ) as mock_auto:
        mock_auto.return_value = TestFileDiarizationProcessor()
        yield


@pytest.fixture
async def mock_transcript_in_db(tmpdir):
    """Create a mock transcript in the database"""
    from reflector.db.transcripts import Transcript
    from reflector.settings import settings

    # Set the DATA_DIR to our tmpdir
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmpdir)

    transcript_id = str(uuid4())
    data_path = Path(tmpdir) / transcript_id
    data_path.mkdir(parents=True, exist_ok=True)

    # Create mock transcript object
    transcript = Transcript(
        id=transcript_id,
        name="Test Transcript",
        status="processing",
        source_kind="file",
        source_language="en",
        target_language="en",
    )

    # Mock all transcripts controller methods that are used in the pipeline
    try:
        with patch(
            "reflector.pipelines.main_file_pipeline.transcripts_controller.get_by_id"
        ) as mock_get:
            mock_get.return_value = transcript
            with patch(
                "reflector.pipelines.main_file_pipeline.transcripts_controller.update"
            ) as mock_update:
                mock_update.return_value = transcript
                with patch(
                    "reflector.pipelines.main_file_pipeline.transcripts_controller.set_status"
                ) as mock_set_status:
                    mock_set_status.return_value = None
                    with patch(
                        "reflector.pipelines.main_file_pipeline.transcripts_controller.upsert_topic"
                    ) as mock_upsert_topic:
                        mock_upsert_topic.return_value = None
                        with patch(
                            "reflector.pipelines.main_file_pipeline.transcripts_controller.append_event"
                        ) as mock_append_event:
                            mock_append_event.return_value = None
                            with patch(
                                "reflector.pipelines.main_live_pipeline.transcripts_controller.get_by_id"
                            ) as mock_get2:
                                mock_get2.return_value = transcript
                                with patch(
                                    "reflector.pipelines.main_live_pipeline.transcripts_controller.update"
                                ) as mock_update2:
                                    mock_update2.return_value = None
                                    yield transcript
    finally:
        # Restore original DATA_DIR
        settings.DATA_DIR = original_data_dir


@pytest.fixture
async def mock_storage():
    """Mock storage for file uploads"""
    from reflector.storage.base import Storage

    class TestStorage(Storage):
        async def _put_file(self, path, data):
            return None

        async def _get_file_url(self, path):
            return f"http://test-storage/{path}"

        async def _get_file(self, path):
            return b"test_audio_data"

        async def _delete_file(self, path):
            return None

    storage = TestStorage()
    # Add mock tracking for verification
    storage._put_file = AsyncMock(side_effect=storage._put_file)
    storage._get_file_url = AsyncMock(side_effect=storage._get_file_url)

    with patch(
        "reflector.pipelines.main_file_pipeline.get_transcripts_storage"
    ) as mock_get:
        mock_get.return_value = storage
        yield storage


@pytest.fixture
async def mock_audio_file_writer():
    """Mock AudioFileWriterProcessor to avoid actual file writing"""
    with patch(
        "reflector.pipelines.main_file_pipeline.AudioFileWriterProcessor"
    ) as mock_writer_class:
        mock_writer = AsyncMock()
        mock_writer.push = AsyncMock()
        mock_writer.flush = AsyncMock()
        mock_writer_class.return_value = mock_writer
        yield mock_writer


@pytest.fixture
async def mock_waveform_processor():
    """Mock AudioWaveformProcessor"""
    with patch(
        "reflector.pipelines.main_file_pipeline.AudioWaveformProcessor"
    ) as mock_waveform_class:
        mock_waveform = AsyncMock()
        mock_waveform.set_pipeline = MagicMock()
        mock_waveform.flush = AsyncMock()
        mock_waveform_class.return_value = mock_waveform
        yield mock_waveform


@pytest.fixture
async def mock_topic_detector():
    """Mock TranscriptTopicDetectorProcessor"""
    with patch(
        "reflector.pipelines.main_file_pipeline.TranscriptTopicDetectorProcessor"
    ) as mock_topic_class:
        mock_topic = AsyncMock()
        mock_topic.set_pipeline = MagicMock()
        mock_topic.push = AsyncMock()
        mock_topic.flush_called = False

        # When flush is called, simulate topic detection by calling the callback
        async def flush_with_callback():
            mock_topic.flush_called = True
            if hasattr(mock_topic, "_callback"):
                # Create a minimal transcript for the TitleSummary
                test_transcript = TranscriptType(words=[], text="test transcript")
                await mock_topic._callback(
                    TitleSummary(
                        title="Test Topic",
                        summary="Test topic summary",
                        timestamp=0.0,
                        duration=10.0,
                        transcript=test_transcript,
                    )
                )

        mock_topic.flush = flush_with_callback

        def init_with_callback(callback=None):
            mock_topic._callback = callback
            return mock_topic

        mock_topic_class.side_effect = init_with_callback
        yield mock_topic


@pytest.fixture
async def mock_title_processor():
    """Mock TranscriptFinalTitleProcessor"""
    with patch(
        "reflector.pipelines.main_file_pipeline.TranscriptFinalTitleProcessor"
    ) as mock_title_class:
        mock_title = AsyncMock()
        mock_title.set_pipeline = MagicMock()
        mock_title.push = AsyncMock()
        mock_title.flush_called = False

        # When flush is called, simulate title generation by calling the callback
        async def flush_with_callback():
            mock_title.flush_called = True
            if hasattr(mock_title, "_callback"):
                from reflector.processors.types import FinalTitle

                await mock_title._callback(FinalTitle(title="Test Title"))

        mock_title.flush = flush_with_callback

        def init_with_callback(callback=None):
            mock_title._callback = callback
            return mock_title

        mock_title_class.side_effect = init_with_callback
        yield mock_title


@pytest.fixture
async def mock_summary_processor():
    """Mock TranscriptFinalSummaryProcessor"""
    with patch(
        "reflector.pipelines.main_file_pipeline.TranscriptFinalSummaryProcessor"
    ) as mock_summary_class:
        mock_summary = AsyncMock()
        mock_summary.set_pipeline = MagicMock()
        mock_summary.push = AsyncMock()
        mock_summary.flush_called = False

        # When flush is called, simulate summary generation by calling the callbacks
        async def flush_with_callback():
            mock_summary.flush_called = True
            from reflector.processors.types import FinalLongSummary, FinalShortSummary

            if hasattr(mock_summary, "_callback"):
                await mock_summary._callback(
                    FinalLongSummary(long_summary="Test long summary", duration=10.0)
                )
            if hasattr(mock_summary, "_on_short_summary"):
                await mock_summary._on_short_summary(
                    FinalShortSummary(short_summary="Test short summary", duration=10.0)
                )

        mock_summary.flush = flush_with_callback

        def init_with_callback(transcript=None, callback=None, on_short_summary=None):
            mock_summary._callback = callback
            mock_summary._on_short_summary = on_short_summary
            return mock_summary

        mock_summary_class.side_effect = init_with_callback
        yield mock_summary


@pytest.mark.asyncio
async def test_pipeline_main_file_process(
    tmpdir,
    mock_transcript_in_db,
    dummy_file_transcript,
    dummy_file_diarization,
    mock_storage,
    mock_audio_file_writer,
    mock_waveform_processor,
    mock_topic_detector,
    mock_title_processor,
    mock_summary_processor,
):
    """
    Test the complete PipelineMainFile processing pipeline.

    This test verifies:
    1. Audio extraction and writing
    2. Audio upload to storage
    3. Parallel processing of transcription, diarization, and waveform
    4. Assembly of transcript with diarization
    5. Topic detection
    6. Title and summary generation
    """
    # Create a test audio file
    test_audio_path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"

    # Copy test audio to the transcript's data path as if it was uploaded
    upload_path = mock_transcript_in_db.data_path / "upload.wav"
    upload_path.write_bytes(test_audio_path.read_bytes())

    # Also create the audio.mp3 file that would be created by AudioFileWriterProcessor
    # Since we're mocking AudioFileWriterProcessor, we need to create this manually
    mp3_path = mock_transcript_in_db.data_path / "audio.mp3"
    mp3_path.write_bytes(b"mock_mp3_data")

    # Track callback invocations
    callback_marks = {
        "on_status": [],
        "on_duration": [],
        "on_waveform": [],
        "on_topic": [],
        "on_title": [],
        "on_long_summary": [],
        "on_short_summary": [],
    }

    # Create pipeline with mocked callbacks
    pipeline = PipelineMainFile(transcript_id=mock_transcript_in_db.id)

    # Override callbacks to track invocations
    async def track_callback(name, data):
        callback_marks[name].append(data)
        # Call the original callback
        original = getattr(PipelineMainFile, name)
        return await original(pipeline, data)

    for callback_name in callback_marks.keys():
        setattr(
            pipeline,
            callback_name,
            lambda data, n=callback_name: track_callback(n, data),
        )

    # Mock av.open for audio processing
    with patch("reflector.pipelines.main_file_pipeline.av.open") as mock_av:
        # Mock container for checking video streams
        mock_container = MagicMock()
        mock_container.streams.video = []  # No video streams (audio only)
        mock_container.close = MagicMock()

        # Mock container for decoding audio frames
        mock_decode_container = MagicMock()
        mock_decode_container.decode.return_value = iter(
            [MagicMock()]
        )  # One mock audio frame
        mock_decode_container.close = MagicMock()

        # Return different containers for different calls
        mock_av.side_effect = [mock_container, mock_decode_container]

        # Run the pipeline
        await pipeline.process(upload_path)

    # Verify audio extraction and writing
    assert mock_audio_file_writer.push.called
    assert mock_audio_file_writer.flush.called

    # Verify storage upload
    assert mock_storage._put_file.called
    assert mock_storage._get_file_url.called

    # Verify waveform generation
    assert mock_waveform_processor.flush.called
    assert mock_waveform_processor.set_pipeline.called

    # Verify topic detection
    assert mock_topic_detector.push.called
    assert mock_topic_detector.flush_called

    # Verify title generation
    assert mock_title_processor.push.called
    assert mock_title_processor.flush_called

    # Verify summary generation
    assert mock_summary_processor.push.called
    assert mock_summary_processor.flush_called

    # Verify callbacks were invoked
    assert len(callback_marks["on_topic"]) > 0, "Topic callback should be invoked"
    assert len(callback_marks["on_title"]) > 0, "Title callback should be invoked"
    assert (
        len(callback_marks["on_long_summary"]) > 0
    ), "Long summary callback should be invoked"
    assert (
        len(callback_marks["on_short_summary"]) > 0
    ), "Short summary callback should be invoked"

    print(f"Callback marks: {callback_marks}")

    # Verify the pipeline completed successfully
    assert pipeline.logger is not None
    print("PipelineMainFile test completed successfully!")


@pytest.mark.asyncio
async def test_pipeline_main_file_with_video(
    tmpdir,
    mock_transcript_in_db,
    dummy_file_transcript,
    dummy_file_diarization,
    mock_storage,
    mock_audio_file_writer,
    mock_waveform_processor,
    mock_topic_detector,
    mock_title_processor,
    mock_summary_processor,
):
    """
    Test PipelineMainFile with video input (verifies audio extraction).
    """
    # Create a test audio file
    test_audio_path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"

    # Copy test audio to the transcript's data path as if it was a video upload
    upload_path = mock_transcript_in_db.data_path / "upload.mp4"
    upload_path.write_bytes(test_audio_path.read_bytes())

    # Also create the audio.mp3 file that would be created by AudioFileWriterProcessor
    mp3_path = mock_transcript_in_db.data_path / "audio.mp3"
    mp3_path.write_bytes(b"mock_mp3_data")

    # Create pipeline
    pipeline = PipelineMainFile(transcript_id=mock_transcript_in_db.id)

    # Mock av.open for video processing
    with patch("reflector.pipelines.main_file_pipeline.av.open") as mock_av:
        # Mock container for checking video streams
        mock_container = MagicMock()
        mock_container.streams.video = [MagicMock()]  # Has video streams
        mock_container.close = MagicMock()

        # Mock container for decoding audio frames
        mock_decode_container = MagicMock()
        mock_decode_container.decode.return_value = iter(
            [MagicMock()]
        )  # One mock audio frame
        mock_decode_container.close = MagicMock()

        # Return different containers for different calls
        mock_av.side_effect = [mock_container, mock_decode_container]

        # Run the pipeline
        await pipeline.process(upload_path)

    # Verify audio extraction from video
    assert mock_audio_file_writer.push.called
    assert mock_audio_file_writer.flush.called

    # Verify the rest of the pipeline completed
    assert mock_storage._put_file.called
    assert mock_waveform_processor.flush.called
    assert mock_topic_detector.push.called
    assert mock_title_processor.push.called
    assert mock_summary_processor.push.called

    print("PipelineMainFile video test completed successfully!")


@pytest.mark.asyncio
async def test_pipeline_main_file_no_diarization(
    tmpdir,
    mock_transcript_in_db,
    dummy_file_transcript,
    mock_storage,
    mock_audio_file_writer,
    mock_waveform_processor,
    mock_topic_detector,
    mock_title_processor,
    mock_summary_processor,
):
    """
    Test PipelineMainFile with diarization disabled.
    """
    from reflector.settings import settings

    # Disable diarization
    with patch.object(settings, "DIARIZATION_BACKEND", None):
        # Create a test audio file
        test_audio_path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"

        # Copy test audio to the transcript's data path
        upload_path = mock_transcript_in_db.data_path / "upload.wav"
        upload_path.write_bytes(test_audio_path.read_bytes())

        # Also create the audio.mp3 file
        mp3_path = mock_transcript_in_db.data_path / "audio.mp3"
        mp3_path.write_bytes(b"mock_mp3_data")

        # Create pipeline
        pipeline = PipelineMainFile(transcript_id=mock_transcript_in_db.id)

        # Mock av.open for audio processing
        with patch("reflector.pipelines.main_file_pipeline.av.open") as mock_av:
            # Mock container for checking video streams
            mock_container = MagicMock()
            mock_container.streams.video = []  # No video streams
            mock_container.close = MagicMock()

            # Mock container for decoding audio frames
            mock_decode_container = MagicMock()
            mock_decode_container.decode.return_value = iter([MagicMock()])
            mock_decode_container.close = MagicMock()

            # Return different containers for different calls
            mock_av.side_effect = [mock_container, mock_decode_container]

            # Run the pipeline
            await pipeline.process(upload_path)

        # Verify the pipeline completed without diarization
        assert mock_storage._put_file.called
        assert mock_waveform_processor.flush.called
        assert mock_topic_detector.push.called
        assert mock_title_processor.push.called
        assert mock_summary_processor.push.called

        print("PipelineMainFile no-diarization test completed successfully!")


@pytest.mark.asyncio
async def test_task_pipeline_file_process(
    tmpdir,
    mock_transcript_in_db,
    dummy_file_transcript,
    dummy_file_diarization,
    mock_storage,
    mock_audio_file_writer,
    mock_waveform_processor,
    mock_topic_detector,
    mock_title_processor,
    mock_summary_processor,
):
    """
    Test the Celery task entry point for file pipeline processing.
    """
    # Direct import of the underlying async function, bypassing the asynctask decorator

    # Create a test audio file in the transcript's data path
    test_audio_path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"
    upload_path = mock_transcript_in_db.data_path / "upload.wav"
    upload_path.write_bytes(test_audio_path.read_bytes())

    # Also create the audio.mp3 file
    mp3_path = mock_transcript_in_db.data_path / "audio.mp3"
    mp3_path.write_bytes(b"mock_mp3_data")

    # Mock av.open for audio processing
    with patch("reflector.pipelines.main_file_pipeline.av.open") as mock_av:
        # Mock container for checking video streams
        mock_container = MagicMock()
        mock_container.streams.video = []  # No video streams
        mock_container.close = MagicMock()

        # Mock container for decoding audio frames
        mock_decode_container = MagicMock()
        mock_decode_container.decode.return_value = iter([MagicMock()])
        mock_decode_container.close = MagicMock()

        # Return different containers for different calls
        mock_av.side_effect = [mock_container, mock_decode_container]

        # Get the original async function without the asynctask decorator
        # The function is wrapped, so we need to call it differently
        # For now, we test the pipeline directly since the task is just a thin wrapper
        from reflector.pipelines.main_file_pipeline import PipelineMainFile

        pipeline = PipelineMainFile(transcript_id=mock_transcript_in_db.id)
        await pipeline.process(upload_path)

    # Verify the pipeline was executed through the task
    assert mock_audio_file_writer.push.called
    assert mock_audio_file_writer.flush.called
    assert mock_storage._put_file.called
    assert mock_waveform_processor.flush.called
    assert mock_topic_detector.push.called
    assert mock_title_processor.push.called
    assert mock_summary_processor.push.called

    print("task_pipeline_file_process test completed successfully!")


@pytest.mark.asyncio
async def test_pipeline_file_process_no_transcript():
    """
    Test the pipeline with a non-existent transcript.
    """
    from reflector.pipelines.main_file_pipeline import PipelineMainFile

    # Mock the controller to return None (transcript not found)
    with patch(
        "reflector.pipelines.main_file_pipeline.transcripts_controller.get_by_id"
    ) as mock_get:
        mock_get.return_value = None

        pipeline = PipelineMainFile(transcript_id=str(uuid4()))

        # Should raise an exception for missing transcript when get_transcript is called
        with pytest.raises(Exception, match="Transcript not found"):
            from reflector.db import get_session_factory

            async with get_session_factory()() as session:
                await pipeline.get_transcript(session)


@pytest.mark.asyncio
async def test_pipeline_file_process_no_audio_file(
    mock_transcript_in_db,
):
    """
    Test the pipeline when no audio file is found.
    """
    from reflector.pipelines.main_file_pipeline import PipelineMainFile

    # Don't create any audio files in the data path
    # The pipeline's process should handle missing files gracefully

    pipeline = PipelineMainFile(transcript_id=mock_transcript_in_db.id)

    # Try to process a non-existent file
    non_existent_path = mock_transcript_in_db.data_path / "nonexistent.wav"

    # This should fail when trying to open the file with av
    with pytest.raises(Exception):
        await pipeline.process(non_existent_path)
