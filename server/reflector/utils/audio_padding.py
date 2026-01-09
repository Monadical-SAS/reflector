"""
Audio track padding utilities.

Shared PyAV-based functions for extracting stream metadata and applying
silence padding to audio tracks. Used by both Hatchet workflows and Celery pipelines.
"""

import math
from fractions import Fraction

import av
from av.audio.resampler import AudioResampler

from reflector.utils.audio_constants import (
    OPUS_DEFAULT_BIT_RATE,
    OPUS_STANDARD_SAMPLE_RATE,
)


def extract_stream_start_time_from_container(
    container,
    track_idx: int,
    logger=None,
) -> float:
    """Extract meeting-relative start time from WebM stream metadata.

    Uses PyAV to read stream.start_time from WebM container.
    Note: Differs from filename timestamps by ~200ms in test recordings, but this difference
    is not crucial - either method works. Filename timestamps are preferable due to being
    better officially documented by Daily.co.

    Args:
        container: PyAV container opened from audio file/URL
        track_idx: Track index for logging context
        logger: Optional logger instance (structlog or stdlib compatible)

    Returns:
        Start time in seconds (0.0 if extraction fails)
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
        if logger:
            logger.warning(
                "PyAV metadata read failed; assuming 0 start_time",
                track_idx=track_idx,
                error=str(e),
            )
        start_time_seconds = 0.0

    if logger:
        logger.info(
            f"Track {track_idx} stream metadata: start_time={start_time_seconds:.3f}s",
            track_idx=track_idx,
        )
    return start_time_seconds


def apply_audio_padding_to_file(
    in_container,
    output_path: str,
    start_time_seconds: float,
    track_idx: int,
    logger=None,
) -> None:
    """Apply silence padding to audio track using PyAV filter graph.

    Uses adelay filter to prepend silence, aligning track to meeting start time.
    Output is WebM/Opus format.

    Args:
        in_container: PyAV container opened from source audio
        output_path: Path for output WebM file
        start_time_seconds: Amount of silence to prepend (in seconds)
        track_idx: Track index for logging context
        logger: Optional logger instance (structlog or stdlib compatible)

    Raises:
        Exception: If no audio stream found or PyAV processing fails
    """
    delay_ms = math.floor(start_time_seconds * 1000)

    if logger:
        logger.info(
            f"Padding track {track_idx} with {delay_ms}ms delay using PyAV",
            track_idx=track_idx,
            delay_ms=delay_ms,
        )

    try:
        with av.open(output_path, "w", format="webm") as out_container:
            in_stream = next(
                (s for s in in_container.streams if s.type == "audio"), None
            )
            if in_stream is None:
                raise Exception("No audio stream in input")

            out_stream = out_container.add_stream(
                "libopus", rate=OPUS_STANDARD_SAMPLE_RATE
            )
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
            adelay_f = graph.add(
                "adelay", args=f"delays={delays_arg}:all=1", name="delay"
            )
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

            # Flush remaining frames from filter graph
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

            # Flush encoder
            for packet in out_stream.encode(None):
                out_container.mux(packet)

    except Exception as e:
        if logger:
            logger.error(
                "PyAV padding failed for track",
                track_idx=track_idx,
                delay_ms=delay_ms,
                error=str(e),
                exc_info=True,
            )
        raise
