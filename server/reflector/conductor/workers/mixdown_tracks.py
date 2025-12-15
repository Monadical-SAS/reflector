"""Conductor worker: mixdown_tracks - Mix multiple audio tracks into single file.

Builds PyAV filter graph with amix filter to combine N padded tracks into
a single stereo MP3 file.
"""

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
from reflector.storage import get_transcripts_storage

PRESIGNED_URL_EXPIRATION_SECONDS = 7200
MP3_BITRATE = 192000


def _build_mixdown_filter_graph(containers: list, target_sample_rate: int):
    """Build PyAV filter graph: N abuffer -> amix -> aformat -> sink.

    Args:
        containers: List of PyAV containers for input tracks
        target_sample_rate: Output sample rate

    Returns:
        Tuple of (graph, inputs list, sink)
    """
    graph = av.filter.Graph()
    inputs = []

    for idx in range(len(containers)):
        args = (
            f"time_base=1/{target_sample_rate}:"
            f"sample_rate={target_sample_rate}:"
            f"sample_fmt=s32:"
            f"channel_layout=stereo"
        )
        in_ctx = graph.add("abuffer", args=args, name=f"in{idx}")
        inputs.append(in_ctx)

    # amix with normalize=0 to prevent volume reduction
    mixer = graph.add("amix", args=f"inputs={len(containers)}:normalize=0", name="mix")
    fmt = graph.add(
        "aformat",
        args=f"sample_fmts=s16:channel_layouts=stereo:sample_rates={target_sample_rate}",
        name="fmt",
    )
    sink = graph.add("abuffersink", name="out")

    for idx, in_ctx in enumerate(inputs):
        in_ctx.link_to(mixer, 0, idx)
    mixer.link_to(fmt)
    fmt.link_to(sink)
    graph.configure()

    return graph, inputs, sink


@worker_task(task_definition_name="mixdown_tracks")
def mixdown_tracks(task: Task) -> TaskResult:
    """Mix multiple audio tracks into single stereo file.

    Input:
        padded_urls: list[str] - Presigned URLs of padded tracks
        transcript_id: str - Transcript ID for storage path

    Output:
        audio_key: str - S3 key of mixed audio file
        duration: float - Audio duration in seconds
        size: int - File size in bytes
    """
    padded_urls = task.input_data.get("padded_urls", [])
    transcript_id = task.input_data.get("transcript_id")

    logger.info(
        "[Worker] mixdown_tracks",
        track_count=len(padded_urls),
        transcript_id=transcript_id,
    )

    if transcript_id:
        emit_progress(
            transcript_id, "mixdown_tracks", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not padded_urls or not transcript_id:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing padded_urls or transcript_id"
        return task_result

    import asyncio

    async def _process():
        storage = get_transcripts_storage()

        # Determine target sample rate from first track
        target_sample_rate = None
        for url in padded_urls:
            if not url:
                continue
            try:
                with av.open(url) as container:
                    for frame in container.decode(audio=0):
                        target_sample_rate = frame.sample_rate
                        break
            except Exception:
                continue
            if target_sample_rate:
                break

        if not target_sample_rate:
            raise Exception("Mixdown failed: No decodable audio frames in any track")

        # Open all containers with reconnect options for S3 streaming
        containers = []
        valid_urls = [url for url in padded_urls if url]

        for url in valid_urls:
            try:
                c = av.open(
                    url,
                    options={
                        "reconnect": "1",
                        "reconnect_streamed": "1",
                        "reconnect_delay_max": "5",
                    },
                )
                containers.append(c)
            except Exception as e:
                logger.warning(
                    "Mixdown: failed to open container", url=url[:50], error=str(e)
                )

        if not containers:
            raise Exception("Mixdown failed: Could not open any track containers")

        try:
            # Build filter graph
            graph, inputs, sink = _build_mixdown_filter_graph(
                containers, target_sample_rate
            )

            # Create temp file for output
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                # Open output container for MP3
                with av.open(temp_path, "w", format="mp3") as out_container:
                    out_stream = out_container.add_stream(
                        "libmp3lame", rate=target_sample_rate
                    )
                    out_stream.bit_rate = MP3_BITRATE

                    decoders = [c.decode(audio=0) for c in containers]
                    active = [True] * len(decoders)
                    resamplers = [
                        AudioResampler(
                            format="s32", layout="stereo", rate=target_sample_rate
                        )
                        for _ in decoders
                    ]

                    duration_samples = 0

                    while any(active):
                        for i, (dec, is_active) in enumerate(zip(decoders, active)):
                            if not is_active:
                                continue
                            try:
                                frame = next(dec)
                            except StopIteration:
                                active[i] = False
                                inputs[i].push(None)
                                continue

                            if frame.sample_rate != target_sample_rate:
                                continue

                            out_frames = resamplers[i].resample(frame) or []
                            for rf in out_frames:
                                rf.sample_rate = target_sample_rate
                                rf.time_base = Fraction(1, target_sample_rate)
                                inputs[i].push(rf)

                                while True:
                                    try:
                                        mixed = sink.pull()
                                    except Exception:
                                        break
                                    mixed.sample_rate = target_sample_rate
                                    mixed.time_base = Fraction(1, target_sample_rate)
                                    duration_samples += mixed.samples
                                    for packet in out_stream.encode(mixed):
                                        out_container.mux(packet)

                    # Flush remaining
                    while True:
                        try:
                            mixed = sink.pull()
                        except Exception:
                            break
                        mixed.sample_rate = target_sample_rate
                        mixed.time_base = Fraction(1, target_sample_rate)
                        duration_samples += mixed.samples
                        for packet in out_stream.encode(mixed):
                            out_container.mux(packet)

                    for packet in out_stream.encode(None):
                        out_container.mux(packet)

                # Get file size and duration
                file_size = Path(temp_path).stat().st_size
                duration = (
                    duration_samples / target_sample_rate if target_sample_rate else 0
                )

                # Upload to S3
                storage_path = f"{transcript_id}/audio.mp3"
                with open(temp_path, "rb") as mp3_file:
                    await storage.put_file(storage_path, mp3_file)

            finally:
                Path(temp_path).unlink(missing_ok=True)

        finally:
            for c in containers:
                try:
                    c.close()
                except Exception:
                    pass

        return {
            "audio_key": storage_path,
            "duration": duration,
            "size": file_size,
        }

    try:
        result = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = result

        logger.info(
            "[Worker] mixdown_tracks complete",
            audio_key=result["audio_key"],
            duration=result["duration"],
            size=result["size"],
        )

        if transcript_id:
            emit_progress(
                transcript_id, "mixdown_tracks", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] mixdown_tracks failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "mixdown_tracks", "failed", task.workflow_instance_id
            )

    return task_result
