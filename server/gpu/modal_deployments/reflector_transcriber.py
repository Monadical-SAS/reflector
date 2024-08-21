"""
Reflector GPU backend - transcriber
===================================
"""

import os
import tempfile
import threading

from modal import Image, Secret, App, asgi_app, method, enter
from pydantic import BaseModel

# Whisper
WHISPER_MODEL: str = "large-v2"
WHISPER_COMPUTE_TYPE: str = "float16"
WHISPER_NUM_WORKERS: int = 1


WHISPER_MODEL_DIR = "/root/transcription_models"

app = App(name="reflector-transcriber")


def download_whisper():
    from faster_whisper.utils import download_model

    print("Downloading Whisper model")
    download_model(WHISPER_MODEL, cache_dir=WHISPER_MODEL_DIR)
    print("Whisper model downloaded")


def migrate_cache_llm():
    """
    XXX The cache for model files in Transformers v4.22.0 has been updated.
    Migrating your old cache. This is a one-time only operation. You can
    interrupt this and resume the migration later on by calling
    `transformers.utils.move_cache()`.
    """
    from transformers.utils.hub import move_cache

    print("Moving LLM cache")
    move_cache(cache_dir=WHISPER_MODEL_DIR, new_cache_dir=WHISPER_MODEL_DIR)
    print("LLM cache moved")


transcriber_image = (
    Image.debian_slim(python_version="3.10.8")
    .apt_install("git")
    .apt_install("wget")
    .apt_install("libsndfile-dev")
    .pip_install(
        "faster-whisper",
        "requests",
        "torch",
        "transformers==4.34.0",
        "sentencepiece",
        "protobuf",
        "huggingface_hub==0.16.4",
        "gitpython",
        "torchaudio",
        "fairseq2",
        "pyyaml",
        "hf-transfer~=0.1"
    )
    .run_function(download_whisper)
    .run_function(migrate_cache_llm)
    .env(
        {
            "LD_LIBRARY_PATH": (
                "/usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib/:"
                "/opt/conda/lib/python3.10/site-packages/nvidia/cublas/lib/"
            )
        }
    )
)


@app.cls(
    gpu="A10G",
    timeout=60 * 5,
    container_idle_timeout=60 * 5,
    allow_concurrent_inputs=6,
    image=transcriber_image,
)
class Transcriber:
    @enter()
    def enter(self):
        import faster_whisper
        import torch

        self.lock = threading.Lock()
        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.model = faster_whisper.WhisperModel(
            WHISPER_MODEL,
            device=self.device,
            compute_type=WHISPER_COMPUTE_TYPE,
            num_workers=WHISPER_NUM_WORKERS,
            download_root=WHISPER_MODEL_DIR,
            local_files_only=True
        )

    @method()
    def transcribe_segment(
        self,
        audio_data: str,
        audio_suffix: str,
        source_language: str,
        timestamp: float = 0
    ):
        with tempfile.NamedTemporaryFile("wb+", suffix=f".{audio_suffix}") as fp:
            fp.write(audio_data)

            with self.lock:
                segments, _ = self.model.transcribe(
                    fp.name,
                    language=source_language,
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                )

            multilingual_transcript = {}
            transcript_source_lang = ""
            words = []
            if segments:
                segments = list(segments)

                for segment in segments:
                    transcript_source_lang += segment.text
                    for word in segment.words:
                        words.append(
                            {
                                "text": word.word,
                                "start": round(timestamp + word.start, 3),
                                "end": round(timestamp + word.end, 3),
                            }
                        )

            multilingual_transcript[source_language] = transcript_source_lang

            return {
                "text": multilingual_transcript,
                "words": words
            }

# -------------------------------------------------------------------
# Web API
# -------------------------------------------------------------------


@app.function(
    container_idle_timeout=60,
    timeout=60,
    allow_concurrent_inputs=40,
    secrets=[
        Secret.from_name("reflector-gpu"),
    ],
)
@asgi_app()
def web():
    from fastapi import Body, Depends, FastAPI, HTTPException, UploadFile, status
    from fastapi.security import OAuth2PasswordBearer
    from typing_extensions import Annotated

    transcriberstub = Transcriber()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    supported_audio_file_types = ["wav", "mp3", "ogg", "flac"]

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey != os.environ["REFLECTOR_GPU_APIKEY"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    class TranscriptResponse(BaseModel):
        result: dict

    @app.post("/transcribe", dependencies=[Depends(apikey_auth)])
    def transcribe(
        file: UploadFile,
        source_language: Annotated[str, Body(...)] = "en",
        timestamp: Annotated[float, Body()] = 0.0
    ) -> TranscriptResponse:
        audio_data = file.file.read()
        audio_suffix = file.filename.split(".")[-1]
        assert audio_suffix in supported_audio_file_types

        func = transcriberstub.transcribe_segment.spawn(
            audio_data=audio_data,
            audio_suffix=audio_suffix,
            source_language=source_language,
            timestamp=timestamp
        )
        result = func.get()
        return result

    return app
