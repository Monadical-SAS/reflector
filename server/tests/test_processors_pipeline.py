import pytest


@pytest.mark.asyncio
async def test_basic_process(event_loop):
    # goal is to start the server, and send rtc audio to it
    # validate the events received
    from reflector.tools.process import process_audio_file
    from reflector.settings import settings
    from reflector.llm.base import LLM
    from pathlib import Path

    # use an LLM test backend
    settings.LLM_BACKEND = "test"
    settings.TRANSCRIPT_BACKEND = "whisper"

    class LLMTest(LLM):
        async def _generate(
            self, prompt: str, gen_schema: dict | None, **kwargs
        ) -> str:
            return {
                "title": "TITLE",
                "summary": "SUMMARY",
            }

    LLM.register("test", LLMTest)

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
    assert marks["TranscriptLinerProcessor"] == 5
    assert marks["TranscriptTopicDetectorProcessor"] == 1
    assert marks["TranscriptFinalSummaryProcessor"] == 1
