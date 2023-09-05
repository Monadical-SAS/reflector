"""
Reflector GPU backend - transcriber
===================================
"""

import os
import tempfile

from modal import Image, Secret, Stub, asgi_app, method
from pydantic import BaseModel

# Whisper
WHISPER_MODEL: str = "large-v2"
WHISPER_COMPUTE_TYPE: str = "float16"
WHISPER_NUM_WORKERS: int = 1

MODEL_DIR = "/model"

# Translation Model
TRANSLATION_MODEL = "facebook/m2m100_418M"
TRANSLATION_MODEL_DIR = "translation"

stub = Stub(name="reflector-transtest")


def download_whisper():
    from faster_whisper.utils import download_model

    print("Downloading Whisper model")
    download_model(WHISPER_MODEL, cache_dir=MODEL_DIR)
    print("Whisper model downloaded")


def download_translation_model():
    from huggingface_hub import snapshot_download

    print("Downloading Translation model")
    ignore_patterns = ["*.ot"]
    snapshot_download(TRANSLATION_MODEL, local_dir=MODEL_DIR, ignore_patterns=ignore_patterns)
    print("Translation model downloaded")


def migrate_cache_llm():
    """
    XXX The cache for model files in Transformers v4.22.0 has been updated.
    Migrating your old cache. This is a one-time only operation. You can
    interrupt this and resume the migration later on by calling
    `transformers.utils.move_cache()`.
    """
    from transformers.utils.hub import move_cache

    print("Moving LLM cache")
    move_cache()
    print("LLM cache moved")


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
        "huggingface_hub==0.16.4",
    )
    .run_function(download_models)
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
        self.translation_model = M2M100ForConditionalGeneration.from_pretrained(
                TRANSLATION_MODEL_DIR
        ).to(self.device)
        self.translation_tokenizer = M2M100Tokenizer.from_pretrained(TRANSLATION_MODEL)


    @method()
    def warmup(self):
        return {"status": "ok"}

    @method()
    def transcribe_segment(
        self,
        audio_data: str,
        audio_suffix: str,
        source_language: str,
        target_language: str,
        timestamp: float = 0
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

            if target_language != source_language:
                self.translation_tokenizer.src_lang = source_language
                forced_bos_token_id = self.translation_tokenizer.get_lang_id(target_language)
                encoded_transcript = self.translation_tokenizer(transcript_source_lang, return_tensors="pt").to(self.device)
                generated_tokens = self.translation_model.generate(
                        **encoded_transcript,
                        forced_bos_token_id=forced_bos_token_id
                )
                result = self.translation_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
                translation = result[0].strip()
                multilingual_transcript[target_language] = translation


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
    from fastapi import Body, Depends, FastAPI, HTTPException, UploadFile, status
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

    class TranscriptResponse(BaseModel):
        result: dict

    @app.post("/transcribe", dependencies=[Depends(apikey_auth)])
    async def transcribe(
        file: UploadFile,
        source_language: Annotated[str, Body(...)] = "en",
        target_language: Annotated[str, Body(...)] = "en",
        timestamp: Annotated[float, Body()] = 0.0
    ) -> TranscriptResponse:
        audio_data = await file.read()
        audio_suffix = file.filename.split(".")[-1]
        assert audio_suffix in supported_audio_file_types

        func = transcriberstub.transcribe_segment.spawn(
            audio_data=audio_data,
            audio_suffix=audio_suffix,
            source_language=source_language,
            target_language=target_language,
            timestamp=timestamp
        )
        result = func.get()
        return result

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        return transcriberstub.warmup.spawn().get()

    return app
