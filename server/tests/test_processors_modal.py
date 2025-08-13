"""
Tests for Modal-based processors using pytest-vcr for HTTP recording/playbook

Note: theses tests require full modal configuration to be able to record
      vcr cassettes

Configuration required for the first recording:
- TRANSCRIPT_BACKEND=modal
- TRANSCRIPT_URL=https://xxxxx--reflector-transcriber-parakeet-web.modal.run
- TRANSCRIPT_MODAL_API_KEY=xxxxx
- DIARIZATION_BACKEND=modal
- DIARIZATION_URL=https://xxxxx--reflector-diarizer-web.modal.run
- DIARIZATION_MODAL_API_KEY=xxxxx
"""

from unittest.mock import patch

import pytest

from reflector.processors.file_diarization import FileDiarizationInput
from reflector.processors.file_diarization_modal import FileDiarizationModalProcessor
from reflector.processors.file_transcript import FileTranscriptInput
from reflector.processors.file_transcript_modal import FileTranscriptModalProcessor
from reflector.processors.transcript_diarization_assembler import (
    TranscriptDiarizationAssemblerInput,
    TranscriptDiarizationAssemblerProcessor,
)
from reflector.processors.types import DiarizationSegment, Transcript, Word

# Public test audio file hosted on S3 specifically for reflector pytests
TEST_AUDIO_URL = (
    "https://reflector-github-pytest.s3.us-east-1.amazonaws.com/test_mathieu_hello.mp3"
)


@pytest.fixture(scope="module")
def vcr_config():
    """VCR configuration to filter sensitive headers"""
    return {
        "filter_headers": [("authorization", "DUMMY_API_KEY")],
        "record_mode": "once",  # Record once, then replay
    }


@pytest.mark.asyncio
async def test_file_transcript_modal_processor_missing_url():
    with patch("reflector.processors.file_transcript_modal.settings") as mock_settings:
        mock_settings.TRANSCRIPT_URL = None
        with pytest.raises(Exception, match="TRANSCRIPT_URL required"):
            FileTranscriptModalProcessor(modal_api_key="test-api-key")


@pytest.mark.asyncio
async def test_file_diarization_modal_processor_missing_url():
    with patch("reflector.processors.file_diarization_modal.settings") as mock_settings:
        mock_settings.DIARIZATION_URL = None
        with pytest.raises(Exception, match="DIARIZATION_URL required"):
            FileDiarizationModalProcessor(modal_api_key="test-api-key")


@pytest.mark.vcr()
@pytest.mark.asyncio
async def test_file_diarization_modal_processor(vcr):
    """Test FileDiarizationModalProcessor using public audio URL and Modal API"""
    from reflector.settings import settings

    processor = FileDiarizationModalProcessor(
        modal_api_key=settings.DIARIZATION_MODAL_API_KEY
    )

    test_input = FileDiarizationInput(audio_url=TEST_AUDIO_URL)
    result = await processor._diarize(test_input)

    # Verify the result structure
    assert result is not None
    assert hasattr(result, "diarization")
    assert isinstance(result.diarization, list)

    # Check structure of each diarization segment
    for segment in result.diarization:
        assert "start" in segment
        assert "end" in segment
        assert "speaker" in segment
        assert isinstance(segment["start"], (int, float))
        assert isinstance(segment["end"], (int, float))
        assert isinstance(segment["speaker"], int)
        # Basic sanity check - start should be before end
        assert segment["start"] < segment["end"]


@pytest.mark.vcr()
@pytest.mark.asyncio
async def test_file_transcript_modal_processor():
    """Test FileTranscriptModalProcessor using public audio URL and Modal API"""
    from reflector.settings import settings

    processor = FileTranscriptModalProcessor(
        modal_api_key=settings.TRANSCRIPT_MODAL_API_KEY
    )

    test_input = FileTranscriptInput(
        audio_url=TEST_AUDIO_URL,
        language="en",
    )

    # This will record the HTTP interaction on first run, replay on subsequent runs
    result = await processor._transcript(test_input)

    # Verify the result structure
    assert result is not None
    assert hasattr(result, "words")
    assert isinstance(result.words, list)

    # Check structure of each word if present
    for word in result.words:
        assert hasattr(word, "text")
        assert hasattr(word, "start")
        assert hasattr(word, "end")
        assert isinstance(word.start, (int, float))
        assert isinstance(word.end, (int, float))
        assert isinstance(word.text, str)
        # Basic sanity check - start should be before or equal to end
        assert word.start <= word.end


@pytest.mark.asyncio
async def test_transcript_diarization_assembler_processor():
    """Test TranscriptDiarizationAssemblerProcessor without VCR (no HTTP requests)"""
    # Create test transcript with words
    words = [
        Word(text="Hello", start=0.0, end=1.0, speaker=0),
        Word(text=" ", start=1.0, end=1.1, speaker=0),
        Word(text="world", start=1.1, end=2.0, speaker=0),
        Word(text=".", start=2.0, end=2.1, speaker=0),
        Word(text=" ", start=2.1, end=2.2, speaker=0),
        Word(text="How", start=2.2, end=2.8, speaker=0),
        Word(text=" ", start=2.8, end=2.9, speaker=0),
        Word(text="are", start=2.9, end=3.2, speaker=0),
        Word(text=" ", start=3.2, end=3.3, speaker=0),
        Word(text="you", start=3.3, end=3.8, speaker=0),
        Word(text="?", start=3.8, end=3.9, speaker=0),
    ]
    transcript = Transcript(words=words)

    # Create test diarization segments
    diarization = [
        DiarizationSegment(start=0.0, end=2.1, speaker=0),
        DiarizationSegment(start=2.1, end=3.9, speaker=1),
    ]

    # Create processor and test input
    processor = TranscriptDiarizationAssemblerProcessor()
    test_input = TranscriptDiarizationAssemblerInput(
        transcript=transcript, diarization=diarization
    )

    # Track emitted results
    emitted_results = []

    async def capture_result(result):
        emitted_results.append(result)

    processor.on(capture_result)

    # Process the input
    await processor.push(test_input)

    # Verify result was emitted
    assert len(emitted_results) == 1
    result = emitted_results[0]

    # Verify result structure
    assert isinstance(result, Transcript)
    assert len(result.words) == len(words)

    # Verify speaker assignments were applied
    # Words 0-3 (indices) should be speaker 0 (time 0.0-2.0)
    # Words 4-10 (indices) should be speaker 1 (time 2.1-3.9)
    for i in range(4):  # First 4 words (Hello, space, world, .)
        assert (
            result.words[i].speaker == 0
        ), f"Word {i} '{result.words[i].text}' should be speaker 0, got {result.words[i].speaker}"

    for i in range(4, 11):  # Remaining words (space, How, space, are, space, you, ?)
        assert (
            result.words[i].speaker == 1
        ), f"Word {i} '{result.words[i].text}' should be speaker 1, got {result.words[i].speaker}"


@pytest.mark.asyncio
async def test_transcript_diarization_assembler_no_diarization():
    """Test TranscriptDiarizationAssemblerProcessor with no diarization data"""
    # Create test transcript
    words = [Word(text="Hello", start=0.0, end=1.0, speaker=0)]
    transcript = Transcript(words=words)

    # Create processor and test input with empty diarization
    processor = TranscriptDiarizationAssemblerProcessor()
    test_input = TranscriptDiarizationAssemblerInput(
        transcript=transcript, diarization=[]
    )

    # Track emitted results
    emitted_results = []

    async def capture_result(result):
        emitted_results.append(result)

    processor.on(capture_result)

    # Process the input
    await processor.push(test_input)

    # Verify original transcript was returned unchanged
    assert len(emitted_results) == 1
    result = emitted_results[0]
    assert result is transcript  # Should be the same object
    assert result.words[0].speaker == 0  # Original speaker unchanged


@pytest.mark.vcr()
@pytest.mark.asyncio
async def test_full_modal_pipeline_integration(vcr):
    """Integration test: Transcription -> Diarization -> Assembly

    This test demonstrates the full pipeline:
    1. Run transcription via Modal
    2. Run diarization via Modal
    3. Assemble transcript with diarization
    """
    from reflector.settings import settings

    # Step 1: Transcription
    transcript_processor = FileTranscriptModalProcessor(
        modal_api_key=settings.TRANSCRIPT_MODAL_API_KEY
    )
    transcript_input = FileTranscriptInput(audio_url=TEST_AUDIO_URL, language="en")
    transcript = await transcript_processor._transcript(transcript_input)

    # Step 2: Diarization
    diarization_processor = FileDiarizationModalProcessor(
        modal_api_key=settings.DIARIZATION_MODAL_API_KEY
    )
    diarization_input = FileDiarizationInput(audio_url=TEST_AUDIO_URL)
    diarization_result = await diarization_processor._diarize(diarization_input)

    # Step 3: Assembly
    assembler = TranscriptDiarizationAssemblerProcessor()
    assembly_input = TranscriptDiarizationAssemblerInput(
        transcript=transcript, diarization=diarization_result.diarization
    )

    # Track assembled result
    assembled_results = []

    async def capture_result(result):
        assembled_results.append(result)

    assembler.on(capture_result)

    await assembler.push(assembly_input)

    # Verify the full pipeline worked
    assert len(assembled_results) == 1
    final_transcript = assembled_results[0]

    # Verify the final transcript has the original words with updated speaker info
    assert isinstance(final_transcript, Transcript)
    assert len(final_transcript.words) == len(transcript.words)
    assert len(final_transcript.words) > 0

    # Verify some words have been assigned speakers from diarization
    speakers_found = set(word.speaker for word in final_transcript.words)
    assert len(speakers_found) > 0  # At least some speaker assignments
