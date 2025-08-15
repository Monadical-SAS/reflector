import pytest


@pytest.mark.asyncio
async def test_basic_process(
    dummy_transcript,
    dummy_llm,
    dummy_processors,
):
    # goal is to start the server, and send rtc audio to it
    # validate the events received
    from pathlib import Path

    from reflector.settings import settings
    from reflector.tools.process import process_audio_file

    # LLM_BACKEND no longer exists in settings
    # settings.LLM_BACKEND = "test"
    settings.TRANSCRIPT_BACKEND = "whisper"

    # event callback
    marks = {}

    async def event_callback(event):
        if event.processor not in marks:
            marks[event.processor] = 0
        marks[event.processor] += 1

    # invoke the process and capture events
    path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"
    await process_audio_file(path.as_posix(), event_callback, enable_diarization=False)
    print(marks)

    # validate the events
    # Each processor should be called for each audio segment processed
    # The final processors (Topic, Title, Summary) should be called once at the end
    assert marks["TranscriptLinerProcessor"] > 0
    assert marks["TranscriptTranslatorPassthroughProcessor"] > 0
    assert marks["TranscriptTopicDetectorProcessor"] == 1  # Called once at end
    assert marks["TranscriptFinalSummaryProcessor"] == 1  # Called once at end
    assert marks["TranscriptFinalTitleProcessor"] == 1  # Called once at end
