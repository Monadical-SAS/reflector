import os
import tempfile
import threading

import modal
from pydantic import BaseModel

MODELS_DIR = "/models"

MODEL_NAME = "large-v2"
MODEL_COMPUTE_TYPE: str = "float16"
MODEL_NUM_WORKERS: int = 1

MINUTES = 60  # seconds

volume = modal.Volume.from_name("models", create_if_missing=True)

app = modal.App("reflector-transcriber")


def download_model():
    from faster_whisper import download_model

    volume.reload()

    download_model(MODEL_NAME, cache_dir=MODELS_DIR)

    volume.commit()


image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "huggingface_hub==0.27.1",
        "hf-transfer==0.1.9",
        "torch==2.5.1",
        "faster-whisper==1.1.1",
    )
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "LD_LIBRARY_PATH": (
                "/usr/local/lib/python3.12/site-packages/nvidia/cudnn/lib/:"
                "/opt/conda/lib/python3.12/site-packages/nvidia/cublas/lib/"
            ),
        }
    )
    .run_function(download_model, volumes={MODELS_DIR: volume})
)


@app.cls(
    gpu="A10G",
    timeout=5 * MINUTES,
    container_idle_timeout=5 * MINUTES,
    allow_concurrent_inputs=6,
    image=image,
    volumes={MODELS_DIR: volume},
)
class Transcriber:
    @modal.enter()
    def enter(self):
        import faster_whisper
        import torch

        self.lock = threading.Lock()
        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.model = faster_whisper.WhisperModel(
            MODEL_NAME,
            device=self.device,
            compute_type=MODEL_COMPUTE_TYPE,
            num_workers=MODEL_NUM_WORKERS,
            download_root=MODELS_DIR,
            local_files_only=True,
        )

    @modal.method()
    def transcribe_segment(
        self,
        audio_data: str,
        audio_suffix: str,
        language: str,
    ):
        with tempfile.NamedTemporaryFile("wb+", suffix=f".{audio_suffix}") as fp:
            fp.write(audio_data)

            with self.lock:
                segments, _ = self.model.transcribe(
                    fp.name,
                    language=language,
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                )

            text = ""
            words = []
            for segment in segments:
                text += segment.text
                words.extend(
                    {"word": word.word, "start": word.start, "end": word.end}
                    for word in segment.words
                )

            return {"text": text, "words": words}


@app.function(
    container_idle_timeout=60,
    timeout=60,
    allow_concurrent_inputs=40,
    secrets=[
        modal.Secret.from_name("reflector-gpu"),
    ],
    volumes={MODELS_DIR: volume},
)
@modal.asgi_app()
def web():
    from fastapi import Body, Depends, FastAPI, HTTPException, UploadFile, status
    from fastapi.security import OAuth2PasswordBearer
    from typing_extensions import Annotated

    transcriber = Transcriber()

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
        model: str = "whisper-1",
        language: Annotated[str, Body(...)] = "en",
    ) -> TranscriptResponse:
        audio_data = file.file.read()
        audio_suffix = file.filename.split(".")[-1]
        assert audio_suffix in supported_file_types

        func = transcriber.transcribe_segment.spawn(
            audio_data=audio_data,
            audio_suffix=audio_suffix,
            language=language,
        )
        result = func.get()
        return result

    return app
