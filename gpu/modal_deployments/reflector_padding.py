"""
Reflector GPU backend - audio padding
======================================

CPU-intensive audio padding service for adding silence to audio tracks.
Uses PyAV filter graph (adelay) for precise track synchronization.

IMPORTANT: This padding logic is duplicated from server/reflector/utils/audio_padding.py
for Modal deployment isolation (Modal can't import from server/reflector/). If you modify
the PyAV filter graph or padding algorithm, you MUST update both:
  - gpu/modal_deployments/reflector_padding.py (this file)
  - server/reflector/utils/audio_padding.py

Constants duplicated from server/reflector/utils/audio_constants.py for same reason.
"""

import os
import tempfile
from fractions import Fraction
import math

import modal

PADDING_TIMEOUT = 600  # 10 minutes - more would be unreasonable
SCALEDOWN_WINDOW = 60  # The maximum duration (in seconds) that individual containers can remain idle when scaling down.

app = modal.App("reflector-padding")

# CPU-based image
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")  # Required by PyAV
    .pip_install(
        "av==13.1.0",  # PyAV for audio processing
        "requests==2.32.3",  # HTTP for presigned URL downloads/uploads
        "fastapi==0.115.12",  # API framework
    )
)

# ref B0F71CE8-FC59-4AA5-8414-DAFB836DB711
OPUS_STANDARD_SAMPLE_RATE = 48000
# ref B0F71CE8-FC59-4AA5-8414-DAFB836DB711
OPUS_DEFAULT_BIT_RATE = 128000


@app.function(
    cpu=2.0,
    timeout=PADDING_TIMEOUT,
    scaledown_window=SCALEDOWN_WINDOW,
    image=image,
)
def pad_track(
    track_url: str,
    output_url: str,
    start_time_seconds: float,
    track_index: int,
) -> dict:
    """Modal function for padding audio tracks.

    Returns:
        dict with keys: size (int)
    """
    import logging
    import av
    import requests
    from av.audio.resampler import AudioResampler

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    if not track_url:
        raise ValueError("track_url cannot be empty")
    if not output_url:
        raise ValueError("output_url cannot be empty")
    if start_time_seconds <= 0:
        raise ValueError(f"start_time_seconds must be positive, got {start_time_seconds}")
    if start_time_seconds > 3600:
        raise ValueError(f"start_time_seconds exceeds maximum 3600s")

    logger.info(f"Padding request: track {track_index}, delay={start_time_seconds}s")

    temp_dir = tempfile.mkdtemp()
    input_path = None
    output_path = None

    try:
        logger.info("Downloading track for padding")
        response = requests.get(track_url, stream=True, timeout=300)
        response.raise_for_status()

        input_path = os.path.join(temp_dir, "track.webm")
        total_bytes = 0
        with open(input_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)
        logger.info(f"Track downloaded: {total_bytes} bytes")

        # Apply padding using PyAV
        output_path = os.path.join(temp_dir, "padded.webm")
        delay_ms = math.floor(start_time_seconds * 1000)
        logger.info(f"Padding track {track_index} with {delay_ms}ms delay using PyAV")

        in_container = av.open(input_path)
        in_stream = next((s for s in in_container.streams if s.type == "audio"), None)
        if in_stream is None:
            raise ValueError("No audio stream in input")

        with av.open(output_path, "w", format="webm") as out_container:
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

            # Flush filter graph
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

        in_container.close()

        file_size = os.path.getsize(output_path)
        logger.info(f"Padding complete: {file_size} bytes")

        # Upload to S3
        logger.info("Uploading padded track to S3")
        with open(output_path, "rb") as f:
            upload_response = requests.put(output_url, data=f, timeout=300)
        upload_response.raise_for_status()
        logger.info(f"Upload complete: {file_size} bytes")

        return {"size": file_size}

    finally:
        if input_path and os.path.exists(input_path):
            try:
                os.unlink(input_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup input file: {e}")
        if output_path and os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup output file: {e}")
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")

