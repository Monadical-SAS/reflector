"""
Reflector GPU backend - audio padding
======================================

CPU-intensive audio padding service for adding silence to audio tracks.
Uses PyAV filter graph (adelay) for precise track synchronization.
"""

import os
import tempfile
import time
from fractions import Fraction
import math

import modal

PADDING_TIMEOUT = 900  # 15 minutes
SCALEDOWN_WINDOW = 60  # 1 minute idle before shutdown

app = modal.App("reflector-padding")

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

# Constants matching local implementation
OPUS_STANDARD_SAMPLE_RATE = 48000
OPUS_DEFAULT_BIT_RATE = 32000


@app.function(
    cpu=2.0,  # 2 CPU cores for audio processing
    timeout=PADDING_TIMEOUT,
    scaledown_window=SCALEDOWN_WINDOW,
    secrets=[modal.Secret.from_name("reflector-gpu")],
    image=image,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    import logging
    import secrets

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

    class PaddingRequest(BaseModel):
        track_url: str
        output_url: str
        start_time_seconds: float
        track_index: int

    class PaddingResponse(BaseModel):
        size: int
        audio_uploaded: bool

    def download_track(url: str, temp_dir: str) -> str:
        """Download track from presigned URL to temp file using streaming."""
        logger.info("Downloading track for padding")
        response = requests.get(url, stream=True, timeout=300)

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Track not found")
        if response.status_code == 403:
            raise HTTPException(
                status_code=403, detail="Track presigned URL expired"
            )

        response.raise_for_status()

        temp_path = os.path.join(temp_dir, "track.webm")
        total_bytes = 0
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)

        logger.info(f"Track downloaded: {total_bytes} bytes")
        return temp_path

    def apply_padding_modal(
        input_path: str,
        output_path: str,
        start_time_seconds: float,
        track_idx: int,
        logger,
    ) -> int:
        """Apply silence padding to audio track using PyAV filter graph.

        Args:
            input_path: Local path to input audio file
            output_path: Local path for output WebM file
            start_time_seconds: Amount of silence to prepend (in seconds)
            track_idx: Track index for logging context
            logger: Logger instance for progress tracking

        Returns:
            File size in bytes

        Raises:
            ValueError: If no audio stream found
            Exception: If PyAV processing fails
        """
        delay_ms = math.floor(start_time_seconds * 1000)

        logger.info(
            f"Padding track {track_idx} with {delay_ms}ms delay using PyAV",
        )

        try:
            in_container = av.open(input_path)
            in_stream = next(
                (s for s in in_container.streams if s.type == "audio"), None
            )
            if in_stream is None:
                raise ValueError("No audio stream in input")

            with av.open(output_path, "w", format="webm") as out_container:
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

            in_container.close()

            file_size = os.path.getsize(output_path)
            logger.info(f"Padding complete: {file_size} bytes")
            return file_size

        except Exception as e:
            logger.error(
                f"PyAV padding failed for track {track_idx}",
                exc_info=True,
            )
            raise

    @app.post("/v1/audio/padding", dependencies=[Depends(apikey_auth)])
    def pad_track(request: PaddingRequest) -> PaddingResponse:
        """Pad audio track with silence to align with meeting start time.

        Track is downloaded from presigned S3 URL, padded using PyAV,
        and uploaded to a presigned S3 PUT URL.
        """
        if not request.track_url:
            raise HTTPException(status_code=400, detail="No track URL provided")

        if request.start_time_seconds <= 0:
            raise HTTPException(
                status_code=400, detail="start_time_seconds must be positive"
            )

        logger.info(
            f"Padding request: track {request.track_index}, delay={request.start_time_seconds}s"
        )

        temp_dir = tempfile.mkdtemp()
        input_path = None
        output_path = None

        try:
            # Download track
            input_path = download_track(request.track_url, temp_dir)

            # Apply padding
            output_path = os.path.join(temp_dir, "padded.webm")
            file_size = apply_padding_modal(
                input_path,
                output_path,
                request.start_time_seconds,
                request.track_index,
                logger,
            )

            # Upload result to S3
            logger.info("Uploading padded track to S3")
            with open(output_path, "rb") as f:
                upload_response = requests.put(request.output_url, data=f, timeout=300)

            if upload_response.status_code == 403:
                raise HTTPException(
                    status_code=403, detail="Output presigned URL expired"
                )

            upload_response.raise_for_status()
            logger.info(f"Upload complete: {file_size} bytes")

            return PaddingResponse(
                size=file_size,
                audio_uploaded=True,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Padding failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Padding failed: {str(e)}")

        finally:
            # Cleanup temp files
            if input_path and os.path.exists(input_path):
                try:
                    os.unlink(input_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup input file {input_path}: {e}")

            if output_path and os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup output file {output_path}: {e}")

            try:
                os.rmdir(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

    return app
