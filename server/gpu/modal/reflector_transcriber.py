"""
Reflector GPU backend - transcriber
===================================
"""

import tempfile
import os
from modal import Image, method, Stub, asgi_app, Secret
from pydantic import BaseModel


# Whisper
WHISPER_MODEL: str = "large-v2"
WHISPER_COMPUTE_TYPE: str = "float16"
WHISPER_NUM_WORKERS: int = 1
WHISPER_CACHE_DIR: str = "/cache/whisper"

stub = Stub(name="reflector-transcriber")


def download_whisper():
    from faster_whisper.utils import download_model

    download_model(WHISPER_MODEL, local_files_only=False)


whisper_image = (
    Image.debian_slim(python_version="3.10.8")
    .apt_install("git")
    .pip_install(
        "faster-whisper",
        "requests",
        "torch",
    )
    .run_function(download_whisper)
    .env(
        {
            "LD_LIBRARY_PATH": (
                "/usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib/:"
                "/opt/conda/lib/python3.10/site-packages/nvidia/cublas/lib/"
            )
        }
    )
)


@stub.cls(
    gpu="A10G",
    container_idle_timeout=60,
    image=whisper_image,
)
class Whisper:
    def __enter__(self):
        import torch
        import faster_whisper

        self.use_gpu = torch.cuda.is_available()
        device = "cuda" if self.use_gpu else "cpu"
        self.model = faster_whisper.WhisperModel(
            WHISPER_MODEL,
            device=device,
            compute_type=WHISPER_COMPUTE_TYPE,
            num_workers=WHISPER_NUM_WORKERS,
        )

    @method()
    def warmup(self):
        return {"status": "ok"}

    @method()
    def transcribe_segment(
        self,
        audio_data: str,
        audio_suffix: str,
        timestamp: float = 0,
        language: str = "en",
    ):
        with tempfile.NamedTemporaryFile("wb+", suffix=f".{audio_suffix}") as fp:
            fp.write(audio_data)

            segments, _ = self.model.transcribe(
                fp.name,
                language=language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )

            transcript = ""
            words = []
            if segments:
                segments = list(segments)

                for segment in segments:
                    transcript += segment.text
                    for word in segment.words:
                        words.append(
                            {
                                "text": word.word,
                                "start": round(timestamp + word.start, 3),
                                "end": round(timestamp + word.end, 3),
                            }
                        )
            return {
                "text": transcript,
                "words": words,
            }


# -------------------------------------------------------------------
# Web API
# -------------------------------------------------------------------


@stub.function(
    container_idle_timeout=60,
    timeout=60,
    secrets=[
        Secret.from_name("reflector-gpu"),
    ],
)
@asgi_app()
def web():
    from fastapi import FastAPI, UploadFile, Form, Depends, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from typing_extensions import Annotated

    transcriberstub = Whisper()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey != os.environ["REFLECTOR_GPU_APIKEY"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    class TranscriptionRequest(BaseModel):
        timestamp: float = 0
        language: str = "en"

    class TranscriptResponse(BaseModel):
        result: str

    @app.post("/transcribe", dependencies=[Depends(apikey_auth)])
    async def transcribe(
        file: UploadFile,
        timestamp: Annotated[float, Form()] = 0,
        language: Annotated[str, Form()] = "en",
    ):
        audio_data = await file.read()
        audio_suffix = file.filename.split(".")[-1]
        assert audio_suffix in ["wav", "mp3", "ogg", "flac"]

        func = transcriberstub.transcribe_segment.spawn(
            audio_data=audio_data,
            audio_suffix=audio_suffix,
            language=language,
            timestamp=timestamp,
        )
        result = func.get()
        return result

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        return transcriberstub.warmup.spawn().get()

    return app
