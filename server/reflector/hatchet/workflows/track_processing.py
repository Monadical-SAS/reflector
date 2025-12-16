"""
Hatchet child workflow: TrackProcessing

Handles individual audio track processing: padding and transcription.
Spawned dynamically by the main diarization pipeline for each track.
"""

import math
import tempfile
from datetime import timedelta
from fractions import Fraction
from pathlib import Path

import av
from av.audio.resampler import AudioResampler
from hatchet_sdk import Context
from pydantic import BaseModel

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.progress import emit_progress_async
from reflector.hatchet.workflows.models import PadTrackResult, TranscribeTrackResult
from reflector.logger import logger


def _to_dict(output) -> dict:
    """Convert task output to dict, handling both dict and Pydantic model returns."""
    if isinstance(output, dict):
        return output
    return output.model_dump()


# Audio constants matching existing pipeline
OPUS_STANDARD_SAMPLE_RATE = 48000
OPUS_DEFAULT_BIT_RATE = 64000
PRESIGNED_URL_EXPIRATION_SECONDS = 7200


class TrackInput(BaseModel):
    """Input for individual track processing."""

    track_index: int
    s3_key: str
    bucket_name: str
    transcript_id: str
    language: str = "en"


# Get hatchet client and define workflow
hatchet = HatchetClientManager.get_client()

track_workflow = hatchet.workflow(name="TrackProcessing", input_validator=TrackInput)


def _extract_stream_start_time_from_container(container, track_idx: int) -> float:
    """Extract meeting-relative start time from WebM stream metadata.

    Uses PyAV to read stream.start_time from WebM container.
    More accurate than filename timestamps by ~209ms due to network/encoding delays.
    """
    start_time_seconds = 0.0
    try:
        audio_streams = [s for s in container.streams if s.type == "audio"]
        stream = audio_streams[0] if audio_streams else container.streams[0]

        # 1) Try stream-level start_time (most reliable for Daily.co tracks)
        if stream.start_time is not None and stream.time_base is not None:
            start_time_seconds = float(stream.start_time * stream.time_base)

        # 2) Fallback to container-level start_time
        if (start_time_seconds <= 0) and (container.start_time is not None):
            start_time_seconds = float(container.start_time * av.time_base)

        # 3) Fallback to first packet DTS
        if start_time_seconds <= 0:
            for packet in container.demux(stream):
                if packet.dts is not None:
                    start_time_seconds = float(packet.dts * stream.time_base)
                    break
    except Exception as e:
        logger.warning(
            "PyAV metadata read failed; assuming 0 start_time",
            track_idx=track_idx,
            error=str(e),
        )
        start_time_seconds = 0.0

    logger.info(
        f"Track {track_idx} stream metadata: start_time={start_time_seconds:.3f}s",
        track_idx=track_idx,
    )
    return start_time_seconds


def _apply_audio_padding_to_file(
    in_container,
    output_path: str,
    start_time_seconds: float,
    track_idx: int,
) -> None:
    """Apply silence padding to audio track using PyAV filter graph."""
    delay_ms = math.floor(start_time_seconds * 1000)

    logger.info(
        f"Padding track {track_idx} with {delay_ms}ms delay using PyAV",
        track_idx=track_idx,
        delay_ms=delay_ms,
    )

    with av.open(output_path, "w", format="webm") as out_container:
        in_stream = next((s for s in in_container.streams if s.type == "audio"), None)
        if in_stream is None:
            raise Exception("No audio stream in input")

        out_stream = out_container.add_stream("libopus", rate=OPUS_STANDARD_SAMPLE_RATE)
        out_stream.bit_rate = OPUS_DEFAULT_BIT_RATE
        graph = av.filter.Graph()

        abuf_args = (
            f"time_base=1/{OPUS_STANDARD_SAMPLE_RATE}:"
            f"sample_rate={OPUS_STANDARD_SAMPLE_RATE}:"
            f"sample_fmt=s16:"
            f"channel_layout=stereo"
        )
        src = graph.add("abuffer", args=abuf_args, name="src")
        aresample_f = graph.add("aresample", args="async=1", name="ares")
        delays_arg = f"{delay_ms}|{delay_ms}"
        adelay_f = graph.add("adelay", args=f"delays={delays_arg}:all=1", name="delay")
        sink = graph.add("abuffersink", name="sink")

        src.link_to(aresample_f)
        aresample_f.link_to(adelay_f)
        adelay_f.link_to(sink)
        graph.configure()

        resampler = AudioResampler(
            format="s16", layout="stereo", rate=OPUS_STANDARD_SAMPLE_RATE
        )

        for frame in in_container.decode(in_stream):
            out_frames = resampler.resample(frame) or []
            for rframe in out_frames:
                rframe.sample_rate = OPUS_STANDARD_SAMPLE_RATE
                rframe.time_base = Fraction(1, OPUS_STANDARD_SAMPLE_RATE)
                src.push(rframe)

                while True:
                    try:
                        f_out = sink.pull()
                    except Exception:
                        break
                    f_out.sample_rate = OPUS_STANDARD_SAMPLE_RATE
                    f_out.time_base = Fraction(1, OPUS_STANDARD_SAMPLE_RATE)
                    for packet in out_stream.encode(f_out):
                        out_container.mux(packet)

        # Flush remaining frames
        src.push(None)
        while True:
            try:
                f_out = sink.pull()
            except Exception:
                break
            f_out.sample_rate = OPUS_STANDARD_SAMPLE_RATE
            f_out.time_base = Fraction(1, OPUS_STANDARD_SAMPLE_RATE)
            for packet in out_stream.encode(f_out):
                out_container.mux(packet)

        for packet in out_stream.encode(None):
            out_container.mux(packet)


@track_workflow.task(execution_timeout=timedelta(seconds=300), retries=3)
async def pad_track(input: TrackInput, ctx: Context) -> PadTrackResult:
    """Pad single audio track with silence for alignment.

    Extracts stream.start_time from WebM container metadata and applies
    silence padding using PyAV filter graph (adelay).
    """
    logger.info(
        "[Hatchet] pad_track",
        track_index=input.track_index,
        s3_key=input.s3_key,
        transcript_id=input.transcript_id,
    )

    await emit_progress_async(
        input.transcript_id, "pad_track", "in_progress", ctx.workflow_run_id
    )

    try:
        # Create fresh storage instance to avoid aioboto3 fork issues
        from reflector.settings import settings
        from reflector.storage.storage_aws import AwsStorage

        storage = AwsStorage(
            aws_bucket_name=settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME,
            aws_region=settings.TRANSCRIPT_STORAGE_AWS_REGION,
            aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
        )

        # Get presigned URL for source file
        source_url = await storage.get_file_url(
            input.s3_key,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
            bucket=input.bucket_name,
        )

        # Open container and extract start time
        with av.open(source_url) as in_container:
            start_time_seconds = _extract_stream_start_time_from_container(
                in_container, input.track_index
            )

            # If no padding needed, return original URL
            if start_time_seconds <= 0:
                logger.info(
                    f"Track {input.track_index} requires no padding",
                    track_index=input.track_index,
                )
                await emit_progress_async(
                    input.transcript_id, "pad_track", "completed", ctx.workflow_run_id
                )
                return PadTrackResult(
                    padded_url=source_url,
                    size=0,
                    track_index=input.track_index,
                )

            # Create temp file for padded output
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                _apply_audio_padding_to_file(
                    in_container, temp_path, start_time_seconds, input.track_index
                )

                file_size = Path(temp_path).stat().st_size
                storage_path = f"file_pipeline_hatchet/{input.transcript_id}/tracks/padded_{input.track_index}.webm"

                logger.info(
                    f"About to upload padded track",
                    key=storage_path,
                    size=file_size,
                )

                with open(temp_path, "rb") as padded_file:
                    await storage.put_file(storage_path, padded_file)

                logger.info(
                    f"Uploaded padded track to S3",
                    key=storage_path,
                    size=file_size,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        # Get presigned URL for padded file
        padded_url = await storage.get_file_url(
            storage_path,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
        )

        logger.info(
            "[Hatchet] pad_track complete",
            track_index=input.track_index,
            padded_url=padded_url[:50] + "...",
        )

        await emit_progress_async(
            input.transcript_id, "pad_track", "completed", ctx.workflow_run_id
        )

        return PadTrackResult(
            padded_url=padded_url,
            size=file_size,
            track_index=input.track_index,
        )

    except Exception as e:
        logger.error("[Hatchet] pad_track failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "pad_track", "failed", ctx.workflow_run_id
        )
        raise


@track_workflow.task(
    parents=[pad_track], execution_timeout=timedelta(seconds=600), retries=3
)
async def transcribe_track(input: TrackInput, ctx: Context) -> TranscribeTrackResult:
    """Transcribe audio track using GPU (Modal.com) or local Whisper."""
    logger.info(
        "[Hatchet] transcribe_track",
        track_index=input.track_index,
        language=input.language,
    )

    await emit_progress_async(
        input.transcript_id, "transcribe_track", "in_progress", ctx.workflow_run_id
    )

    try:
        pad_result = _to_dict(ctx.task_output(pad_track))
        audio_url = pad_result.get("padded_url")

        if not audio_url:
            raise ValueError("Missing padded_url from pad_track")

        from reflector.pipelines.transcription_helpers import (
            transcribe_file_with_processor,
        )

        transcript = await transcribe_file_with_processor(audio_url, input.language)

        # Tag all words with speaker index
        words = []
        for word in transcript.words:
            word_dict = word.model_dump()
            word_dict["speaker"] = input.track_index
            words.append(word_dict)

        logger.info(
            "[Hatchet] transcribe_track complete",
            track_index=input.track_index,
            word_count=len(words),
        )

        await emit_progress_async(
            input.transcript_id, "transcribe_track", "completed", ctx.workflow_run_id
        )

        return TranscribeTrackResult(
            words=words,
            track_index=input.track_index,
        )

    except Exception as e:
        logger.error("[Hatchet] transcribe_track failed", error=str(e), exc_info=True)
        await emit_progress_async(
            input.transcript_id, "transcribe_track", "failed", ctx.workflow_run_id
        )
        raise
