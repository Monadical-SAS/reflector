import asyncio
from enum import StrEnum
from json import dumps, loads
from pathlib import Path

import av
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter, Request
from prometheus_client import Gauge
from pydantic import BaseModel
from reflector.events import subscribers_shutdown
from reflector.logger import logger
from reflector.processors import (
    AudioChunkerProcessor,
    AudioFileWriterProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    FinalLongSummary,
    FinalShortSummary,
    Pipeline,
    TitleSummary,
    Transcript,
    TranscriptFinalLongSummaryProcessor,
    TranscriptFinalShortSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptTranslatorProcessor,
)
from reflector.processors.base import BroadcastProcessor
from reflector.processors.types import FinalTitle

sessions = []
router = APIRouter()
m_rtc_sessions = Gauge("rtc_sessions", "Number of active RTC sessions")


class TranscriptionContext(object):
    def __init__(self, logger):
        self.logger = logger
        self.pipeline = None
        self.data_channel = None
        self.status = "idle"
        self.topics = []


class AudioStreamTrack(MediaStreamTrack):
    """
    An audio stream track.
    """

    kind = "audio"

    def __init__(self, ctx: TranscriptionContext, track):
        super().__init__()
        self.ctx = ctx
        self.track = track

    async def recv(self) -> av.audio.frame.AudioFrame:
        ctx = self.ctx
        frame = await self.track.recv()
        try:
            await ctx.pipeline.push(frame)
        except Exception as e:
            ctx.logger.error("Pipeline error", error=e)
        return frame


class RtcOffer(BaseModel):
    sdp: str
    type: str


class StrValue(BaseModel):
    value: str


class PipelineEvent(StrEnum):
    TRANSCRIPT = "TRANSCRIPT"
    TOPIC = "TOPIC"
    FINAL_LONG_SUMMARY = "FINAL_LONG_SUMMARY"
    STATUS = "STATUS"
    FINAL_SHORT_SUMMARY = "FINAL_SHORT_SUMMARY"
    FINAL_TITLE = "FINAL_TITLE"


async def rtc_offer_base(
    params: RtcOffer,
    request: Request,
    event_callback=None,
    event_callback_args=None,
    audio_filename: Path | None = None,
    source_language: str = "en",
    target_language: str = "en",
):
    # build an rtc session
    offer = RTCSessionDescription(sdp=params.sdp, type=params.type)

    # client identification
    peername = request.client
    clientid = f"{peername[0]}:{peername[1]}"
    ctx = TranscriptionContext(logger=logger.bind(client=clientid))

    async def update_status(status: str):
        changed = ctx.status != status
        if changed:
            ctx.status = status
            if event_callback:
                await event_callback(
                    event=PipelineEvent.STATUS,
                    args=event_callback_args,
                    data=StrValue(value=status),
                )

    # build pipeline callback
    async def on_transcript(transcript: Transcript):
        ctx.logger.info("Transcript", transcript=transcript)

        # send to RTC
        if ctx.data_channel.readyState == "open":
            result = {
                "cmd": "SHOW_TRANSCRIPTION",
                "text": transcript.text,
            }
            ctx.data_channel.send(dumps(result))

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.TRANSCRIPT,
                args=event_callback_args,
                data=transcript,
            )

    async def on_topic(topic: TitleSummary):
        # FIXME: make it incremental with the frontend, not send everything
        ctx.logger.info("Topic", topic=topic)
        ctx.topics.append(
            {
                "title": topic.title,
                "timestamp": topic.timestamp,
                "transcript": topic.transcript.text,
                "desc": topic.summary,
            }
        )

        # send to RTC
        if ctx.data_channel.readyState == "open":
            result = {"cmd": "UPDATE_TOPICS", "topics": ctx.topics}
            ctx.data_channel.send(dumps(result))

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.TOPIC, args=event_callback_args, data=topic
            )

    async def on_final_short_summary(summary: FinalShortSummary):
        ctx.logger.info("FinalShortSummary", final_short_summary=summary)

        # send to RTC
        if ctx.data_channel.readyState == "open":
            result = {
                "cmd": "DISPLAY_FINAL_SHORT_SUMMARY",
                "summary": summary.short_summary,
                "duration": summary.duration,
            }
            ctx.data_channel.send(dumps(result))

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.FINAL_SHORT_SUMMARY,
                args=event_callback_args,
                data=summary,
            )

    async def on_final_long_summary(summary: FinalLongSummary):
        ctx.logger.info("FinalLongSummary", final_summary=summary)

        # send to RTC
        if ctx.data_channel.readyState == "open":
            result = {
                "cmd": "DISPLAY_FINAL_LONG_SUMMARY",
                "summary": summary.long_summary,
                "duration": summary.duration,
            }
            ctx.data_channel.send(dumps(result))

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.FINAL_LONG_SUMMARY,
                args=event_callback_args,
                data=summary,
            )

    async def on_final_title(title: FinalTitle):
        ctx.logger.info("FinalTitle", final_title=title)

        # send to RTC
        if ctx.data_channel.readyState == "open":
            result = {"cmd": "DISPLAY_FINAL_TITLE", "title": title.title}
            ctx.data_channel.send(dumps(result))

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.FINAL_TITLE,
                args=event_callback_args,
                data=title,
            )

    # create a context for the whole rtc transaction
    # add a customised logger to the context
    processors = []
    if audio_filename is not None:
        processors += [AudioFileWriterProcessor(path=audio_filename)]
    processors += [
        AudioChunkerProcessor(),
        AudioMergeProcessor(),
        AudioTranscriptAutoProcessor.as_threaded(),
        TranscriptLinerProcessor(),
        TranscriptTranslatorProcessor.as_threaded(callback=on_transcript),
        TranscriptTopicDetectorProcessor.as_threaded(callback=on_topic),
        BroadcastProcessor(
            processors=[
                TranscriptFinalTitleProcessor.as_threaded(callback=on_final_title),
                TranscriptFinalLongSummaryProcessor.as_threaded(
                    callback=on_final_long_summary
                ),
                TranscriptFinalShortSummaryProcessor.as_threaded(
                    callback=on_final_short_summary
                ),
            ]
        ),
    ]
    ctx.pipeline = Pipeline(*processors)
    ctx.pipeline.set_pref("audio:source_language", source_language)
    ctx.pipeline.set_pref("audio:target_language", target_language)

    # handle RTC peer connection
    pc = RTCPeerConnection()

    async def flush_pipeline_and_quit(close=True):
        # may be called twice
        # 1. either the client ask to sotp the meeting
        #    - we flush and close
        #    - when we receive the close event, we do nothing.
        # 2. or the client close the connection
        #    and there is nothing to do because it is already closed
        await update_status("processing")
        await ctx.pipeline.flush()
        if close:
            ctx.logger.debug("Closing peer connection")
            await pc.close()
            await update_status("ended")
            if pc in sessions:
                sessions.remove(pc)
                m_rtc_sessions.dec()

    @pc.on("datachannel")
    def on_datachannel(channel):
        ctx.data_channel = channel
        ctx.logger = ctx.logger.bind(channel=channel.label)
        ctx.logger.info("Channel created by remote party")

        @channel.on("message")
        def on_message(message: str):
            ctx.logger.info(f"Message: {message}")
            if loads(message)["cmd"] == "STOP":
                ctx.logger.debug("STOP command received")
                asyncio.get_event_loop().create_task(flush_pipeline_and_quit())

            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        ctx.logger.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()
        elif pc.connectionState == "closed":
            await flush_pipeline_and_quit(close=False)

    @pc.on("track")
    def on_track(track):
        ctx.logger.info(f"Track {track.kind} received")
        pc.addTrack(AudioStreamTrack(ctx, track))
        asyncio.get_event_loop().create_task(update_status("recording"))

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    sessions.append(pc)

    # update metrics
    m_rtc_sessions.inc()

    return RtcOffer(sdp=pc.localDescription.sdp, type=pc.localDescription.type)


@subscribers_shutdown.append
async def rtc_clean_sessions(_):
    logger.info("Closing all RTC sessions")
    for pc in sessions:
        logger.debug(f"Closing session {pc}")
        await pc.close()
    sessions.clear()


@router.post("/offer")
async def rtc_offer(params: RtcOffer, request: Request):
    return await rtc_offer_base(params, request)
