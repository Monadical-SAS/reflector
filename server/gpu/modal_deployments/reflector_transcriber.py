import os
import tempfile
import threading

import modal

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
        "fastapi==0.115.12",
        "requests",
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
    scaledown_window=5 * MINUTES,
    image=image,
    volumes={MODELS_DIR: volume},
)
@modal.concurrent(max_inputs=6)
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
        audio_data: bytes,
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

            segments = list(segments)
            text = "".join(segment.text for segment in segments)
            words = [
                {"word": word.word, "start": word.start, "end": word.end}
                for segment in segments
                for word in segment.words
            ]

            return {"text": text, "words": words}


@app.function(
    scaledown_window=60,
    timeout=60,
    secrets=[
        modal.Secret.from_name("reflector-gpu"),
    ],
    volumes={MODELS_DIR: volume},
    image=image,
)
@modal.concurrent(max_inputs=40)
@modal.asgi_app()
def web():
    import uuid

    from fastapi import (
        Body,
        Depends,
        FastAPI,
        Form,
        HTTPException,
        UploadFile,
        status,
    )
    from fastapi.security import OAuth2PasswordBearer

    transcriber = Transcriber()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    supported_file_types = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey == os.environ["REFLECTOR_GPU_APIKEY"]:
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def detect_audio_format(url: str, headers: dict) -> str:
        from urllib.parse import urlparse

        url_path = urlparse(url).path
        for ext in supported_file_types:
            if url_path.lower().endswith(f".{ext}"):
                return ext

        content_type = headers.get("content-type", "").lower()
        if "audio/mpeg" in content_type or "audio/mp3" in content_type:
            return "mp3"
        if "audio/wav" in content_type:
            return "wav"
        if "audio/mp4" in content_type:
            return "mp4"

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported audio format for URL. Supported extensions: {', '.join(supported_file_types)}"
            ),
        )

    @app.post("/v1/audio/transcriptions", dependencies=[Depends(apikey_auth)])
    def transcribe(
        file: UploadFile | None = None,
        files: list[UploadFile] | None = None,
        model: str = Form(MODEL_NAME),
        language: str = Form("en"),
        batch: bool = Form(False),
    ):
        if not file and not files:
            raise HTTPException(
                status_code=400, detail="Either 'file' or 'files' parameter is required"
            )

        upload_files = [file] if file else files
        results = []

        for upload_file in upload_files:
            audio_suffix = upload_file.filename.split(".")[-1]
            assert audio_suffix in supported_file_types

            content = upload_file.file.read()
            func = transcriber.transcribe_segment.spawn(
                audio_data=content,
                audio_suffix=audio_suffix,
                language=language,
            )
            result = func.get()
            result["filename"] = upload_file.filename or str(uuid.uuid4())
            results.append(result)

        return {"results": results} if len(results) > 1 else results[0]

    @app.post("/v1/audio/transcriptions-from-url", dependencies=[Depends(apikey_auth)])
    def transcribe_from_url(
        audio_file_url: str = Body(
            ..., description="URL of the audio file to transcribe"
        ),
        model: str = Body(MODEL_NAME),
        language: str = Body("en"),
        timestamp_offset: float = Body(0.0),
    ):
        import requests

        head_response = requests.head(audio_file_url, allow_redirects=True)
        if head_response.status_code == 404:
            raise HTTPException(status_code=404, detail="Audio file not found")

        response = requests.get(audio_file_url, allow_redirects=True)
        response.raise_for_status()

        audio_suffix = detect_audio_format(audio_file_url, response.headers)
        audio_data = response.content

        func = transcriber.transcribe_segment.spawn(
            audio_data=audio_data,
            audio_suffix=audio_suffix,
            language=language,
        )
        result = func.get()

        if timestamp_offset:
            words = result.get("words", [])
            for w in words:
                if "start" in w:
                    w["start"] = round(float(w["start"]) + timestamp_offset, 2)
                if "end" in w:
                    w["end"] = round(float(w["end"]) + timestamp_offset, 2)
            result["words"] = words

        return result

    return app
