"""
Reflector GPU backend - diarizer
===================================
"""

import os
import uuid
from typing import Mapping, NewType
from urllib.parse import urlparse

import modal

PYANNOTE_MODEL_NAME: str = "pyannote/speaker-diarization-3.1"
MODEL_DIR = "/root/diarization_models"
UPLOADS_PATH = "/uploads"
SUPPORTED_FILE_EXTENSIONS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

DiarizerUniqFilename = NewType("DiarizerUniqFilename", str)
AudioFileExtension = NewType("AudioFileExtension", str)

app = modal.App(name="reflector-diarizer")

# Volume for temporary file uploads
upload_volume = modal.Volume.from_name("diarizer-uploads", create_if_missing=True)


def detect_audio_format(url: str, headers: Mapping[str, str]) -> AudioFileExtension:
    parsed_url = urlparse(url)
    url_path = parsed_url.path

    for ext in SUPPORTED_FILE_EXTENSIONS:
        if url_path.lower().endswith(f".{ext}"):
            return AudioFileExtension(ext)

    content_type = headers.get("content-type", "").lower()
    if "audio/mpeg" in content_type or "audio/mp3" in content_type:
        return AudioFileExtension("mp3")
    if "audio/wav" in content_type:
        return AudioFileExtension("wav")
    if "audio/mp4" in content_type:
        return AudioFileExtension("mp4")

    raise ValueError(
        f"Unsupported audio format for URL: {url}. "
        f"Supported extensions: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
    )


def download_audio_to_volume(
    audio_file_url: str,
) -> tuple[DiarizerUniqFilename, AudioFileExtension]:
    import requests
    from fastapi import HTTPException

    print(f"Checking audio file at: {audio_file_url}")
    response = requests.head(audio_file_url, allow_redirects=True)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Audio file not found")

    print(f"Downloading audio file from: {audio_file_url}")
    response = requests.get(audio_file_url, allow_redirects=True)

    if response.status_code != 200:
        print(f"Download failed with status {response.status_code}: {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to download audio file: {response.status_code}",
        )

    audio_suffix = detect_audio_format(audio_file_url, response.headers)
    unique_filename = DiarizerUniqFilename(f"{uuid.uuid4()}.{audio_suffix}")
    file_path = f"{UPLOADS_PATH}/{unique_filename}"

    print(f"Writing file to: {file_path} (size: {len(response.content)} bytes)")
    with open(file_path, "wb") as f:
        f.write(response.content)

    upload_volume.commit()
    print(f"File saved as: {unique_filename}")
    return unique_filename, audio_suffix


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
        PYANNOTE_MODEL_NAME,
        cache_dir=MODEL_DIR,
        use_auth_token=os.environ["HF_TOKEN"],
    )


diarizer_image = (
    modal.Image.debian_slim(python_version="3.10.8")
    .pip_install(
        "pyannote.audio==3.1.0",
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
        "hf-transfer",
    )
    .run_function(
        download_pyannote_audio,
        secrets=[modal.Secret.from_name("hf_token")],
    )
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
    gpu="A100",
    timeout=60 * 30,
    image=diarizer_image,
    volumes={UPLOADS_PATH: upload_volume},
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
    secrets=[
        modal.Secret.from_name("hf_token"),
    ],
)
@modal.concurrent(max_inputs=1)
class Diarizer:
    @modal.enter(snap=True)
    def enter(self):
        import torch
        from pyannote.audio import Pipeline

        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        print(f"Using device: {self.device}")
        self.diarization_pipeline = Pipeline.from_pretrained(
            PYANNOTE_MODEL_NAME,
            cache_dir=MODEL_DIR,
            use_auth_token=os.environ["HF_TOKEN"],
        )
        self.diarization_pipeline.to(torch.device(self.device))

    @modal.method()
    def diarize(self, filename: str, timestamp: float = 0.0):
        import torchaudio

        upload_volume.reload()

        file_path = f"{UPLOADS_PATH}/{filename}"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"Diarizing audio from: {file_path}")
        waveform, sample_rate = torchaudio.load(file_path)
        diarization = self.diarization_pipeline(
            {"waveform": waveform, "sample_rate": sample_rate}
        )

        words = []
        for diarization_segment, _, speaker in diarization.itertracks(yield_label=True):
            words.append(
                {
                    "start": round(timestamp + diarization_segment.start, 3),
                    "end": round(timestamp + diarization_segment.end, 3),
                    "speaker": int(speaker[-2:]),
                }
            )
        print("Diarization complete")
        return {"diarization": words}


# -------------------------------------------------------------------
# Web API
# -------------------------------------------------------------------


@app.function(
    timeout=60 * 10,
    scaledown_window=60 * 3,
    secrets=[
        modal.Secret.from_name("reflector-gpu"),
    ],
    volumes={UPLOADS_PATH: upload_volume},
    image=diarizer_image,
)
@modal.concurrent(max_inputs=40)
@modal.asgi_app()
def web():
    from fastapi import Depends, FastAPI, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from pydantic import BaseModel

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

    class DiarizationResponse(BaseModel):
        result: dict

    @app.post("/diarize", dependencies=[Depends(apikey_auth)])
    def diarize(audio_file_url: str, timestamp: float = 0.0) -> DiarizationResponse:
        unique_filename, audio_suffix = download_audio_to_volume(audio_file_url)

        try:
            func = diarizerstub.diarize.spawn(
                filename=unique_filename, timestamp=timestamp
            )
            result = func.get()
            return result
        finally:
            try:
                file_path = f"{UPLOADS_PATH}/{unique_filename}"
                print(f"Deleting file: {file_path}")
                os.remove(file_path)
                upload_volume.commit()
            except Exception as e:
                print(f"Error cleaning up {unique_filename}: {e}")

    return app
