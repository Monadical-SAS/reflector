import asyncio
import configparser
import datetime
import io
import json
from utils.log_utils import logger
import os
import threading
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor

import jax.numpy as jnp

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import (MediaRelay)
from av import AudioFifo
from sortedcontainers import SortedDict
from whisper_jax import FlaxWhisperPipline

from utils.server_utils import Mutex

ROOT = os.path.dirname(__file__)

config = configparser.ConfigParser()
config.read('config.ini')

WHISPER_MODEL_SIZE = config['DEFAULT']["WHISPER_MODEL_SIZE"]
pcs = set()
relay = MediaRelay()
data_channel = None
sorted_message_queue = SortedDict()

CHANNELS = 2
RATE = 44100
CHUNK_SIZE = 256

audio_buffer = AudioFifo()
pipeline = FlaxWhisperPipline("openai/whisper-" + WHISPER_MODEL_SIZE,
                              dtype=jnp.float16,
                              batch_size=16)

transcription = ""
start_time = datetime.datetime.now()
total_bytes_handled = 0

executor = ThreadPoolExecutor()

frame_lock = Mutex(audio_buffer)


def channel_log(channel, t, message):
    print("channel(%s) %s %s" % (channel.label, t, message))


def thread_queue_channel_send():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        least_time = sorted_message_queue.keys()[0]
        message = sorted_message_queue[least_time]
        if message:
            del sorted_message_queue[least_time]
            data_channel.send(message)
    except Exception as e:
        print("Exception", str(e))
        pass
    loop.run_forever()


def get_transcription():
    while True:
        with frame_lock.lock() as audio_buffer:
            frames = audio_buffer.read_many(CHUNK_SIZE * 960, partial=False)
            if not frames:
                transcribe = False
            else:
                transcribe = True

        if transcribe:
            try:
                sorted_message_queue[frames[0].time] = None
                out_file = io.BytesIO()
                wf = wave.open(out_file, "wb")
                wf.setnchannels(CHANNELS)
                wf.setframerate(RATE)
                wf.setsampwidth(2)

                for frame in frames:
                    wf.writeframes(b''.join(frame.to_ndarray()))
                wf.close()

                whisper_result = pipeline(out_file.getvalue())
                item = {'text': whisper_result["text"],
                        'start_time': str(frames[0].time),
                        'time': str(datetime.datetime.now())
                        }
                sorted_message_queue[frames[0].time] = str(item)
                start_messaging_thread()
            except Exception as e:
                print("Exception -> ", str(e))


class AudioStreamTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "audio"

    def __init__(self, track):
        super().__init__()  # don't forget this!
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        audio_buffer.write(frame)
        return frame


def start_messaging_thread():
    message_thread = threading.Thread(target=thread_queue_channel_send)
    message_thread.start()


def start_transcription_thread(max_threads):
    t_threads = []
    for i in range(max_threads):
        t_thread = threading.Thread(target=get_transcription, args=(i,))
        t_threads.append(t_thread)
        t_thread.start()


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    log_info("Created for %s", request.remote)

    @pc.on("datachannel")
    def on_datachannel(channel):
        global data_channel, start_time
        data_channel = channel
        channel_log(channel, "-", "created by remote party")
        start_time = datetime.datetime.now()

        @channel.on("message")
        def on_message(message):
            channel_log(channel, "<", message)
            if isinstance(message, str) and message.startswith("ping"):
                # reply
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)
        pc.addTrack(AudioStreamTrack(relay.subscribe(track)))

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    start_transcription_thread(6)
    app.router.add_post("/offer", offer)
    web.run_app(
        app, access_log=None, host="127.0.0.1", port=1250
    )
