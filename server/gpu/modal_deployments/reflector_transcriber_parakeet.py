import os
import threading

import modal
from pydantic import BaseModel

# Volume for caching model weights
model_cache = modal.Volume.from_name("parakeet-model-cache", create_if_missing=True)

# App configuration
app = modal.App("reflector-transcriber-parakeet")

MINUTES = 60  # seconds

# Image configuration using modern Modal SDK patterns from parakeet.py
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04", add_python="3.12"
    )
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_HOME": "/cache",  # cache directory for Hugging Face models
            "DEBIAN_FRONTEND": "noninteractive",
            "CXX": "g++",
            "CC": "g++",
        }
    )
    .apt_install("ffmpeg")
    .pip_install(
        "hf_transfer==0.1.9",
        "huggingface_hub[hf-xet]==0.31.2",
        "nemo_toolkit[asr]==2.3.0",
        "cuda-python==12.8.0",
        "fastapi==0.115.12",
        "numpy<2",
        "pydub==0.25.1",
    )
    .entrypoint([])  # silence chatty logs by container on start
)


@app.cls(
    gpu="A10G",
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
    image=image,
    volumes={"/cache": model_cache},
)
@modal.concurrent(max_inputs=6)
class TranscriberParakeet:
    @modal.enter()
    def enter(self):
        import logging

        import nemo.collections.asr as nemo_asr

        # silence chatty logs from nemo
        logging.getLogger("nemo_logger").setLevel(logging.CRITICAL)

        self.lock = threading.Lock()
        self.model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v2"
        )

    @modal.method()
    def transcribe_segment(
        self,
        audio_data: bytes,
        audio_suffix: str,
        language: str,
    ):
        import io

        import numpy as np
        from pydub import AudioSegment

        # Convert audio data to proper format
        if audio_suffix.lower() == "mp3":
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
        elif audio_suffix.lower() == "wav":
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
        else:
            # Try to handle as wav by default
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))

        # Convert to 16kHz mono format as required by Parakeet
        audio = audio.set_frame_rate(16000).set_channels(1)

        # Split long audio into chunks based on silence to avoid CUDA OOM
        all_text_parts = []
        all_words = []
        total_duration = 0.0

        # Always chunk audio longer than 15 seconds to avoid CUDA OOM
        if len(audio) > 15 * 1000:  # 15 seconds in milliseconds
            chunks = self._split_audio_on_silence(audio)
        else:
            chunks = [audio]

        for chunk in chunks:
            if len(chunk) < 500:  # Skip very short chunks (less than 0.5 seconds)
                continue

            chunk_array = np.frombuffer(chunk.raw_data, dtype=np.int16).astype(
                np.float32
            )

            with self.lock:
                # Use NoStdStreams context manager to silence output
                with NoStdStreams():
                    output = self.model.transcribe([chunk_array], timestamps=True)

            chunk_text = output[0].text.strip()
            if chunk_text:  # Only add non-empty transcriptions
                all_text_parts.append(chunk_text)

            # Extract word timestamps and adjust for cumulative time
            if (
                hasattr(output[0], "timestamp")
                and output[0].timestamp
                and "word" in output[0].timestamp
            ):
                chunk_words = [
                    {
                        "word": word_info["word"],
                        "start": word_info["start"] + total_duration,
                        "end": word_info["end"] + total_duration,
                    }
                    for word_info in output[0].timestamp["word"]
                ]
                all_words.extend(chunk_words)

            # Update total duration for next chunk
            total_duration += len(chunk) / 1000.0  # Convert to seconds

        # Combine all text parts
        combined_text = " ".join(all_text_parts)

        return {"text": combined_text, "words": all_words}

    def _split_audio_on_silence(
        self,
        audio,
        silence_thresh=-45,  # dB
        min_silence_len=2000,  # ms
        chunk_len=5000,  # 5 seconds max per chunk
    ):
        """Split audio on silence, with fallback to fixed-size chunks"""
        from pydub import silence

        # Find silent segments
        silent_ranges = silence.detect_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
        )

        chunks = []
        start = 0

        for silent_start, silent_end in silent_ranges:
            # If chunk would be too long, split it further
            if silent_start - start > chunk_len:
                # Split into smaller fixed-size chunks
                while start + chunk_len < silent_start:
                    chunks.append(audio[start : start + chunk_len])
                    start += chunk_len

            # Add chunk up to silence
            if silent_start > start:
                chunks.append(audio[start:silent_start])

            # Skip the silence and continue from after it
            start = silent_end

        # Add remaining audio
        if start < len(audio):
            remaining = audio[start:]
            # If remaining is too long, split it
            while len(remaining) > chunk_len:
                chunks.append(remaining[:chunk_len])
                remaining = remaining[chunk_len:]
            if len(remaining) > 500:  # Only add if longer than 0.5 seconds
                chunks.append(remaining)

        # If no silence was found and audio is long, fall back to fixed-size chunks
        if not chunks and len(audio) > chunk_len:
            for i in range(0, len(audio), chunk_len):
                chunk = audio[i : i + chunk_len]
                if len(chunk) > 500:  # Only add chunks longer than 0.5 seconds
                    chunks.append(chunk)
        elif not chunks:
            chunks = [audio]

        return chunks

    @modal.method()
    def transcribe_with_progress(
        self,
        audio_data: bytes,
        audio_suffix: str,
        language: str,
    ):
        """Process transcription and return results with progress info"""
        import io

        import numpy as np
        from pydub import AudioSegment

        # Convert audio data to proper format
        if audio_suffix.lower() == "mp3":
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
        elif audio_suffix.lower() == "wav":
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
        else:
            # Try to handle as wav by default
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))

        # Convert to 16kHz mono format as required by Parakeet
        audio = audio.set_frame_rate(16000).set_channels(1)

        # Split long audio into chunks based on silence to avoid CUDA OOM
        all_text_parts = []
        all_words = []
        total_duration = 0.0
        results = []  # Store all progress updates

        # Always chunk audio longer than 15 seconds to avoid CUDA OOM
        if len(audio) > 15 * 1000:  # 15 seconds in milliseconds
            chunks = self._split_audio_on_silence(audio)
        else:
            chunks = [audio]

        total_chunks = len(chunks)

        for chunk_index, chunk in enumerate(chunks):
            if len(chunk) < 500:  # Skip very short chunks (less than 0.5 seconds)
                continue

            chunk_array = np.frombuffer(chunk.raw_data, dtype=np.int16).astype(
                np.float32
            )

            with self.lock:
                # Use NoStdStreams context manager to silence output
                with NoStdStreams():
                    output = self.model.transcribe([chunk_array], timestamps=True)

            chunk_text = output[0].text.strip()
            if chunk_text:  # Only add non-empty transcriptions
                all_text_parts.append(chunk_text)

            # Extract word timestamps and adjust for cumulative time
            chunk_words = []
            if (
                hasattr(output[0], "timestamp")
                and output[0].timestamp
                and "word" in output[0].timestamp
            ):
                chunk_words = [
                    {
                        "word": word_info["word"],
                        "start": word_info["start"] + total_duration,
                        "end": word_info["end"] + total_duration,
                    }
                    for word_info in output[0].timestamp["word"]
                ]
                all_words.extend(chunk_words)

            # Store progress update
            progress_update = {
                "type": "progress",
                "chunk_index": chunk_index + 1,
                "total_chunks": total_chunks,
                "text": chunk_text,
                "words": chunk_words,
            }
            results.append(progress_update)

            # Update total duration for next chunk
            total_duration += len(chunk) / 1000.0  # Convert to seconds

        # Add final result
        combined_text = " ".join(all_text_parts)

        final_result = {"type": "final", "text": combined_text, "words": all_words}
        results.append(final_result)

        return results


@app.function(
    scaledown_window=60,
    timeout=600,
    secrets=[
        modal.Secret.from_name("reflector-gpu"),
    ],
    volumes={"/cache": model_cache},
    image=image,
)
@modal.concurrent(max_inputs=40)
@modal.asgi_app()
def web():
    from fastapi import Body, Depends, FastAPI, HTTPException, Query, UploadFile, status
    from fastapi.responses import StreamingResponse
    from fastapi.security import OAuth2PasswordBearer
    from typing_extensions import Annotated

    transcriber = TranscriberParakeet()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    supported_file_types = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey != os.environ["REFLECTOR_GPU_APIKEY"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    class TranscriptResponse(BaseModel):
        result: dict

    @app.post("/v1/audio/transcriptions", dependencies=[Depends(apikey_auth)])
    def transcribe(
        file: UploadFile,
        model: str = "parakeet-tdt-0.6b-v2",
        language: Annotated[str, Body(...)] = "en",
        stream: bool = Query(False, description="Enable streaming response"),
    ):
        audio_data = file.file.read()
        audio_suffix = file.filename.split(".")[-1]
        assert audio_suffix in supported_file_types

        if stream:
            # Return streaming response
            return StreamingResponse(
                stream_transcription(transcriber, audio_data, audio_suffix, language),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )
        else:
            # Return standard synchronous response
            func = transcriber.transcribe_segment.spawn(
                audio_data=audio_data,
                audio_suffix=audio_suffix,
                language=language,
            )
            result = func.get()
            return result

    async def stream_transcription(
        transcriber, audio_data: bytes, audio_suffix: str, language: str
    ):
        import json

        func = transcriber.transcribe_with_progress.spawn(
            audio_data=audio_data,
            audio_suffix=audio_suffix,
            language=language,
        )
        results = func.get()

        for result in results:
            if result["type"] == "progress":
                data = {
                    "type": "progress",
                    "chunk_index": result["chunk_index"],
                    "total_chunks": result["total_chunks"],
                    "partial_text": result["text"],
                    "chunk_words": result["words"],
                }
                yield f"data: {json.dumps(data)}\n\n"

            elif result["type"] == "final":
                data = {
                    "type": "final",
                    "text": result["text"],
                    "words": result["words"],
                }
                yield f"data: {json.dumps(data)}\n\n"
                yield "data: [DONE]\n\n"

    return app


# Helper class to silence noisy output from NeMo
class NoStdStreams:
    def __init__(self):
        import os

        self.devnull = open(os.devnull, "w")

    def __enter__(self):
        import sys

        self._stdout, self._stderr = sys.stdout, sys.stderr
        self._stdout.flush(), self._stderr.flush()
        sys.stdout, sys.stderr = self.devnull, self.devnull

    def __exit__(self, exc_type, exc_value, traceback):
        import sys

        sys.stdout, sys.stderr = self._stdout, self._stderr
        self.devnull.close()
