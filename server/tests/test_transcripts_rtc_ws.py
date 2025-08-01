# === further tests
# FIXME test status of transcript
# FIXME test websocket connection after RTC is finished still send the full events
# FIXME try with locked session, RTC should not work

import asyncio
import json
import threading
from pathlib import Path

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from uvicorn import Config, Server


class ThreadedUvicorn:
    def __init__(self, config: Config):
        self.server = Server(config)
        self.thread = threading.Thread(daemon=True, target=self.server.run)

    async def start(self):
        self.thread.start()
        while not self.server.started:
            await asyncio.sleep(0.1)

    def stop(self):
        if self.thread.is_alive():
            self.server.should_exit = True
            while self.thread.is_alive():
                continue


@pytest.fixture
async def appserver(tmpdir, setup_database, celery_session_app, celery_session_worker):
    from reflector.app import app
    from reflector.settings import settings

    DATA_DIR = settings.DATA_DIR
    settings.DATA_DIR = Path(tmpdir)

    # start server
    host = "127.0.0.1"
    port = 1255
    config = Config(app=app, host=host, port=port)
    server = ThreadedUvicorn(config)
    await server.start()

    yield (server, host, port)

    server.stop()
    settings.DATA_DIR = DATA_DIR


@pytest.fixture(scope="session")
def celery_includes():
    return ["reflector.pipelines.main_live_pipeline"]


@pytest.mark.usefixtures("setup_database")
@pytest.mark.usefixtures("celery_session_app")
@pytest.mark.usefixtures("celery_session_worker")
@pytest.mark.asyncio
async def test_transcript_rtc_and_websocket(
    tmpdir,
    dummy_llm,
    dummy_transcript,
    dummy_processors,
    dummy_diarization,
    dummy_storage,
    fake_mp3_upload,
    appserver,
):
    # goal: start the server, exchange RTC, receive websocket events
    # because of that, we need to start the server in a thread
    # to be able to connect with aiortc
    server, host, port = appserver

    # create a transcript
    base_url = f"http://{host}:{port}/v1"
    ac = AsyncClient(base_url=base_url)
    response = await ac.post("/transcripts", json={"name": "Test RTC"})
    assert response.status_code == 200
    tid = response.json()["id"]

    # create a websocket connection as a task
    events = []

    async def websocket_task():
        print("Test websocket: TASK STARTED")
        async with aconnect_ws(f"{base_url}/transcripts/{tid}/events") as ws:
            print("Test websocket: CONNECTED")
            try:
                while True:
                    msg = await ws.receive_json()
                    print(f"Test websocket: JSON {msg}")
                    if msg is None:
                        break
                    events.append(msg)
            except Exception as e:
                print(f"Test websocket: EXCEPTION {e}")
            finally:
                ws.close()
                print("Test websocket: DISCONNECTED")

    websocket_task = asyncio.get_event_loop().create_task(websocket_task())
    print("Test websocket: TASK CREATED", websocket_task)

    # create stream client
    import argparse

    from aiortc.contrib.signaling import add_signaling_arguments, create_signaling

    from reflector.stream_client import StreamClient

    parser = argparse.ArgumentParser()
    add_signaling_arguments(parser)
    args = parser.parse_args(["-s", "tcp-socket"])
    signaling = create_signaling(args)

    url = f"{base_url}/transcripts/{tid}/record/webrtc"
    path = Path(__file__).parent / "records" / "test_short.wav"
    client = StreamClient(signaling, url=url, play_from=path.as_posix())
    await client.start()

    timeout = 20
    while not client.is_ended():
        await asyncio.sleep(1)
        timeout -= 1
        if timeout < 0:
            raise TimeoutError("Timeout while waiting for RTC to end")

    # XXX aiortc is long to close the connection
    # instead of waiting a long time, we just send a STOP
    client.channel.send(json.dumps({"cmd": "STOP"}))
    await client.stop()

    # wait the processing to finish
    timeout = 20
    while True:
        # fetch the transcript and check if it is ended
        resp = await ac.get(f"/transcripts/{tid}")
        assert resp.status_code == 200
        if resp.json()["status"] in ("ended", "error"):
            break
        await asyncio.sleep(1)

    if resp.json()["status"] != "ended":
        raise TimeoutError("Timeout while waiting for transcript to be ended")

    # stop websocket task
    websocket_task.cancel()

    # check events
    assert len(events) > 0
    from pprint import pprint

    pprint(events)

    # get events list
    eventnames = [e["event"] for e in events]

    # check events
    assert "TRANSCRIPT" in eventnames
    ev = events[eventnames.index("TRANSCRIPT")]
    assert ev["data"]["text"].startswith("Hello world.")
    assert ev["data"]["translation"] == "Bonjour le monde"

    assert "TOPIC" in eventnames
    ev = events[eventnames.index("TOPIC")]
    assert ev["data"]["id"]
    assert ev["data"]["summary"] == "LLM SUMMARY"
    assert ev["data"]["transcript"].startswith("Hello world.")
    assert ev["data"]["timestamp"] == 0.0

    assert "FINAL_LONG_SUMMARY" in eventnames
    ev = events[eventnames.index("FINAL_LONG_SUMMARY")]
    assert ev["data"]["long_summary"] == "LLM LONG SUMMARY"

    assert "FINAL_SHORT_SUMMARY" in eventnames
    ev = events[eventnames.index("FINAL_SHORT_SUMMARY")]
    assert ev["data"]["short_summary"] == "LLM SHORT SUMMARY"

    assert "FINAL_TITLE" in eventnames
    ev = events[eventnames.index("FINAL_TITLE")]
    assert ev["data"]["title"] == "Llm Title"

    assert "WAVEFORM" in eventnames
    ev = events[eventnames.index("WAVEFORM")]
    assert isinstance(ev["data"]["waveform"], list)
    assert len(ev["data"]["waveform"]) >= 250
    waveform_resp = await ac.get(f"/transcripts/{tid}/audio/waveform")
    assert waveform_resp.status_code == 200
    assert waveform_resp.headers["content-type"] == "application/json"
    assert isinstance(waveform_resp.json()["data"], list)
    assert len(waveform_resp.json()["data"]) >= 250

    # check status order
    statuses = [e["data"]["value"] for e in events if e["event"] == "STATUS"]
    assert statuses.index("recording") < statuses.index("processing")
    assert statuses.index("processing") < statuses.index("ended")

    # ensure the last event received is ended
    assert events[-1]["event"] == "STATUS"
    assert events[-1]["data"]["value"] == "ended"

    # check on the latest response that the audio duration is > 0
    assert resp.json()["duration"] > 0
    assert "DURATION" in eventnames

    # check that audio/mp3 is available
    audio_resp = await ac.get(f"/transcripts/{tid}/audio/mp3")
    assert audio_resp.status_code == 200
    assert audio_resp.headers["Content-Type"] == "audio/mpeg"


@pytest.mark.usefixtures("setup_database")
@pytest.mark.usefixtures("celery_session_app")
@pytest.mark.usefixtures("celery_session_worker")
@pytest.mark.asyncio
async def test_transcript_rtc_and_websocket_and_fr(
    tmpdir,
    dummy_llm,
    dummy_transcript,
    dummy_processors,
    dummy_diarization,
    dummy_storage,
    fake_mp3_upload,
    ensure_casing,
    nltk,
    appserver,
):
    # goal: start the server, exchange RTC, receive websocket events
    # because of that, we need to start the server in a thread
    # to be able to connect with aiortc
    # with target french language
    server, host, port = appserver

    # create a transcript
    base_url = f"http://{host}:{port}/v1"
    ac = AsyncClient(base_url=base_url)
    response = await ac.post(
        "/transcripts", json={"name": "Test RTC", "target_language": "fr"}
    )
    assert response.status_code == 200
    tid = response.json()["id"]

    # create a websocket connection as a task
    events = []

    async def websocket_task():
        print("Test websocket: TASK STARTED")
        async with aconnect_ws(f"{base_url}/transcripts/{tid}/events") as ws:
            print("Test websocket: CONNECTED")
            try:
                while True:
                    msg = await ws.receive_json()
                    print(f"Test websocket: JSON {msg}")
                    if msg is None:
                        break
                    events.append(msg)
            except Exception as e:
                print(f"Test websocket: EXCEPTION {e}")
            finally:
                ws.close()
                print("Test websocket: DISCONNECTED")

    websocket_task = asyncio.get_event_loop().create_task(websocket_task())
    print("Test websocket: TASK CREATED", websocket_task)

    # create stream client
    import argparse

    from aiortc.contrib.signaling import add_signaling_arguments, create_signaling

    from reflector.stream_client import StreamClient

    parser = argparse.ArgumentParser()
    add_signaling_arguments(parser)
    args = parser.parse_args(["-s", "tcp-socket"])
    signaling = create_signaling(args)

    url = f"{base_url}/transcripts/{tid}/record/webrtc"
    path = Path(__file__).parent / "records" / "test_short.wav"
    client = StreamClient(signaling, url=url, play_from=path.as_posix())
    await client.start()

    timeout = 20
    while not client.is_ended():
        await asyncio.sleep(1)
        timeout -= 1
        if timeout < 0:
            raise TimeoutError("Timeout while waiting for RTC to end")

    # XXX aiortc is long to close the connection
    # instead of waiting a long time, we just send a STOP
    client.channel.send(json.dumps({"cmd": "STOP"}))

    # wait the processing to finish
    await asyncio.sleep(2)

    await client.stop()

    # wait the processing to finish
    timeout = 20
    while True:
        # fetch the transcript and check if it is ended
        resp = await ac.get(f"/transcripts/{tid}")
        assert resp.status_code == 200
        if resp.json()["status"] == "ended":
            break
        await asyncio.sleep(1)

    if resp.json()["status"] != "ended":
        raise TimeoutError("Timeout while waiting for transcript to be ended")

    await asyncio.sleep(2)

    # stop websocket task
    websocket_task.cancel()

    # check events
    assert len(events) > 0
    from pprint import pprint

    pprint(events)

    # get events list
    eventnames = [e["event"] for e in events]

    # check events
    assert "TRANSCRIPT" in eventnames
    ev = events[eventnames.index("TRANSCRIPT")]
    assert ev["data"]["text"].startswith("Hello world.")
    assert ev["data"]["translation"] == "Bonjour le monde"

    assert "TOPIC" in eventnames
    ev = events[eventnames.index("TOPIC")]
    assert ev["data"]["id"]
    assert ev["data"]["summary"] == "LLM SUMMARY"
    assert ev["data"]["transcript"].startswith("Hello world.")
    assert ev["data"]["timestamp"] == 0.0

    assert "FINAL_LONG_SUMMARY" in eventnames
    ev = events[eventnames.index("FINAL_LONG_SUMMARY")]
    assert ev["data"]["long_summary"] == "LLM LONG SUMMARY"

    assert "FINAL_SHORT_SUMMARY" in eventnames
    ev = events[eventnames.index("FINAL_SHORT_SUMMARY")]
    assert ev["data"]["short_summary"] == "LLM SHORT SUMMARY"

    assert "FINAL_TITLE" in eventnames
    ev = events[eventnames.index("FINAL_TITLE")]
    assert ev["data"]["title"] == "LLm Title"

    # check status order
    statuses = [e["data"]["value"] for e in events if e["event"] == "STATUS"]
    assert statuses.index("recording") < statuses.index("processing")
    assert statuses.index("processing") < statuses.index("ended")

    # ensure the last event received is ended
    assert events[-1]["event"] == "STATUS"
    assert events[-1]["data"]["value"] == "ended"
