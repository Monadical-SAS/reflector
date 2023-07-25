import argparse
import asyncio
import datetime
import json
import os
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor

import aiohttp_cors
import requests
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from av import AudioFifo
from faster_whisper import WhisperModel
from loguru import logger
from sortedcontainers import SortedDict

from utils.run_utils import run_in_executor, config

pcs = set()
relay = MediaRelay()
data_channel = None
model = WhisperModel("tiny", device="cpu",
                     compute_type="float32",
                     num_workers=12)

CHANNELS = 2
RATE = 48000
audio_buffer = AudioFifo()
executor = ThreadPoolExecutor()
transcription_text = ""
last_transcribed_time = 0.0
LLM_MACHINE_IP = config["DEFAULT"]["LLM_MACHINE_IP"]
LLM_MACHINE_PORT = config["DEFAULT"]["LLM_MACHINE_PORT"]
LLM_URL = f"http://{LLM_MACHINE_IP}:{LLM_MACHINE_PORT}/api/v1/generate"
incremental_responses = []
sorted_transcripts = SortedDict()

blacklisted_messages = [" Thank you.", " See you next time!",
                        " Thank you for watching!", " Bye!",
                        " And that's what I'm talking about."]


def get_title_and_summary(llm_input_text, last_timestamp):
    logger.info("Generating title and summary")
    # output = llm.generate(prompt)

    # Use monadical-ml to fire this query to an LLM and get result
    headers = {
            "Content-Type": "application/json"
    }

    prompt = f"""
        ### Human:
        Create a JSON object as response. The JSON object must have 2 fields:
        i) title and ii) summary. For the title field,generate a short title
        for the given text. For the summary field, summarize the given text
        in three sentences.

        {llm_input_text}

        ### Assistant:
        """

    data = {
            "prompt": prompt
    }

    # TODO : Handle unexpected output formats from the model
    try:
        response = requests.post(LLM_URL, headers=headers, json=data)
        output = json.loads(response.json()["results"][0]["text"])
        output["description"] = output.pop("summary")
        output["transcript"] = llm_input_text
        output["timestamp"] = \
            str(datetime.timedelta(seconds=round(last_timestamp)))
        incremental_responses.append(output)
        result = {
                "cmd": "UPDATE_TOPICS",
                "topics": incremental_responses,
        }

    except Exception as e:
        logger.info("Exception" + str(e))
        result = None
    return result


def channel_log(channel, t, message):
    logger.info("channel(%s) %s %s" % (channel.label, t, message))


def channel_send(channel, message):
    if channel:
        channel.send(message)


def channel_send_increment(channel, message):
    if channel and message:
        channel.send(json.dumps(message))


def channel_send_transcript(channel):
    # channel_log(channel, ">", message)
    if channel:
        try:
            least_time = sorted_transcripts.keys()[0]
            message = sorted_transcripts[least_time]
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


def get_transcription(frames):
    logger.info("Transcribing..")
    sorted_transcripts[frames[0].time] = None

    # TODO:
    # Passing IO objects instead of temporary files throws an error
    # Passing ndarrays (typecasted with float) does not give any
    # transcription. Refer issue,
    # https://github.com/guillaumekln/faster-whisper/issues/369
    audiofilename = "test" + str(datetime.datetime.now())
    wf = wave.open(audiofilename, "wb")
    wf.setnchannels(CHANNELS)
    wf.setframerate(RATE)
    wf.setsampwidth(2)

    for frame in frames:
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

    result = {
            "cmd": "SHOW_TRANSCRIPTION",
            "text": result_text
    }
    sorted_transcripts[frames[0].time] = result
    return result


def get_final_summary_response():
    final_summary = ""

    # Collate inc summaries
    for topic in incremental_responses:
        final_summary += topic["description"]

    response = {
            "cmd": "DISPLAY_FINAL_SUMMARY",
            "duration": str(datetime.timedelta(
                    seconds=round(last_transcribed_time))),
            "summary": final_summary
    }

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

    async def recv(self):
        global transcription_text
        frame = await self.track.recv()
        audio_buffer.write(frame)

        if local_frames := audio_buffer.read_many(256 * 960, partial=False):
            whisper_result = run_in_executor(
                    get_transcription, local_frames, executor=executor
            )
            whisper_result.add_done_callback(
                    lambda f: channel_send_transcript(data_channel)
                    if f.result()
                    else None
            )

        if len(transcription_text) > 750:
            llm_input_text = transcription_text
            transcription_text = ""
            llm_result = run_in_executor(get_title_and_summary,
                                         llm_input_text,
                                         last_transcribed_time,
                                         executor=executor)
            llm_result.add_done_callback(
                    lambda f: channel_send_increment(data_channel,
                                                     llm_result.result())
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
            if json.loads(message)["cmd"] == "STOP":
                # Place holder final summary
                response = get_final_summary_response()
                channel_send_increment(data_channel, response)
                # To-do Add code to stop connection from server side here
                # But have to handshake with client once
                # pc.close()

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
    web.run_app(app, access_log=None,  host=args.host, port=args.port)
