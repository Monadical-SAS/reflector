import asyncio
import io
import json
import time
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor

import jax.numpy as jnp
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from av import AudioFifo
from loguru import logger
from whisper_jax import FlaxWhisperPipline
from gpt4all import GPT4All
from utils.run_utils import run_in_executor

pcs = set()
relay = MediaRelay()
data_channel = None
pipeline = FlaxWhisperPipline("openai/whisper-tiny",
                              dtype=jnp.float16,
                              batch_size=16)

CHANNELS = 2
RATE = 48000
audio_buffer = AudioFifo()
executor = ThreadPoolExecutor()
transcription_text = ""
llm = GPT4All("/Users/gokulmohanarangan/Library/Application Support/nomic.ai/GPT4All/ggml-vicuna-13b-1.1-q4_2.bin")


def get_title_and_summary():
    global transcription_text
    output = None
    if len(transcription_text) > 1000:
        print("Generating title and summary")
        prompt = f"""
        ### Human:
        Create a JSON object having 2 fields: title and summary. For the title field generate a short title for the given
         text and for the summary field, summarize the given text by creating 3 key points.

        {transcription_text}
        
        ### Assistant:
        """
        transcription_text = ""
        output = llm.generate(prompt)
        return str(output)
    return output


def channel_log(channel, t, message):
    print("channel(%s) %s %s" % (channel.label, t, message))


def channel_send(channel, message):
    # channel_log(channel, ">", message)
    if channel and message:
        channel.send(str(message))


def get_transcription(frames):
    print("Transcribing..")
    out_file = io.BytesIO()
    wf = wave.open(out_file, "wb")
    wf.setnchannels(CHANNELS)
    wf.setframerate(RATE)
    wf.setsampwidth(2)

    for frame in frames:
        wf.writeframes(b"".join(frame.to_ndarray()))
    wf.close()
    whisper_result = pipeline(out_file.getvalue(), return_timestamps=True)
    # whisper_result['start_time'] = [f.time for f in frames]
    global transcription_text
    transcription_text += whisper_result["text"]
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
                    lambda f: channel_send(data_channel, whisper_result.result())
                    if f.result()
                    else None
            )
            llm_result = run_in_executor(get_title_and_summary,
                                         executor=executor)
            llm_result.add_done_callback(
                    lambda f: channel_send(data_channel, llm_result.result())
                    if f.result()
                    else None
            )
        return frame


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    log_info("Created for " + request.remote)

    @pc.on("datachannel")
    def on_datachannel(channel):
        global data_channel
        data_channel = channel
        channel_log(channel, "-", "created by remote party")

        @channel.on("message")
        def on_message(message):
            channel_log(channel, "<", message)

            if isinstance(message, str) and message.startswith("ping"):
                channel_send(channel, "pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is " + pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        log_info("Track " + track.kind + " received")
        pc.addTrack(AudioStreamTrack(relay.subscribe(track)))

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.Response(
            content_type="application/json",
            text=json.dumps(
                    {"sdp": pc.localDescription.sdp,
                     "type": pc.localDescription.type}
            ),
    )


async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_post("/offer", offer)
    web.run_app(app, access_log=None, host="127.0.0.1", port=1250)
