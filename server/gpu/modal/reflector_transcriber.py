"""
Reflector GPU backend - transcriber
===================================
"""

import os
import tempfile

from modal import Image, Secret, Stub, asgi_app, method
from pydantic import BaseModel

# Whisper
WHISPER_MODEL: str = "tiny"
WHISPER_COMPUTE_TYPE: str = "float16"
WHISPER_NUM_WORKERS: int = 1
WHISPER_CACHE_DIR: str = "/cache/whisper"

# Translation Model
TRANSLATION_MODEL = "facebook/m2m100_418M"

stub = Stub(name="reflector-translator")


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
        "transformers",
        "sentencepiece",
        "protobuf",
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
        import faster_whisper
        import torch
        from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.model = faster_whisper.WhisperModel(
            WHISPER_MODEL,
            device=self.device,
            compute_type=WHISPER_COMPUTE_TYPE,
            num_workers=WHISPER_NUM_WORKERS,
        )
        self.translation_model = M2M100ForConditionalGeneration.from_pretrained(TRANSLATION_MODEL).to(self.device)
        self.translation_tokenizer = M2M100Tokenizer.from_pretrained(TRANSLATION_MODEL)


    @method()
    def warmup(self):
        return {"status": "ok"}

    @method()
    def transcribe_segment(
        self,
        audio_data: str,
        audio_suffix: str,
        timestamp: float = 0,
        source_language: str = "en",
        target_language: str = "fr"
    ):
        with tempfile.NamedTemporaryFile("wb+", suffix=f".{audio_suffix}") as fp:
            fp.write(audio_data)

            segments, _ = self.model.transcribe(
                fp.name,
                language=source_language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )

            multilingual_transcript = {}
            transcript_en = ""
            words = []
            if segments:
                segments = list(segments)

                for segment in segments:
                    transcript_en += segment.text
                    for word in segment.words:
                        words.append(
                            {
                                "text": word.word,
                                "start": round(timestamp + word.start, 3),
                                "end": round(timestamp + word.end, 3),
                            }
                        )

            multilingual_transcript["en"] = transcript_en

            if target_language != "en":
                self.translation_tokenizer.src_lang = source_language
                forced_bos_token_id = self.translation_tokenizer.get_lang_id(target_language)
                encoded_transcript = self.translation_tokenizer(transcript_en, return_tensors="pt").to(self.device)
                generated_tokens = self.translation_model.generate(
                        **encoded_transcript,
                        forced_bos_token_id=forced_bos_token_id
                )
                result = self.translation_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
                multilingual_transcript[target_language] = result[0].strip()

            return {
                "text": multilingual_transcript,
                "words": words
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
    from fastapi import Depends, FastAPI, Form, HTTPException, UploadFile, status
    from fastapi.security import OAuth2PasswordBearer
    from typing_extensions import Annotated

    transcriberstub = Whisper()

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

    class TranscriptionRequest(BaseModel):
        file: UploadFile
        timestamp: Annotated[float, Form()] = 0
        source_language: Annotated[str, Form()] = "en"
        target_language: Annotated[str, Form()] = "en"

    class TranscriptResponse(BaseModel):
        result: dict

    @app.post("/transcribe", dependencies=[Depends(apikey_auth)])
    async def transcribe(
            req
    ):
        print(req)
        audio_data = await req.file.read()
        audio_suffix = req.file.filename.split(".")[-1]
        assert audio_suffix in supported_audio_file_types

        func = transcriberstub.transcribe_segment.spawn(
            audio_data=audio_data,
            audio_suffix=audio_suffix,
            source_language="en",
            timestamp=req.timestamp
        )
        result = func.get()
        return result

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        return transcriberstub.warmup.spawn().get()

    return app
