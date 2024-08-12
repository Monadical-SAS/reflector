"""
Reflector GPU backend - diarizer
===================================
"""

import os

import modal.gpu
from modal import Image, Secret, App, asgi_app, method, enter
from pydantic import BaseModel

PYANNOTE_MODEL_NAME: str = "pyannote/speaker-diarization-3.1"
MODEL_DIR = "/root/diarization_models"
app = App(name="reflector-diarizer")


def migrate_cache_llm():
    """
    XXX The cache for model files in Transformers v4.22.0 has been updated.
    Migrating your old cache. This is a one-time only operation. You can
    interrupt this and resume the migration later on by calling
    `transformers.utils.move_cache()`.
    """
    from transformers.utils.hub import move_cache

    print("Moving LLM cache")
    move_cache(cache_dir=MODEL_DIR, new_cache_dir=MODEL_DIR)
    print("LLM cache moved")


def download_pyannote_audio():
    from pyannote.audio import Pipeline
    Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.0",
        cache_dir=MODEL_DIR,
    )


diarizer_image = (
    Image.debian_slim(python_version="3.10.8")
    .pip_install(
        "pyannote.audio",
        "requests",
        "onnx",
        "torchaudio",
        "onnxruntime-gpu",
        "torch==2.0.0",
        "transformers==4.34.0",
        "sentencepiece",
        "protobuf",
        "numpy",
        "huggingface_hub",
        "hf-transfer"
    )
    .run_function(migrate_cache_llm)
    .run_function(download_pyannote_audio)
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
    gpu=modal.gpu.A100(memory=40),
    timeout=60 * 30,
    container_idle_timeout=60,
    allow_concurrent_inputs=1,
    image=diarizer_image,
)
class Diarizer:
    @enter()
    def enter(self):
        import torch
        from pyannote.audio import Pipeline

        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.0",
            cache_dir=MODEL_DIR
        )
        self.diarization_pipeline.to(torch.device(self.device))

    @method()
    def diarize(
            self,
            audio_data: str,
            audio_suffix: str,
            timestamp: float
    ):
        import tempfile

        import torchaudio

        with tempfile.NamedTemporaryFile("wb+", suffix=f".{audio_suffix}") as fp:
            fp.write(audio_data)

            print("Diarizing audio")
            waveform, sample_rate = torchaudio.load(fp.name)
            diarization = self.diarization_pipeline({"waveform": waveform, "sample_rate": sample_rate})

            words = []
            for diarization_segment, _, speaker in diarization.itertracks(yield_label=True):
                words.append(
                    {
                        "start": round(timestamp + diarization_segment.start, 3),
                        "end": round(timestamp + diarization_segment.end, 3),
                        "speaker": int(speaker[-2:])
                    }
                )
            print("Diarization complete")
            return {
                "diarization": words
            }

# -------------------------------------------------------------------
# Web API
# -------------------------------------------------------------------


@app.function(
    timeout=60 * 10,
    container_idle_timeout=60 * 3,
    allow_concurrent_inputs=40,
    secrets=[
        Secret.from_name("reflector-gpu"),
    ],
    image=diarizer_image
)
@asgi_app()
def web():
    import requests
    from fastapi import Depends, FastAPI, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer

    diarizerstub = Diarizer()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey != os.environ["REFLECTOR_GPU_APIKEY"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def validate_audio_file(audio_file_url: str):
        # Check if the audio file exists
        response = requests.head(audio_file_url, allow_redirects=True)
        if response.status_code == 404:
            raise HTTPException(
                status_code=response.status_code,
                detail="The audio file does not exist."
            )

    class DiarizationResponse(BaseModel):
        result: dict

    @app.post("/diarize", dependencies=[Depends(apikey_auth), Depends(validate_audio_file)])
    def diarize(
            audio_file_url: str,
            timestamp: float = 0.0
    ) -> HTTPException | DiarizationResponse:
        # Currently the uploaded files are in mp3 format
        audio_suffix = "mp3"

        print("Downloading audio file")
        response = requests.get(audio_file_url, allow_redirects=True)
        print("Audio file downloaded successfully")

        func = diarizerstub.diarize.spawn(
            audio_data=response.content,
            audio_suffix=audio_suffix,
            timestamp=timestamp
        )
        result = func.get()
        return result

    return app
