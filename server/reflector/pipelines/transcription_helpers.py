"""
Helper utilities for file transcription across pipelines.
"""

from reflector.processors.file_transcript import FileTranscriptInput
from reflector.processors.file_transcript_auto import FileTranscriptAutoProcessor
from reflector.processors.types import Transcript as TranscriptType


async def transcribe_file_with_processor(
    audio_url: str,
    language: str,
    processor_name: str | None = None,
) -> TranscriptType:
    """
    Transcribe an audio file using FileTranscriptAutoProcessor.

    Args:
        audio_url: URL to the audio file (must be publicly accessible)
        language: Language code (e.g., "en", "es")
        processor_name: Optional processor name (e.g., "whisper", "modal").
                       If None, uses default auto-selection.

    Returns:
        TranscriptType with words and optional translation

    Raises:
        ValueError: If no transcript was captured from the processor
    """
    processor = (
        FileTranscriptAutoProcessor(name=processor_name)
        if processor_name
        else FileTranscriptAutoProcessor()
    )
    input_data = FileTranscriptInput(audio_url=audio_url, language=language)

    result: TranscriptType | None = None

    async def capture_result(transcript):
        nonlocal result
        result = transcript

    processor.on(capture_result)
    await processor.push(input_data)
    await processor.flush()

    if not result:
        processor_label = processor_name or "default"
        raise ValueError(
            f"No transcript captured from {processor_label} processor for audio: {audio_url}"
        )

    return result
