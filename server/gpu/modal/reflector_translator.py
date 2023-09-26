"""
Reflector GPU backend - transcriber
===================================
"""

import os

from modal import Image, Secret, Stub, asgi_app, method
from pydantic import BaseModel

SEAMLESSM4T_MODEL_SIZE: str = "large"
SEAMLESSM4T_MODEL_CARD_NAME: str = f"seamlessM4T_{SEAMLESSM4T_MODEL_SIZE}"
SEAMLESSM4T_VOCODER_CARD_NAME: str = "vocoder_36langs"

HF_SEAMLESS_M4T_REPO: str = f"facebook/seamless-m4t-{SEAMLESSM4T_MODEL_SIZE}"
HF_SEAMLESS_M4T_VOCODER_REPO: str = "facebook/seamless-m4t-vocoder"

SEAMLESS_GIT_REPO: str = "https://github.com/facebookresearch/seamless_communication.git"

MODEL_DIR: str = "m4t"
stub = Stub(name="reflector-translator")

# Whisper
WHISPER_MODEL: str = "large-v2"
WHISPER_COMPUTE_TYPE: str = "float16"
WHISPER_NUM_WORKERS: int = 1

# LLM
LLM_MODEL: str = "lmsys/vicuna-13b-v1.5"
LLM_LOW_CPU_MEM_USAGE: bool = True
LLM_TORCH_DTYPE: str = "bfloat16"
LLM_MAX_NEW_TOKENS: int = 300

LLM_IMAGE_MODEL_DIR = "/root/llm_models"

# Translation Model
TRANSLATION_MODEL = "facebook/m2m100_1.2B"

IMAGE_MODEL_DIR = "/root/translation_models"


def download_llm():
    from huggingface_hub import snapshot_download

    print("Downloading LLM model")
    snapshot_download(LLM_MODEL, cache_dir=LLM_IMAGE_MODEL_DIR)
    print("LLM model downloaded")


def migrate_cache_llm():
    """
    XXX The cache for model files in Transformers v4.22.0 has been updated.
    Migrating your old cache. This is a one-time only operation. You can
    interrupt this and resume the migration later on by calling
    `transformers.utils.move_cache()`.
    """
    from transformers.utils.hub import move_cache

    print("Moving LLM cache")
    move_cache(cache_dir=LLM_IMAGE_MODEL_DIR, new_cache_dir=LLM_IMAGE_MODEL_DIR)
    print("LLM cache moved")

def setup_seamless_communication():
    import os
    import subprocess
    initial_dir = os.getcwd()
    subprocess.run(["ssh-keyscan", "-t", "rsa", "github.com", ">>", "~/.ssh/known_hosts"])
    subprocess.run(["rm", "-rf", "seamless_communication"])
    subprocess.run(["git", "clone", SEAMLESS_GIT_REPO, "." + "/seamless_communication"])
    os.chdir("seamless_communication")
    subprocess.run(["pip", "install", "-e", "."])
    os.chdir(initial_dir)


def download_seamlessm4t():
    from huggingface_hub import snapshot_download

    print("Downloading Transcriber model & tokenizer")
    snapshot_download(HF_SEAMLESS_M4T_REPO, cache_dir=MODEL_DIR)
    print("Transcriber model & tokenizer downloaded")

    print("Downloading vocoder weights")
    snapshot_download(HF_SEAMLESS_M4T_VOCODER_REPO, cache_dir=MODEL_DIR)
    print("Vocoder weights downloaded")


def setup_seamless_m4t():
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

    model_dir = f"{MODEL_DIR}/models--facebook--seamless-m4t-{SEAMLESSM4T_MODEL_SIZE}/snapshots"
    available_model_versions = os.listdir(model_dir)
    latest_model_version = sorted(available_model_versions)[-1]
    model_name = f"multitask_unity_{SEAMLESSM4T_MODEL_SIZE}.pt"
    model_path = os.path.join(os.getcwd(), model_dir, latest_model_version, model_name)

    vocoder_dir = f"{MODEL_DIR}/models--facebook--seamless-m4t-vocoder/snapshots"
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


def download_translation_model():
    from huggingface_hub import snapshot_download

    print("Downloading Translation model")
    ignore_patterns = ["*.ot"]
    snapshot_download(
        TRANSLATION_MODEL,
        cache_dir=IMAGE_MODEL_DIR,
        ignore_patterns=ignore_patterns
    )
    print("Translation model downloaded")


image = (
    Image.debian_slim(python_version="3.10.8")
    .apt_install("git")
    .apt_install("wget")
    .apt_install("libsndfile-dev")
    .pip_install(
        "gitpython",
        "torch",
        "torchaudio",
        "fairseq2",
        "pyyaml",
        "hf-transfer~=0.1",
        "huggingface_hub==0.16.4",
        "faster-whisper",
        "requests",
        "transformers",
        "sentencepiece",
        "protobuf",
    )
    .run_function(setup_seamless_communication)
    .run_function(download_seamlessm4t)
    .run_function(setup_seamless_m4t)
    .run_function(download_llm)
    .run_function(migrate_cache_llm)
    .run_function(download_translation_model)
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
    container_idle_timeout=60 * 5,
    concurrency_limit=2,
    image=image,
)
class Translator:
    def __enter__(self):
        import torch
        from seamless_communication.models.inference.translator import Translator
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            M2M100ForConditionalGeneration,
            M2M100Tokenizer,
        )
        self.use_gpu = torch.cuda.is_available()
        self.device = "cuda" if self.use_gpu else "cpu"
        # self.seamless_translator = Translator(
        #     SEAMLESSM4T_MODEL_CARD_NAME,
        #     SEAMLESSM4T_VOCODER_CARD_NAME,
        #     torch.device(self.device),
        #     dtype=torch.float32
        # )
        self.m2m_translator = M2M100ForConditionalGeneration.from_pretrained(
            TRANSLATION_MODEL,
            cache_dir=IMAGE_MODEL_DIR
        ).to(self.device)
        self.m2m_tokenizer = M2M100Tokenizer.from_pretrained(
            TRANSLATION_MODEL,
            cache_dir=IMAGE_MODEL_DIR
        )
        # self.llm_translator = AutoModelForCausalLM.from_pretrained(
        #     LLM_MODEL,
        #     torch_dtype=getattr(torch, LLM_TORCH_DTYPE),
        #     low_cpu_mem_usage=False,
        #     cache_dir=LLM_IMAGE_MODEL_DIR
        # )
        # self.llm_tokenizer = AutoTokenizer.from_pretrained(
        #     LLM_MODEL,
        #     cache_dir=LLM_IMAGE_MODEL_DIR
        # )

    @method()
    def warmup(self):
        return {"status": "ok"}

    @method()
    def translate(
            self,
            text: str,
            case: str,
            source_language: str,
            target_language: str
    ):
        multilingual_transcript = {source_language: text}
        if case == "seamless":
            print(text, case)
            translated_text, _, _ = self.seamless_translator.predict(text, "t2tt",
                                                            src_lang="eng",
                                                            tgt_lang="fra",
                                                            ngram_filtering=True)
            multilingual_transcript[target_language] = str(translated_text)
        elif case == "m2m":
            self.m2m_tokenizer.src_lang = source_language
            forced_bos_token_id = self.m2m_tokenizer.get_lang_id(target_language)
            encoded_transcript = self.m2m_tokenizer(text, return_tensors="pt").to(self.device)
            generated_tokens = self.m2m_translator.generate(
                **encoded_transcript,
                forced_bos_token_id=forced_bos_token_id
            )
            result = self.m2m_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
            translation = result[0].strip()
            multilingual_transcript[target_language] = translation
        elif case == "llm":
            prompt = f"""
                    ### HUMAN:translate the following text to French

                    {text}
                    ### Assistant:
                    """
            input_ids = self.llm_tokenizer.encode(prompt, return_tensors="pt").to(
                self.llm_translator.device
            )
            output = self.llm_translator.generate(input_ids)

            # decode output
            response = self.llm_tokenizer.decode(output[0].cpu(), skip_special_tokens=True)
            translation = response[len(prompt):]
            multilingual_transcript[target_language] = translation
        return {"text": multilingual_transcript}

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
    from fastapi import Depends, FastAPI, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer

    translatorstub = Translator()

    app = FastAPI()

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    def apikey_auth(apikey: str = Depends(oauth2_scheme)):
        if apikey != os.environ["REFLECTOR_GPU_APIKEY"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    class LLMRequest(BaseModel):
        text: str
        case: str

    @app.post("/translate", dependencies=[Depends(apikey_auth)])
    async def translate(
        req: LLMRequest
    ):
        func = translatorstub.translate.spawn(
            text=req.text,
            case=req.case,
            source_language="en",
            target_language="fr",
        )
        result = func.get()
        return result

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        # return translatorstub.warmup.spawn().get()
        return "SUCCESS"
    return app
