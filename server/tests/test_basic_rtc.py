import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_basic_rtc_server(aiohttp_server, event_loop):
    # goal is to start the server, and send rtc audio to it
    # validate the events received
    import argparse
    import json
    from pathlib import Path
    from reflector.server import create_app
    from reflector.stream_client import StreamClient
    from reflector.models import TitleSummaryOutput
    from aiortc.contrib.signaling import add_signaling_arguments, create_signaling

    # customize settings to have a mock LLM server
    with patch("reflector.server.get_title_and_summary") as mock_llm:
        # any response from mock_llm will be test topic
        mock_llm.return_value = TitleSummaryOutput(["topic_test"])

        # create the server
        app = create_app()
        server = await aiohttp_server(app)
        url = f"http://{server.host}:{server.port}/offer"

        # create signaling
        parser = argparse.ArgumentParser()
        add_signaling_arguments(parser)
        args = parser.parse_args(["-s", "tcp-socket"])
        signaling = create_signaling(args)

        # create the client
        path = Path(__file__).parent / "records" / "test_mathieu_hello.wav"
        client = StreamClient(signaling, url=url, play_from=path.as_posix())
        await client.start()

        # we just want the first transcription
        # and topic update messages

        marks = {
            "SHOW_TRANSCRIPTION": False,
            "UPDATE_TOPICS": False,
        }

        async for rawmsg in client.get_reader():
            msg = json.loads(rawmsg)
            cmd = msg["cmd"]
            if cmd == "SHOW_TRANSCRIPTION":
                assert "text" in msg
                assert "want to share my incredible experience" in msg["text"]
            elif cmd == "UPDATE_TOPICS":
                assert "topics" in msg
                assert "topic_test" in msg["topics"]
            marks[cmd] = True

            # break if we have all the events we need
            if all(marks.values()):
                break

        # stop the server
        await server.close()
        await client.stop()



