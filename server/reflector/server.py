import argparse
import asyncio
import datetime
import json
import os
import wave
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import NoReturn, Union

import aiohttp_cors
import av
import requests
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from faster_whisper import WhisperModel

from reflector.models import (
    BlackListedMessages,
    FinalSummaryResult,
    ParseLLMResult,
    TitleSummaryInput,
    TitleSummaryOutput,
    TranscriptionInput,
    TranscriptionOutput,
    TranscriptionContext,
)
from reflector.logger import logger
from reflector.utils.run_utils import run_in_executor
from reflector.settings import settings

# WebRTC components
pcs = set()
relay = MediaRelay()
executor = ThreadPoolExecutor()

# Transcription model
model = WhisperModel("tiny", device="cpu", compute_type="float32", num_workers=12)

# LLM
LLM_URL = settings.LLM_URL
if not LLM_URL:
    assert settings.LLM_BACKEND == "oobagooda"
    LLM_URL = f"http://{settings.LLM_HOST}:{settings.LLM_PORT}/api/v1/generate"
logger.info(f"Using LLM [{settings.LLM_BACKEND}]: {LLM_URL}")


def parse_llm_output(
    param: TitleSummaryInput, response: requests.Response
) -> Union[None, ParseLLMResult]:
    """
    Function to parse the LLM response
    :param param:
    :param response:
    :return:
    """
    try:
        output = json.loads(response.json()["results"][0]["text"])
        return ParseLLMResult(param, output)
    except Exception:
        logger.exception("Exception while parsing LLM output")
        return None


def get_title_and_summary(
    ctx: TranscriptionContext, param: TitleSummaryInput
) -> Union[None, TitleSummaryOutput]:
    """
    From the input provided (transcript), query the LLM to generate
    topics and summaries
    :param param:
    :return:
    """
    logger.info("Generating title and summary")

    # TODO : Handle unexpected output formats from the model
    try:
        response = requests.post(LLM_URL, headers=param.headers, json=param.data)
        output = parse_llm_output(param, response)
        if output:
            result = output.get_result()
            ctx.incremental_responses.append(result)
            return TitleSummaryOutput(ctx.incremental_responses)
    except Exception:
        logger.exception("Exception while generating title and summary")
        return None


def channel_send(channel, message: str) -> NoReturn:
    """
    Send text messages via the data channel
    :param channel:
    :param message:
    :return:
    """
    if channel:
        channel.send(message)


def channel_send_increment(
    channel, param: Union[FinalSummaryResult, TitleSummaryOutput]
) -> NoReturn:
    """
    Send the incremental topics and summaries via the data channel
    :param channel:
    :param param:
    :return:
    """
    if channel and param:
        message = param.get_result()
        channel.send(json.dumps(message))


def channel_send_transcript(ctx: TranscriptionContext) -> NoReturn:
    """
    Send the transcription result via the data channel
    :param channel:
    :return:
    """
    if not ctx.data_channel:
        return
    try:
        least_time = next(iter(ctx.sorted_transcripts))
        message = ctx.sorted_transcripts[least_time].get_result()
        if message:
            del ctx.sorted_transcripts[least_time]
            if message["text"] not in BlackListedMessages.messages:
                ctx.data_channel.send(json.dumps(message))
        # Due to exceptions if one of the earlier batches can't return
        # a transcript, we don't want to be stuck waiting for the result
        # With the threshold size of 3, we pop the first(lost) element
        else:
            if len(ctx.sorted_transcripts) >= 3:
                del ctx.sorted_transcripts[least_time]
    except Exception:
        logger.exception("Exception while sending transcript")


def get_transcription(
    ctx: TranscriptionContext, input_frames: TranscriptionInput
) -> Union[None, TranscriptionOutput]:
    """
    From the collected audio frames create transcription by inferring from
    the chosen transcription model
    :param input_frames:
    :return:
    """
    ctx.logger.info("Transcribing..")
    ctx.sorted_transcripts[input_frames.frames[0].time] = None

    # TODO: Find cleaner way, watch "no transcription" issue below
    # Passing IO objects instead of temporary files throws an error
    # Passing ndarray (type casted with float) does not give any
    # transcription. Refer issue,
    # https://github.com/guillaumekln/faster-whisper/issues/369
    audio_file = "test" + str(datetime.datetime.now())
    wf = wave.open(audio_file, "wb")
    wf.setnchannels(settings.AUDIO_CHANNELS)
    wf.setframerate(settings.AUDIO_SAMPLING_RATE)
    wf.setsampwidth(settings.AUDIO_SAMPLING_WIDTH)

    for frame in input_frames.frames:
        wf.writeframes(b"".join(frame.to_ndarray()))
    wf.close()

    result_text = ""

    try:
        segments, _ = model.transcribe(
            audio_file,
            language="en",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        os.remove(audio_file)
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
            duration += end_time - start_time

        ctx.last_transcribed_time += duration
        ctx.transcription_text += result_text

    except Exception:
        logger.exception("Exception while transcribing")

    result = TranscriptionOutput(result_text)
    ctx.sorted_transcripts[input_frames.frames[0].time] = result
    return result


def get_final_summary_response(ctx: TranscriptionContext) -> FinalSummaryResult:
    """
    Collate the incremental summaries generated so far and return as the final
    summary
    :return:
    """
    final_summary = ""

    # Collate inc summaries
    for topic in ctx.incremental_responses:
        final_summary += topic["description"]

    response = FinalSummaryResult(final_summary, ctx.last_transcribed_time)

    with open(
        "./artefacts/meeting_titles_and_summaries.txt", "a", encoding="utf-8"
    ) as file:
        file.write(json.dumps(ctx.incremental_responses))

    return response


class AudioStreamTrack(MediaStreamTrack):
    """
    An audio stream track.
    """

    kind = "audio"

    def __init__(self, ctx: TranscriptionContext, track):
        super().__init__()
        self.ctx = ctx
        self.track = track
        self.audio_buffer = av.AudioFifo()

    async def recv(self) -> av.audio.frame.AudioFrame:
        ctx = self.ctx
        frame = await self.track.recv()
        self.audio_buffer.write(frame)

        if local_frames := self.audio_buffer.read_many(
            settings.AUDIO_BUFFER_SIZE, partial=False
        ):
            whisper_result = run_in_executor(
                get_transcription,
                ctx,
                TranscriptionInput(local_frames),
                executor=executor,
            )
            whisper_result.add_done_callback(
                lambda f: channel_send_transcript(ctx) if f.result() else None
            )

        if len(ctx.transcription_text) > 25:
            llm_input_text = ctx.transcription_text
            ctx.transcription_text = ""
            param = TitleSummaryInput(
                input_text=llm_input_text, transcribed_time=ctx.last_transcribed_time
            )
            llm_result = run_in_executor(
                get_title_and_summary, ctx, param, executor=executor
            )
            llm_result.add_done_callback(
                lambda f: channel_send_increment(ctx.data_channel, llm_result.result())
                if f.result()
                else None
            )
        return frame


async def offer(request: requests.Request) -> web.Response:
    """
    Establish the WebRTC connection with the client
    :param request:
    :return:
    """
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # client identification
    peername = request.transport.get_extra_info("peername")
    if peername is not None:
        clientid = f"{peername[0]}:{peername[1]}"
    else:
        clientid = uuid.uuid4()

    # create a context for the whole rtc transaction
    # add a customised logger to the context
    ctx = TranscriptionContext(logger=logger.bind(client=clientid))

    # handle RTC peer connection
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("datachannel")
    def on_datachannel(channel) -> NoReturn:
        ctx.data_channel = channel
        ctx.logger = ctx.logger.bind(channel=channel.label)
        ctx.logger.info("Channel created by remote party")

        @channel.on("message")
        def on_message(message: str) -> NoReturn:
            ctx.logger.info(f"Message: {message}")
            if json.loads(message)["cmd"] == "STOP":
                # Placeholder final summary
                response = get_final_summary_response()
                channel_send_increment(channel, response)
                # To-do Add code to stop connection from server side here
                # But have to handshake with client once

            if isinstance(message, str) and message.startswith("ping"):
                channel_send(channel, "pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> NoReturn:
        ctx.logger.info(f"Connection state changed: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track) -> NoReturn:
        ctx.logger.info(f"Track {track.kind} received")
        pc.addTrack(AudioStreamTrack(ctx, relay.subscribe(track)))

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def on_shutdown(application: web.Application) -> NoReturn:
    """
    On shutdown, the coroutines that shutdown client connections are
    executed
    :param application:
    :return:
    """
    coroutines = [pc.close() for pc in pcs]
    await asyncio.gather(*coroutines)
    pcs.clear()


def create_app() -> web.Application:
    """
    Create the web application
    """
    app = web.Application()
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True, expose_headers="*", allow_headers="*"
            )
        },
    )

    offer_resource = cors.add(app.router.add_resource("/offer"))
    cors.add(offer_resource.add_route("POST", offer))
    app.on_shutdown.append(on_shutdown)
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC based server for Reflector")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Server host IP (def: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=1250, help="Server port (def: 1250)"
    )
    args = parser.parse_args()
    app = create_app()
    web.run_app(app, access_log=None, host=args.host, port=args.port)
