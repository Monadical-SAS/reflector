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
import asyncio

import modal

S3_TIMEOUT = 60 # happens 2 times
PADDING_TIMEOUT = 600 + (S3_TIMEOUT * 2)
SCALEDOWN_WINDOW = 60  # The maximum duration (in seconds) that individual containers can remain idle when scaling down.
DISCONNECT_CHECK_INTERVAL = 2  # Check for client disconnect


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
@modal.asgi_app()
def web():
    from fastapi import FastAPI, Request, HTTPException
    from pydantic import BaseModel

    class PaddingRequest(BaseModel):
        track_url: str
        output_url: str
        start_time_seconds: float
        track_index: int

    class PaddingResponse(BaseModel):
        size: int
        cancelled: bool = False

    web_app = FastAPI()

    @web_app.post("/pad")
    async def pad_track_endpoint(request: Request, req: PaddingRequest) -> PaddingResponse:
        """Modal web endpoint for padding audio tracks with disconnect detection.

        Returns:
            PaddingResponse with size field
        """
        import logging

        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        logger = logging.getLogger(__name__)

        if not req.track_url:
            raise HTTPException(status_code=400, detail="track_url cannot be empty")
        if not req.output_url:
            raise HTTPException(status_code=400, detail="output_url cannot be empty")
        if req.start_time_seconds <= 0:
            raise HTTPException(status_code=400, detail=f"start_time_seconds must be positive, got {req.start_time_seconds}")
        if req.start_time_seconds > 18000:
            raise HTTPException(status_code=400, detail=f"start_time_seconds exceeds maximum 18000s (5 hours)")

        logger.info(f"Padding request: track {req.track_index}, delay={req.start_time_seconds}s")

        # Thread-safe cancellation flag shared between async disconnect checker and blocking thread
        import threading
        cancelled = threading.Event()

        async def check_disconnect():
            """Background task to check for client disconnect every 2 seconds."""
            while not cancelled.is_set():
                await asyncio.sleep(DISCONNECT_CHECK_INTERVAL)
                if await request.is_disconnected():
                    logger.warning("Client disconnected, setting cancellation flag")
                    cancelled.set()
                    break

        # Start disconnect checker in background
        disconnect_task = asyncio.create_task(check_disconnect())

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, _pad_track_blocking, req, cancelled, logger
            )
            return PaddingResponse(**result)
        finally:
            # Cleanup disconnect checker
            cancelled.set()
            disconnect_task.cancel()
            try:
                await disconnect_task
            except asyncio.CancelledError:
                pass

    def _pad_track_blocking(req, cancelled, logger) -> dict:
        """Blocking CPU-bound padding work with periodic cancellation checks.

        Args:
            cancelled: threading.Event for thread-safe cancellation signaling
        """
        import av
        import requests
        from av.audio.resampler import AudioResampler
        import time

        temp_dir = tempfile.mkdtemp()
        input_path = None
        output_path = None
        last_check = time.time()

        try:
            logger.info("Downloading track for padding")
            response = requests.get(req.track_url, stream=True, timeout=S3_TIMEOUT)
            response.raise_for_status()

            input_path = os.path.join(temp_dir, "track.webm")
            total_bytes = 0
            chunk_count = 0
            with open(input_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)
                        chunk_count += 1

                        # Check for cancellation every ~100KB (12-13 chunks)
                        if chunk_count % 12 == 0:
                            now = time.time()
                            if now - last_check >= DISCONNECT_CHECK_INTERVAL:
                                if cancelled.is_set():
                                    logger.info("Cancelled during download, exiting early")
                                    return {"size": 0, "cancelled": True}
                                last_check = now
            logger.info(f"Track downloaded: {total_bytes} bytes")

            # Final check after download
            if cancelled.is_set():
                logger.info("Cancelled after download, exiting early")
                return {"size": 0, "cancelled": True}

            # Apply padding using PyAV
            output_path = os.path.join(temp_dir, "padded.webm")
            delay_ms = math.floor(req.start_time_seconds * 1000)
            logger.info(f"Padding track {req.track_index} with {delay_ms}ms delay using PyAV")

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
                    # Check for cancellation periodically
                    now = time.time()
                    if now - last_check >= DISCONNECT_CHECK_INTERVAL:
                        if cancelled.is_set():
                            logger.info("Cancelled during processing, exiting early")
                            in_container.close()
                            return {"size": 0, "cancelled": True}
                        last_check = now

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

            logger.info("Uploading padded track to S3")

            with open(output_path, "rb") as f:
                upload_response = requests.put(req.output_url, data=f, timeout=S3_TIMEOUT)

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

    return web_app

