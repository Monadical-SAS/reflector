from fastapi import Request, APIRouter
from pydantic import BaseModel
from reflector.models import (
    TranscriptionContext,
    TranscriptionOutput,
    TitleSummaryOutput,
    IncrementalResult,
)
from reflector.logger import logger
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from json import loads, dumps
import av
from reflector.processors import (
    Pipeline,
    AudioChunkerProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    Transcript,
    TitleSummary,
)


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


sessions = []
router = APIRouter()


@router.post("/offer")
async def rtc_offer(params: RtcOffer, request: Request):
    # build an rtc session
    offer = RTCSessionDescription(sdp=params.sdp, type=params.type)

    # client identification
    peername = request.client
    clientid = f"{peername[0]}:{peername[1]}"
    ctx = TranscriptionContext(logger=logger.bind(client=clientid))

    # build pipeline callback
    async def on_transcript(transcript: Transcript):
        ctx.logger.info("Transcript", transcript=transcript)
        cmd = TranscriptionOutput(transcript.text)
        # FIXME: send the result to the client async way
        ctx.data_channel.send(dumps(cmd.get_result()))

    async def on_summary(summary: TitleSummary):
        ctx.logger.info("Summary", summary=summary)
        # XXX doesnt work as expected, IncrementalResult is not serializable
        #     and previous implementation assume output of oobagooda
        # result = TitleSummaryOutput(
        #     [
        #         IncrementalResult(
        #             title=summary.title,
        #             desc=summary.summary,
        #             transcript=summary.transcript.text,
        #             timestamp=summary.timestamp,
        #         )
        #     ]
        # )
        result = {
            "cmd": "UPDATE_TOPICS",
            "topics": [
                {
                    "title": summary.title,
                    "timestamp": summary.timestamp,
                    "transcript": summary.transcript.text,
                    "desc": summary.summary,
                }
            ],
        }

        ctx.data_channel.send(dumps(result))

    # create a context for the whole rtc transaction
    # add a customised logger to the context
    ctx.pipeline = Pipeline(
        AudioChunkerProcessor(),
        AudioMergeProcessor(),
        AudioTranscriptAutoProcessor.as_threaded(callback=on_transcript),
        TranscriptLinerProcessor(),
        TranscriptTopicDetectorProcessor.as_threaded(callback=on_summary),
        # FinalSummaryProcessor.as_threaded(
        #     filename=result_fn, callback=on_final_summary
        # ),
    )

    # handle RTC peer connection
    pc = RTCPeerConnection()

    @pc.on("datachannel")
    def on_datachannel(channel):
        ctx.data_channel = channel
        ctx.logger = ctx.logger.bind(channel=channel.label)
        ctx.logger.info("Channel created by remote party")

        @channel.on("message")
        def on_message(message: str):
            ctx.logger.info(f"Message: {message}")
            if loads(message)["cmd"] == "STOP":
                # FIXME: flush the pipeline
                pass

            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        ctx.logger.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()

    @pc.on("track")
    def on_track(track):
        ctx.logger.info(f"Track {track.kind} received")
        pc.addTrack(AudioStreamTrack(ctx, track))

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    sessions.append(pc)

    return RtcOffer(sdp=pc.localDescription.sdp, type=pc.localDescription.type)
