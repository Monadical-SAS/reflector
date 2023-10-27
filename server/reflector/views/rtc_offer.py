import asyncio
from json import loads

import av
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter, Request
from prometheus_client import Gauge
from pydantic import BaseModel
from reflector.events import subscribers_shutdown
from reflector.logger import logger
from reflector.pipelines.runner import PipelineRunner

sessions = []
router = APIRouter()
m_rtc_sessions = Gauge("rtc_sessions", "Number of active RTC sessions")


class TranscriptionContext(object):
    def __init__(self, logger):
        self.logger = logger
        self.pipeline_runner = None
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
            ctx.pipeline_runner.push(frame)
        except Exception as e:
            ctx.logger.error("Pipeline error", error=e)
        return frame


class RtcOffer(BaseModel):
    sdp: str
    type: str


async def rtc_offer_base(
    params: RtcOffer,
    request: Request,
    pipeline_runner: PipelineRunner,
):
    # build an rtc session
    offer = RTCSessionDescription(sdp=params.sdp, type=params.type)

    # client identification
    peername = request.client
    clientid = f"{peername[0]}:{peername[1]}"
    ctx = TranscriptionContext(logger=logger.bind(client=clientid))

    # handle RTC peer connection
    pc = RTCPeerConnection()
    ctx.pipeline_runner = pipeline_runner
    ctx.pipeline_runner.start()

    async def flush_pipeline_and_quit(close=True):
        # may be called twice
        # 1. either the client ask to sotp the meeting
        #    - we flush and close
        #    - when we receive the close event, we do nothing.
        # 2. or the client close the connection
        #    and there is nothing to do because it is already closed
        ctx.pipeline_runner.flush()
        if close:
            ctx.logger.debug("Closing peer connection")
            await pc.close()
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
