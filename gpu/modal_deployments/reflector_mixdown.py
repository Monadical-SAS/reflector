"""
Reflector GPU backend - audio mixdown
======================================

CPU-intensive audio mixdown service for combining multiple audio tracks.
Uses PyAV filter graph (amix) for high-quality audio mixing.
"""

import os
import tempfile
import time
from fractions import Fraction

import modal

MIXDOWN_TIMEOUT = 900  # 15 minutes
SCALEDOWN_WINDOW = 60  # 1 minute idle before shutdown

app = modal.App("reflector-mixdown")

# CPU-based image (no GPU needed for audio processing)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")  # Required by PyAV
    .pip_install(
        "av==13.1.0",  # PyAV for audio processing
        "requests==2.32.3",  # HTTP for presigned URL downloads/uploads
        "fastapi==0.115.12",  # API framework
    )
)


@app.function(
    cpu=4.0,  # 4 CPU cores for audio processing
    timeout=MIXDOWN_TIMEOUT,
    scaledown_window=SCALEDOWN_WINDOW,
    secrets=[modal.Secret.from_name("reflector-gpu")],
    image=image,
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def web():
    import logging
    import secrets
    import shutil

    import av
    import requests
    from av.audio.resampler import AudioResampler
    from fastapi import Depends, FastAPI, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from pydantic import BaseModel

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    app = FastAPI()
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    # Validate API key exists at startup
    API_KEY = os.environ.get("REFLECTOR_GPU_APIKEY")
    if not API_KEY:
        raise RuntimeError("REFLECTOR_GPU_APIKEY not configured in Modal secrets")

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        # Use constant-time comparison to prevent timing attacks
        if secrets.compare_digest(apikey, API_KEY):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    class MixdownRequest(BaseModel):
        track_urls: list[str]
        output_url: str
        target_sample_rate: int = 48000
        expected_duration_sec: float | None = None

    class MixdownResponse(BaseModel):
        duration_ms: float
        tracks_mixed: int
        audio_uploaded: bool

    def download_track(url: str, temp_dir: str, index: int) -> str:
        """Download track from presigned URL to temp file using streaming."""
        logger.info(f"Downloading track {index + 1}")
        response = requests.get(url, stream=True, timeout=300)

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Track {index} not found")
        if response.status_code == 403:
            raise HTTPException(
                status_code=403, detail=f"Track {index} presigned URL expired"
            )

        response.raise_for_status()

        temp_path = os.path.join(temp_dir, f"track_{index}.webm")
        total_bytes = 0
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)

        logger.info(f"Track {index + 1} downloaded: {total_bytes} bytes")
        return temp_path

    def mixdown_tracks_modal(
        track_paths: list[str],
        output_path: str,
        target_sample_rate: int,
        expected_duration_sec: float | None,
        logger,
    ) -> float:
        """Mix multiple audio tracks using PyAV filter graph.

        Args:
            track_paths: List of local file paths to audio tracks
            output_path: Local path for output MP3 file
            target_sample_rate: Sample rate for output (Hz)
            expected_duration_sec: Optional fallback duration if container metadata unavailable
            logger: Logger instance for progress tracking

        Returns:
            Duration in milliseconds
        """
        logger.info(f"Starting mixdown of {len(track_paths)} tracks")

        # Build PyAV filter graph: N abuffer -> amix -> aformat -> sink
        graph = av.filter.Graph()
        inputs = []

        for idx in range(len(track_paths)):
            args = (
                f"time_base=1/{target_sample_rate}:"
                f"sample_rate={target_sample_rate}:"
                f"sample_fmt=s32:"
                f"channel_layout=stereo"
            )
            in_ctx = graph.add("abuffer", args=args, name=f"in{idx}")
            inputs.append(in_ctx)

        mixer = graph.add("amix", args=f"inputs={len(inputs)}:normalize=0", name="mix")
        fmt = graph.add(
            "aformat",
            args=f"sample_fmts=s32:channel_layouts=stereo:sample_rates={target_sample_rate}",
            name="fmt",
        )
        sink = graph.add("abuffersink", name="out")

        # Connect inputs to mixer (no delays for Modal implementation)
        for idx, in_ctx in enumerate(inputs):
            in_ctx.link_to(mixer, 0, idx)

        mixer.link_to(fmt)
        fmt.link_to(sink)
        graph.configure()

        # Open all containers
        containers = []
        try:
            for i, path in enumerate(track_paths):
                try:
                    c = av.open(path)
                    containers.append(c)
                except Exception as e:
                    logger.warning(
                        f"Failed to open container {i}: {e}",
                    )

            if not containers:
                raise ValueError("Could not open any track containers")

            # Calculate total duration for progress reporting
            max_duration_sec = 0.0
            for c in containers:
                if c.duration is not None:
                    dur_sec = c.duration / av.time_base
                    max_duration_sec = max(max_duration_sec, dur_sec)
            if max_duration_sec == 0.0 and expected_duration_sec:
                max_duration_sec = expected_duration_sec

            # Setup output container
            out_container = av.open(output_path, "w", format="mp3")
            out_stream = out_container.add_stream("libmp3lame", rate=target_sample_rate)

            decoders = [c.decode(audio=0) for c in containers]
            active = [True] * len(decoders)
            resamplers = [
                AudioResampler(format="s32", layout="stereo", rate=target_sample_rate)
                for _ in decoders
            ]

            current_max_time = 0.0
            last_log_time = time.monotonic()
            start_time = time.monotonic()

            total_duration = 0

            while any(active):
                for i, (dec, is_active) in enumerate(zip(decoders, active)):
                    if not is_active:
                        continue
                    try:
                        frame = next(dec)
                    except StopIteration:
                        active[i] = False
                        inputs[i].push(None)  # Signal end of stream
                        continue

                    if frame.sample_rate != target_sample_rate:
                        continue

                    # Progress logging (every 5 seconds)
                    if frame.time is not None:
                        current_max_time = max(current_max_time, frame.time)
                        now = time.monotonic()
                        if now - last_log_time >= 5.0:
                            elapsed = now - start_time
                            if max_duration_sec > 0:
                                progress_pct = min(
                                    100.0, (current_max_time / max_duration_sec) * 100
                                )
                                logger.info(
                                    f"Mixdown progress: {progress_pct:.1f}% @ {current_max_time:.1f}s (elapsed: {elapsed:.1f}s)"
                                )
                            else:
                                logger.info(
                                    f"Mixdown progress: @ {current_max_time:.1f}s (elapsed: {elapsed:.1f}s)"
                                )
                            last_log_time = now

                    out_frames = resamplers[i].resample(frame) or []
                    for rf in out_frames:
                        rf.sample_rate = target_sample_rate
                        rf.time_base = Fraction(1, target_sample_rate)
                        inputs[i].push(rf)

                    # Pull mixed frames from sink and encode
                    while True:
                        try:
                            mixed = sink.pull()
                        except Exception:
                            break
                        mixed.sample_rate = target_sample_rate
                        mixed.time_base = Fraction(1, target_sample_rate)

                        # Encode and mux
                        for packet in out_stream.encode(mixed):
                            out_container.mux(packet)
                            total_duration += packet.duration

            # Flush remaining frames from filter graph
            while True:
                try:
                    mixed = sink.pull()
                except Exception:
                    break
                mixed.sample_rate = target_sample_rate
                mixed.time_base = Fraction(1, target_sample_rate)

                for packet in out_stream.encode(mixed):
                    out_container.mux(packet)
                    total_duration += packet.duration

            # Flush encoder
            for packet in out_stream.encode():
                out_container.mux(packet)
                total_duration += packet.duration

            # Calculate duration in milliseconds
            if total_duration > 0:
                # Use the same calculation as AudioFileWriterProcessor
                duration_ms = round(
                    float(total_duration * out_stream.time_base * 1000), 2
                )
            else:
                duration_ms = 0.0

            out_container.close()
            logger.info(f"Mixdown complete: duration={duration_ms}ms")

        finally:
            # Cleanup all containers
            for c in containers:
                if c is not None:
                    try:
                        c.close()
                    except Exception:
                        pass

        return duration_ms

    @app.post("/v1/audio/mixdown", dependencies=[Depends(apikey_auth)])
    def mixdown(request: MixdownRequest) -> MixdownResponse:
        """Mix multiple audio tracks into a single MP3 file.

        Tracks are downloaded from presigned S3 URLs, mixed using PyAV,
        and uploaded to a presigned S3 PUT URL.
        """
        if not request.track_urls:
            raise HTTPException(status_code=400, detail="No track URLs provided")

        logger.info(f"Mixdown request: {len(request.track_urls)} tracks")

        temp_dir = tempfile.mkdtemp()
        temp_files = []
        output_mp3_path = None

        try:
            # Download all tracks
            for i, url in enumerate(request.track_urls):
                temp_path = download_track(url, temp_dir, i)
                temp_files.append(temp_path)

            # Mix tracks
            output_mp3_path = os.path.join(temp_dir, "mixed.mp3")
            duration_ms = mixdown_tracks_modal(
                temp_files,
                output_mp3_path,
                request.target_sample_rate,
                request.expected_duration_sec,
                logger,
            )

            # Upload result to S3
            logger.info("Uploading result to S3")
            file_size = os.path.getsize(output_mp3_path)
            with open(output_mp3_path, "rb") as f:
                upload_response = requests.put(
                    request.output_url, data=f, timeout=300
                )

            if upload_response.status_code == 403:
                raise HTTPException(
                    status_code=403, detail="Output presigned URL expired"
                )

            upload_response.raise_for_status()
            logger.info(f"Upload complete: {file_size} bytes")

            return MixdownResponse(
                duration_ms=duration_ms,
                tracks_mixed=len(request.track_urls),
                audio_uploaded=True,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Mixdown failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Mixdown failed: {str(e)}")

        finally:
            # Cleanup temp files
            for temp_path in temp_files:
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")

            if output_mp3_path and os.path.exists(output_mp3_path):
                try:
                    os.unlink(output_mp3_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup output file {output_mp3_path}: {e}")

            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

    return app
