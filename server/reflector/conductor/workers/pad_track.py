"""Conductor worker: pad_track - Pad audio track with silence for alignment.

This worker extracts stream.start_time from WebM container metadata and applies
silence padding using PyAV filter graph (adelay). The padded audio is uploaded
to S3 and a presigned URL is returned.
"""

import math
import tempfile
from fractions import Fraction
from pathlib import Path

import av
from av.audio.resampler import AudioResampler

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger

# Audio constants matching existing pipeline
OPUS_STANDARD_SAMPLE_RATE = 48000
OPUS_DEFAULT_BIT_RATE = 64000
PRESIGNED_URL_EXPIRATION_SECONDS = 7200


def _extract_stream_start_time_from_container(container, track_idx: int) -> float:
    """Extract meeting-relative start time from WebM stream metadata.

    Uses PyAV to read stream.start_time from WebM container.
    More accurate than filename timestamps by ~209ms due to network/encoding delays.

    Args:
        container: PyAV container object
        track_idx: Track index for logging

    Returns:
        Start time in seconds (0.0 if not found)
    """
    start_time_seconds = 0.0
    try:
        audio_streams = [s for s in container.streams if s.type == "audio"]
        stream = audio_streams[0] if audio_streams else container.streams[0]

        # 1) Try stream-level start_time (most reliable for Daily.co tracks)
        if stream.start_time is not None and stream.time_base is not None:
            start_time_seconds = float(stream.start_time * stream.time_base)

        # 2) Fallback to container-level start_time (in av.time_base units)
        if (start_time_seconds <= 0) and (container.start_time is not None):
            start_time_seconds = float(container.start_time * av.time_base)

        # 3) Fallback to first packet DTS in stream.time_base
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
    """Apply silence padding to audio track using PyAV filter graph.

    Filter chain: abuffer -> aresample -> adelay -> abuffersink

    Args:
        in_container: PyAV input container
        output_path: Path to write padded output
        start_time_seconds: Amount of silence to prepend
        track_idx: Track index for logging
    """
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
        # adelay requires one delay value per channel separated by '|'
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

        # Decode -> resample -> push through graph -> encode Opus
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


@worker_task(task_definition_name="pad_track")
def pad_track(task: Task) -> TaskResult:
    """Pad audio track with silence for alignment.

    Input:
        track_index: int - Index of the track
        s3_key: str - S3 key of the source audio file
        bucket_name: str - S3 bucket name
        transcript_id: str - Transcript ID for storage path

    Output:
        padded_url: str - Presigned URL of padded track
        size: int - File size in bytes
        track_index: int - Track index (echoed back)
    """
    track_index = task.input_data.get("track_index", 0)
    s3_key = task.input_data.get("s3_key")
    bucket_name = task.input_data.get("bucket_name")
    transcript_id = task.input_data.get("transcript_id")

    logger.info(
        "[Worker] pad_track",
        track_index=track_index,
        s3_key=s3_key,
        transcript_id=transcript_id,
    )

    if transcript_id:
        emit_progress(
            transcript_id, "pad_track", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not s3_key or not transcript_id:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing s3_key or transcript_id"
        return task_result

    import asyncio

    async def _process():
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
            s3_key,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
            bucket=bucket_name,
        )

        # Open container and extract start time
        with av.open(source_url) as in_container:
            start_time_seconds = _extract_stream_start_time_from_container(
                in_container, track_index
            )

            # If no padding needed, return original URL
            if start_time_seconds <= 0:
                logger.info(
                    f"Track {track_index} requires no padding",
                    track_index=track_index,
                )
                return {
                    "padded_url": source_url,
                    "size": 0,
                    "track_index": track_index,
                }

            # Create temp file for padded output
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                _apply_audio_padding_to_file(
                    in_container, temp_path, start_time_seconds, track_index
                )

                # Get file size
                file_size = Path(temp_path).stat().st_size

                # Upload using storage layer (use separate path in shadow mode to avoid conflicts)
                storage_path = f"file_pipeline_conductor/{transcript_id}/tracks/padded_{track_index}.webm"

                logger.info(
                    f"About to upload padded track",
                    key=storage_path,
                    size=file_size,
                )

                with open(temp_path, "rb") as padded_file:
                    upload_result = await storage.put_file(storage_path, padded_file)
                    logger.info(
                        f"storage.put_file returned",
                        result=str(upload_result),
                    )

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

        return {
            "padded_url": padded_url,
            "size": file_size,
            "track_index": track_index,
        }

    try:
        result = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = result

        logger.info(
            "[Worker] pad_track complete",
            track_index=track_index,
            padded_url=result["padded_url"][:50] + "...",
        )

        if transcript_id:
            emit_progress(
                transcript_id, "pad_track", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] pad_track failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "pad_track", "failed", task.workflow_instance_id
            )

    return task_result
