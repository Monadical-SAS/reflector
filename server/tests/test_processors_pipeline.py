import pytest


@pytest.mark.asyncio
async def test_basic_process(
    event_loop,
    nltk,
    dummy_translate,
    dummy_transcript,
    dummy_llm,
    dummy_processors,
    ensure_casing,
):
    # goal is to start the server, and send rtc audio to it
    # validate the events received
    from reflector.tools.process import process_audio_file
    from reflector.settings import settings
    from pathlib import Path

    # use an LLM test backend
    settings.LLM_BACKEND = "test"
    settings.TRANSCRIPT_BACKEND = "whisper"

    # event callback
    marks = {}

    async def event_callback(event):
        if event.processor not in marks:
            marks[event.processor] = 0
        marks[event.processor] += 1

    # invoke the process and capture events
    path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"
    await process_audio_file(path.as_posix(), event_callback)
    print(marks)

    # validate the events
    print(1, marks["TranscriptLinerProcessor"])
    assert marks["TranscriptLinerProcessor"] == 4
    print(2, marks["TranscriptTranslatorProcessor"])
    assert marks["TranscriptTranslatorProcessor"] == 4
    print(3, marks["TranscriptTopicDetectorProcessor"])
    assert marks["TranscriptTopicDetectorProcessor"] == 1
    print(4, marks["TranscriptFinalLongSummaryProcessor"])
    assert marks["TranscriptFinalLongSummaryProcessor"] == 1
    print(5, marks["TranscriptFinalShortSummaryProcessor"])
    assert marks["TranscriptFinalShortSummaryProcessor"] == 1
    print(6, marks["TranscriptFinalTitleProcessor"])
    assert marks["TranscriptFinalTitleProcessor"] == 1
