import asyncio
import datetime
import io
import json
import logging
import sys
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor

import jax.numpy as jnp
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from av import AudioFifo
from whisper_jax import FlaxWhisperPipline

from reflector.utils.server_utils import run_in_executor

logger = logging.getLogger(__name__)

transcription = ""

pcs = set()
relay = MediaRelay()
data_channel = None
total_bytes_handled = 0
pipeline = FlaxWhisperPipline("openai/whisper-tiny", dtype=jnp.float16, batch_size=16)

CHANNELS = 2
RATE = 48000
audio_buffer = AudioFifo()
start_time = datetime.datetime.now()
executor = ThreadPoolExecutor()


def channel_log(channel, t, message):
    print("channel(%s) %s %s" % (channel.label, t, message))


def channel_send(channel, message):
    # channel_log(channel, ">", message)
    global start_time
    if channel:
        channel.send(message)
        print(
            "Bytes handled :",
            total_bytes_handled,
            " Time : ",
            datetime.datetime.now() - start_time,
        )


def get_transcription(frames):
    print("Transcribing..")
    # samples = np.ndarray(
    #     np.concatenate([f.to_ndarray() for f in frames], axis=None),
    #     dtype=np.float32,
    # )
    # whisper_result = pipeline(
    #     {
    #         "array": samples,
    #         "sampling_rate": 48000,
    #     },
    #     return_timestamps=True,
    # )
    out_file = io.BytesIO()
    wf = wave.open(out_file, "wb")
    wf.setnchannels(CHANNELS)
    wf.setframerate(RATE)
    wf.setsampwidth(2)

    for frame in frames:
        wf.writeframes(b"".join(frame.to_ndarray()))
    wf.close()
    global total_bytes_handled
    total_bytes_handled += sys.getsizeof(wf)
    whisper_result = pipeline(out_file.getvalue(), return_timestamps=True)
    with open("test_exec.txt", "a") as f:
        f.write(whisper_result["text"])
    whisper_result['start_time'] = [f.time for f in frames]
    return whisper_result


class AudioStreamTrack(MediaStreamTrack):
    """
    An audio stream track.
    """

    kind = "audio"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        audio_buffer.write(frame)
        if local_frames := audio_buffer.read_many(256 * 960, partial=False):
            whisper_result = run_in_executor(
                get_transcription, local_frames, executor=executor
            )
            whisper_result.add_done_callback(
                lambda f: channel_send(data_channel, str(whisper_result.result()))
                if (f.result())
                else None
            )
        return frame


async def offer(request):
    params = await request.json()
    print("Request received")
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
                channel_send(channel, "pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        print("Track %s received" % track.kind)
        log_info("Track %s received", track.kind)
        # Trials to listen to the correct track
        pc.addTrack(AudioStreamTrack(relay.subscribe(track)))
        # pc.addTrack(AudioStreamTrack(track))

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    print("Response sent")
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_post("/offer", offer)
    web.run_app(app, access_log=None, host="127.0.0.1", port=1250)
