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
        async def _generate(self, prompt: str, **kwargs) -> str:
            return {
                "title": "TITLE",
                "summary": "SUMMARY",
            }

    LLM.register("test", LLMTest)

    # event callback
    marks = {
        "transcript": 0,
        "topic": 0,
        "summary": 0,
    }

    async def event_callback(event, data):
        print(f"{event}: {data}")
        marks[event] += 1

    # invoke the process and capture events
    path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"
    await process_audio_file(path.as_posix(), event_callback)
    print(marks)

    # validate the events
    assert marks["transcript"] == 5
    assert marks["topic"] == 2
    assert marks["summary"] == 1
