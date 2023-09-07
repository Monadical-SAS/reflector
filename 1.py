# LLM
LLM_MODEL: str = "prajjwal1/bert-tiny"
LLM_LOW_CPU_MEM_USAGE: bool = True
LLM_TORCH_DTYPE: str = "bfloat16"
LLM_MAX_NEW_TOKENS: int = 300

IMAGE_MODEL_DIR = "gokul"


def download_llm():
    from huggingface_hub import snapshot_download
    from faster_whisper.utils import download_model

    print("Downloading LLM model")
    ignore_patterns = ["*.ot"]
    snapshot_download("facebook/m2m100_418M", cache_dir=None, ignore_patterns=ignore_patterns)
    download_model("openai/whisper-tiny", cache_dir=None)
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
    move_cache(new_cache_dir="/gokul")
    print("LLM cache moved")

download_llm()
migrate_cache_llm()

import torch
from transformers import AutoModel, AutoTokenizer
from transformers.generation import GenerationConfig

print("Instance llm model")
model = AutoModel.from_pretrained(
    "facebook/m2m100_418M"
)
print(model.config)

print("Instance llm model")
model = AutoModel.from_pretrained(
    "openai/whisper-tiny"
)
print(model.config)