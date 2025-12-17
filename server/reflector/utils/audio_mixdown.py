"""
Audio track mixdown utilities.

Shared PyAV-based functions for mixing multiple audio tracks into a single output.
Used by both Hatchet workflows and Celery pipelines.
"""

from fractions import Fraction

import av
from av.audio.resampler import AudioResampler


def detect_sample_rate_from_tracks(track_urls: list[str], logger=None) -> int | None:
    """Detect sample rate from first decodable audio frame.

    Args:
        track_urls: List of URLs to audio files (S3 presigned or local)
        logger: Optional logger instance

    Returns:
        Sample rate in Hz, or None if no decodable frames found
    """
    for url in track_urls:
        if not url:
            continue
        container = None
        try:
            container = av.open(url)
            for frame in container.decode(audio=0):
                return frame.sample_rate
        except Exception:
            continue
        finally:
            if container is not None:
                container.close()
    return None


async def mixdown_tracks_pyav(
    track_urls: list[str],
    writer,
    target_sample_rate: int,
    offsets_seconds: list[float] | None = None,
    logger=None,
) -> None:
    """Multi-track mixdown using PyAV filter graph (amix).

    Builds a filter graph: N abuffer -> optional adelay -> amix -> aformat -> sink
    Reads from S3 presigned URLs or local files, pushes mixed frames to writer.

    Args:
        track_urls: List of URLs to audio tracks (S3 presigned or local)
        writer: AudioFileWriterProcessor instance with async push() method
        target_sample_rate: Sample rate for output (Hz)
        offsets_seconds: Optional per-track delays in seconds for alignment.
            If provided, must have same length as track_urls. Delays are relative
            to the minimum offset (earliest track has delay=0).
        logger: Optional logger instance

    Raises:
        ValueError: If no valid tracks or containers can be opened
    """
    valid_track_urls = [url for url in track_urls if url]
    if not valid_track_urls:
        if logger:
            logger.error("Mixdown failed - no valid track URLs provided")
        raise ValueError("Mixdown failed: No valid track URLs")

    # Calculate per-input delays if offsets provided
    input_offsets_seconds = None
    if offsets_seconds is not None:
        input_offsets_seconds = [
            offsets_seconds[i] for i, url in enumerate(track_urls) if url
        ]

    # Build PyAV filter graph:
    # N abuffer (s32/stereo)
    #   -> optional adelay per input (for alignment)
    #   -> amix (s32)
    #   -> aformat(s16)
    #   -> sink
    graph = av.filter.Graph()
    inputs = []

    for idx, url in enumerate(valid_track_urls):
        args = (
            f"time_base=1/{target_sample_rate}:"
            f"sample_rate={target_sample_rate}:"
            f"sample_fmt=s32:"
            f"channel_layout=stereo"
        )
        in_ctx = graph.add("abuffer", args=args, name=f"in{idx}")
        inputs.append(in_ctx)

    if not inputs:
        if logger:
            logger.error("Mixdown failed - no valid inputs for graph")
        raise ValueError("Mixdown failed: No valid inputs for filter graph")

    mixer = graph.add("amix", args=f"inputs={len(inputs)}:normalize=0", name="mix")

    fmt = graph.add(
        "aformat",
        args=f"sample_fmts=s32:channel_layouts=stereo:sample_rates={target_sample_rate}",
        name="fmt",
    )

    sink = graph.add("abuffersink", name="out")

    # Optional per-input delay before mixing
    delays_ms: list[int] = []
    if input_offsets_seconds is not None:
        base = min(input_offsets_seconds) if input_offsets_seconds else 0.0
        delays_ms = [
            max(0, int(round((o - base) * 1000))) for o in input_offsets_seconds
        ]
    else:
        delays_ms = [0 for _ in inputs]

    for idx, in_ctx in enumerate(inputs):
        delay_ms = delays_ms[idx] if idx < len(delays_ms) else 0
        if delay_ms > 0:
            # adelay requires one value per channel; use same for stereo
            adelay = graph.add(
                "adelay",
                args=f"delays={delay_ms}|{delay_ms}:all=1",
                name=f"delay{idx}",
            )
            in_ctx.link_to(adelay)
            adelay.link_to(mixer, 0, idx)
        else:
            in_ctx.link_to(mixer, 0, idx)

    mixer.link_to(fmt)
    fmt.link_to(sink)
    graph.configure()

    containers = []
    try:
        # Open all containers with cleanup guaranteed
        for i, url in enumerate(valid_track_urls):
            try:
                c = av.open(
                    url,
                    options={
                        # S3 streaming options
                        "reconnect": "1",
                        "reconnect_streamed": "1",
                        "reconnect_delay_max": "5",
                    },
                )
                containers.append(c)
            except Exception as e:
                if logger:
                    logger.warning(
                        "Mixdown: failed to open container from URL",
                        input=i,
                        url=url,
                        error=str(e),
                    )

        if not containers:
            if logger:
                logger.error("Mixdown failed - no valid containers opened")
            raise ValueError("Mixdown failed: Could not open any track containers")

        decoders = [c.decode(audio=0) for c in containers]
        active = [True] * len(decoders)
        resamplers = [
            AudioResampler(format="s32", layout="stereo", rate=target_sample_rate)
            for _ in decoders
        ]

        while any(active):
            for i, (dec, is_active) in enumerate(zip(decoders, active)):
                if not is_active:
                    continue
                try:
                    frame = next(dec)
                except StopIteration:
                    active[i] = False
                    # Signal end of stream to filter graph
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
                    await writer.push(mixed)

        # Flush remaining frames from filter graph
        while True:
            try:
                mixed = sink.pull()
            except Exception:
                break
            mixed.sample_rate = target_sample_rate
            mixed.time_base = Fraction(1, target_sample_rate)
            await writer.push(mixed)

    finally:
        # Cleanup all containers, even if processing failed
        for c in containers:
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass  # Best effort cleanup
