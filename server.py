import argparse
import asyncio
import datetime
import json
import os
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from typing import Any, NoReturn

import aiohttp_cors
import av
import requests
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from faster_whisper import WhisperModel
from loguru import logger
from sortedcontainers import SortedDict

from reflector_dataclasses import FinalSummaryResult, ParseLLMResult,\
    TitleSummaryInput, TitleSummaryOutput, TranscriptionInput,\
    TranscriptionOutput
from utils.run_utils import config, run_in_executor

pcs = set()
relay = MediaRelay()
data_channel = None
model = WhisperModel("tiny", device="cpu",
                     compute_type="float32",
                     num_workers=12)

CHANNELS = 2
RATE = 48000
audio_buffer = av.AudioFifo()
executor = ThreadPoolExecutor()
transcription_text = ""
last_transcribed_time = 0.0
LLM_MACHINE_IP = config["LLM"]["LLM_MACHINE_IP"]
LLM_MACHINE_PORT = config["LLM"]["LLM_MACHINE_PORT"]
LLM_URL = f"http://{LLM_MACHINE_IP}:{LLM_MACHINE_PORT}/api/v1/generate"
incremental_responses = []
sorted_transcripts = SortedDict()


def parse_llm_output(param: TitleSummaryInput, response: requests.Response) -> Any[None, ParseLLMResult]:
    try:
        output = json.loads(response.json()["results"][0]["text"])
        return ParseLLMResult(param, output)
    except Exception as e:
        logger.info("Exception" + str(e))
        return None


def get_title_and_summary(param: TitleSummaryInput) -> Any[None, TitleSummaryOutput]:
    logger.info("Generating title and summary")

    # TODO : Handle unexpected output formats from the model
    try:
        response = requests.post(LLM_URL,
                                 headers=param.headers,
                                 json=param.data)
        output = parse_llm_output(param, response)
        if output:
            result = output.get_result()
            incremental_responses.append(result)
            return TitleSummaryOutput(incremental_responses)
    except Exception as e:
        logger.info("Exception" + str(e))
        return None


def channel_log(channel, t: str, message: str) -> NoReturn:
    logger.info("channel(%s) %s %s" % (channel.label, t, message))


def channel_send(channel, message: str) -> NoReturn:
    if channel:
        channel.send(message)


def channel_send_increment(channel, param: Any[FinalSummaryResult, TitleSummaryOutput]) -> NoReturn:
    if channel and param:
        message = param.get_result()
        channel.send(json.dumps(message))


def channel_send_transcript(channel) -> NoReturn:
    # channel_log(channel, ">", message)
    if channel:
        try:
            least_time = sorted_transcripts.keys()[0]
            message = sorted_transcripts[least_time].get_result()
            if message:
                del sorted_transcripts[least_time]
                if message["text"] not in blacklisted_messages:
                    channel.send(json.dumps(message))
            # Due to exceptions if one of the earlier batches can't return
            # a transcript, we don't want to be stuck waiting for the result
            # With the threshold size of 3, we pop the first(lost) element
            else:
                if len(sorted_transcripts) >= 3:
                    del sorted_transcripts[least_time]
        except Exception as e:
            logger.info("Exception", str(e))
            pass


def get_transcription(input_frames: TranscriptionInput) -> Any[None, TranscriptionOutput]:
    logger.info("Transcribing..")
    sorted_transcripts[input_frames[0].time] = None

    # TODO: Find cleaner way, watch "no transcription" issue below
    # Passing IO objects instead of temporary files throws an error
    # Passing ndarrays (typecasted with float) does not give any
    # transcription. Refer issue,
    # https://github.com/guillaumekln/faster-whisper/issues/369
    audiofilename = "test" + str(datetime.datetime.now())
    wf = wave.open(audiofilename, "wb")
    wf.setnchannels(CHANNELS)
    wf.setframerate(RATE)
    wf.setsampwidth(2)

    for frame in input_frames.frames:
        wf.writeframes(b"".join(frame.to_ndarray()))
    wf.close()

    result_text = ""

    try:
        segments, _ = \
            model.transcribe(audiofilename,
                             language="en",
                             beam_size=5,
                             vad_filter=True,
                             vad_parameters=dict(min_silence_duration_ms=500))
        os.remove(audiofilename)
        segments = list(segments)
        result_text = ""
        duration = 0.0
        for segment in segments:
            result_text += segment.text
            start_time = segment.start
            end_time = segment.end
            if not segment.start:
                start_time = 0.0
            if not segment.end:
                end_time = 5.5
            duration += (end_time - start_time)

        global last_transcribed_time, transcription_text
        last_transcribed_time += duration
        transcription_text += result_text

    except Exception as e:
        logger.info("Exception" + str(e))
        pass

    result = TranscriptionOutput(result_text)
    sorted_transcripts[input_frames.frames[0].time] = result
    return result


def get_final_summary_response() -> FinalSummaryResult:
    final_summary = ""

    # Collate inc summaries
    for topic in incremental_responses:
        final_summary += topic["description"]

    response = FinalSummaryResult(final_summary, last_transcribed_time)

    with open("./artefacts/meeting_titles_and_summaries.txt", "a") as f:
        f.write(json.dumps(incremental_responses))

    return response


class AudioStreamTrack(MediaStreamTrack):
    """
    An audio stream track.
    """

    kind = "audio"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self) -> av.audio.frame.AudioFrame:
        global transcription_text
        frame = await self.track.recv()
        audio_buffer.write(frame)

        if local_frames := audio_buffer.read_many(256 * 960, partial=False):
            whisper_result = run_in_executor(
                    get_transcription,
                    TranscriptionInput(local_frames),
                    executor=executor
            )
            whisper_result.add_done_callback(
                    lambda f: channel_send_transcript(data_channel)
                    if f.result()
                    else None
            )

        if len(transcription_text) > 25:
            llm_input_text = transcription_text
            transcription_text = ""
            param = TitleSummaryInput(input_text=llm_input_text,
                                      transcribed_time=last_transcribed_time)
            llm_result = run_in_executor(get_title_and_summary,
                                         param,
                                         executor=executor)
            llm_result.add_done_callback(
                    lambda f: channel_send_increment(data_channel,
                                                     llm_result.result())
                    if f.result()
                    else None
            )
        return frame


async def offer(request: requests.Request) -> web.Response:
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args) -> NoReturn:
        logger.info(pc_id + " " + msg, *args)

    log_info("Created for " + request.remote)

    @pc.on("datachannel")
    def on_datachannel(channel) -> NoReturn:
        global data_channel
        data_channel = channel
        channel_log(channel, "-", "created by remote party")

        @channel.on("message")
        def on_message(message: str) -> NoReturn:
            channel_log(channel, "<", message)
            if json.loads(message)["cmd"] == "STOP":
                # Placeholder final summary
                response = get_final_summary_response()
                channel_send_increment(data_channel, response)
                # To-do Add code to stop connection from server side here
                # But have to handshake with client once

            if isinstance(message, str) and message.startswith("ping"):
                channel_send(channel, "pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> NoReturn:
        log_info("Connection state is " + pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track) -> NoReturn:
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


async def on_shutdown(app) -> NoReturn:
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description="WebRTC based server for Reflector"
    )
    parser.add_argument(
            "--host", default="0.0.0.0", help="Server host IP (def: 0.0.0.0)"
    )
    parser.add_argument(
            "--port", type=int, default=1250, help="Server port (def: 1250)"
    )
    args = parser.parse_args()
    app = web.Application()
    cors = aiohttp_cors.setup(
            app,
            defaults={
                    "*": aiohttp_cors.ResourceOptions(
                            allow_credentials=True,
                            expose_headers="*",
                            allow_headers="*"
                    )
            },
    )

    offer_resource = cors.add(app.router.add_resource("/offer"))
    cors.add(offer_resource.add_route("POST", offer))
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, access_log=None, host=args.host, port=args.port)
