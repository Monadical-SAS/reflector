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

# Seamless M4T
SEAMLESSM4T_MODEL_SIZE: str = "medium"
SEAMLESSM4T_MODEL_CARD_NAME: str = f"seamlessM4T_{SEAMLESSM4T_MODEL_SIZE}"
SEAMLESSM4T_VOCODER_CARD_NAME: str = "vocoder_36langs"

HF_SEAMLESS_M4TEPO: str = f"facebook/seamless-m4t-{SEAMLESSM4T_MODEL_SIZE}"
HF_SEAMLESS_M4T_VOCODEREPO: str = "facebook/seamless-m4t-vocoder"

SEAMLESS_GITEPO: str = "https://github.com/facebookresearch/seamless_communication.git"
SEAMLESS_MODEL_DIR: str = "m4t"

WHISPER_MODEL_DIR = "/root/transcription_models"

stub = Stub(name="reflector-transcriber")


def install_seamless_communication():
    import os
    import subprocess
    initial_dir = os.getcwd()
    subprocess.run(["ssh-keyscan", "-t", "rsa", "github.com", ">>", "~/.ssh/known_hosts"])
    subprocess.run(["rm", "-rf", "seamless_communication"])
    subprocess.run(["git", "clone", SEAMLESS_GITEPO, "." + "/seamless_communication"])
    os.chdir("seamless_communication")
    subprocess.run(["pip", "install", "-e", "."])
    os.chdir(initial_dir)


def download_whisper():
    from faster_whisper.utils import download_model

    print("Downloading Whisper model")
    download_model(WHISPER_MODEL, cache_dir=WHISPER_MODEL_DIR)
    print("Whisper model downloaded")


def download_seamlessm4t_model():
    from huggingface_hub import snapshot_download

    print("Downloading Transcriber model & tokenizer")
    snapshot_download(HF_SEAMLESS_M4TEPO, cache_dir=SEAMLESS_MODEL_DIR)
    print("Transcriber model & tokenizer downloaded")

    print("Downloading vocoder weights")
    snapshot_download(HF_SEAMLESS_M4T_VOCODEREPO, cache_dir=SEAMLESS_MODEL_DIR)
    print("Vocoder weights downloaded")


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


def configure_seamless_m4t():
    import os

    import yaml

    ASSETS_DIR: str = "./seamless_communication/src/seamless_communication/assets/cards"

    with open(f'{ASSETS_DIR}/seamlessM4T_{SEAMLESSM4T_MODEL_SIZE}.yaml', 'r') as file:
        model_yaml_data = yaml.load(file, Loader=yaml.FullLoader)
    with open(f'{ASSETS_DIR}/vocoder_36langs.yaml', 'r') as file:
        vocoder_yaml_data = yaml.load(file, Loader=yaml.FullLoader)
    with open(f'{ASSETS_DIR}/unity_nllb-100.yaml', 'r') as file:
        unity_100_yaml_data = yaml.load(file, Loader=yaml.FullLoader)
    with open(f'{ASSETS_DIR}/unity_nllb-200.yaml', 'r') as file:
        unity_200_yaml_data = yaml.load(file, Loader=yaml.FullLoader)

    model_dir = f"{SEAMLESS_MODEL_DIR}/models--facebook--seamless-m4t-{SEAMLESSM4T_MODEL_SIZE}/snapshots"
    available_model_versions = os.listdir(model_dir)
    latest_model_version = sorted(available_model_versions)[-1]
    model_name = f"multitask_unity_{SEAMLESSM4T_MODEL_SIZE}.pt"
    model_path = os.path.join(os.getcwd(), model_dir, latest_model_version, model_name)

    vocoder_dir = f"{SEAMLESS_MODEL_DIR}/models--facebook--seamless-m4t-vocoder/snapshots"
    available_vocoder_versions = os.listdir(vocoder_dir)
    latest_vocoder_version = sorted(available_vocoder_versions)[-1]
    vocoder_name = "vocoder_36langs.pt"
    vocoder_path = os.path.join(os.getcwd(), vocoder_dir, latest_vocoder_version, vocoder_name)

    tokenizer_name = "tokenizer.model"
    tokenizer_path = os.path.join(os.getcwd(), model_dir, latest_model_version, tokenizer_name)

    model_yaml_data['checkpoint'] = f"file:/{model_path}"
    vocoder_yaml_data['checkpoint'] = f"file:/{vocoder_path}"
    unity_100_yaml_data['tokenizer'] = f"file:/{tokenizer_path}"
    unity_200_yaml_data['tokenizer'] = f"file:/{tokenizer_path}"

    with open(f'{ASSETS_DIR}/seamlessM4T_{SEAMLESSM4T_MODEL_SIZE}.yaml', 'w') as file:
        yaml.dump(model_yaml_data, file)
    with open(f'{ASSETS_DIR}/vocoder_36langs.yaml', 'w') as file:
        yaml.dump(vocoder_yaml_data, file)
    with open(f'{ASSETS_DIR}/unity_nllb-100.yaml', 'w') as file:
        yaml.dump(unity_100_yaml_data, file)
    with open(f'{ASSETS_DIR}/unity_nllb-200.yaml', 'w') as file:
        yaml.dump(unity_200_yaml_data, file)


transcriber_image = (
    Image.debian_slim(python_version="3.10.8")
    .apt_install("git")
    .apt_install("wget")
    .apt_install("libsndfile-dev")
    .pip_install(
        "faster-whisper",
        "requests",
        "torch",
        "transformers",
        "sentencepiece",
        "protobuf",
        "huggingface_hub==0.16.4",
        "gitpython",
        "torchaudio",
        "fairseq2",
        "pyyaml",
        "hf-transfer~=0.1"
    )
    .run_function(install_seamless_communication)
    .run_function(download_seamlessm4t_model)
    .run_function(configure_seamless_m4t)
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


@stub.cls(
    gpu="A10G",
    timeout=60 * 5,
    container_idle_timeout=60,
    image=transcriber_image,
)
class Transcriber:
    def __enter__(self):
        import faster_whisper
        import torch
        from seamless_communication.models.inference.translator import Translator

        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        self.model = faster_whisper.WhisperModel(
            WHISPER_MODEL,
            device=self.device,
            compute_type=WHISPER_COMPUTE_TYPE,
            num_workers=WHISPER_NUM_WORKERS,
            download_root=WHISPER_MODEL_DIR
        )
        self.translator = Translator(
            SEAMLESSM4T_MODEL_CARD_NAME,
            SEAMLESSM4T_VOCODER_CARD_NAME,
            torch.device(self.device),
            dtype=torch.float32
        )

    @method()
    def warmup(self):
        return {"status": "ok"}

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

    def get_seamless_lang_code(self, lang_code: str):
        """
        The codes for SeamlessM4T is different from regular standards.
        For ex, French is "fra" and not "fr".
        """
        # TODO: Enhance with complete list of lang codes
        seamless_lang_code = {
            "en": "eng",
            "fr": "fra"
        }
        return seamless_lang_code.get(lang_code, "eng")

    @method()
    def translate_text(
            self,
            text: str,
            source_language: str,
            target_language: str
    ):
        translated_text, _, _ = self.translator.predict(
            text,
            "t2tt",
            src_lang=self.get_seamless_lang_code(source_language),
            tgt_lang=self.get_seamless_lang_code(target_language),
            ngram_filtering=True
        )
        return {
            "text": {
                source_language: text,
                target_language: str(translated_text)
            }
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
    async def transcribe(
        file: UploadFile,
        source_language: Annotated[str, Body(...)] = "en",
        timestamp: Annotated[float, Body()] = 0.0
    ) -> TranscriptResponse:
        audio_data = await file.read()
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

    @app.post("/translate", dependencies=[Depends(apikey_auth)])
    async def translate(
            text: str,
            source_language: Annotated[str, Body(...)] = "en",
            target_language: Annotated[str, Body(...)] = "fr",
    ) -> TranscriptResponse:
        func = transcriberstub.translate_text.spawn(
            text=text,
            source_language=source_language,
            target_language=target_language,
        )
        result = func.get()
        return result

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        return transcriberstub.warmup.spawn().get()

    return app
