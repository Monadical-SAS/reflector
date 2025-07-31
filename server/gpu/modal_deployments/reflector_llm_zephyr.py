"""
Reflector GPU backend - LLM
===========================

"""

import json
import os
import threading
from typing import Optional

import modal
from modal import App, Image, Secret, asgi_app, enter, exit, method

# LLM
LLM_MODEL: str = "HuggingFaceH4/zephyr-7b-alpha"
LLM_LOW_CPU_MEM_USAGE: bool = True
LLM_TORCH_DTYPE: str = "bfloat16"
LLM_MAX_NEW_TOKENS: int = 300

IMAGE_MODEL_DIR = "/root/llm_models/zephyr"

app = App(name="reflector-llm-zephyr")


def download_llm():
    from huggingface_hub import snapshot_download

    print("Downloading LLM model")
    snapshot_download(LLM_MODEL, cache_dir=IMAGE_MODEL_DIR)
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
    move_cache(cache_dir=IMAGE_MODEL_DIR, new_cache_dir=IMAGE_MODEL_DIR)
    print("LLM cache moved")


llm_image = (
    Image.debian_slim(python_version="3.10.8")
    .apt_install("git")
    .pip_install(
        "transformers==4.34.0",
        "torch",
        "sentencepiece",
        "protobuf",
        "jsonformer==0.12.0",
        "accelerate==0.21.0",
        "einops==0.6.1",
        "hf-transfer~=0.1",
        "huggingface_hub==0.16.4",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(download_llm)
    .run_function(migrate_cache_llm)
)


@app.cls(
    gpu="A10G",
    timeout=60 * 5,
    scaledown_window=60 * 5,
    allow_concurrent_inputs=10,
    image=llm_image,
)
class LLM:
    @enter()
    def enter(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

        print("Instance llm model")
        model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL,
            torch_dtype=getattr(torch, LLM_TORCH_DTYPE),
            low_cpu_mem_usage=LLM_LOW_CPU_MEM_USAGE,
            cache_dir=IMAGE_MODEL_DIR,
            local_files_only=True,
        )

        # JSONFormer doesn't yet support generation configs
        print("Instance llm generation config")
        model.config.max_new_tokens = LLM_MAX_NEW_TOKENS

        # generation configuration
        gen_cfg = GenerationConfig.from_model_config(model.config)
        gen_cfg.max_new_tokens = LLM_MAX_NEW_TOKENS

        # load tokenizer
        print("Instance llm tokenizer")
        tokenizer = AutoTokenizer.from_pretrained(
            LLM_MODEL, cache_dir=IMAGE_MODEL_DIR, local_files_only=True
        )
        gen_cfg.pad_token_id = tokenizer.eos_token_id
        gen_cfg.eos_token_id = tokenizer.eos_token_id
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = tokenizer.eos_token_id

        # move model to gpu
        print("Move llm model to GPU")
        model = model.cuda()

        print("Warmup llm done")
        self.model = model
        self.tokenizer = tokenizer
        self.gen_cfg = gen_cfg
        self.GenerationConfig = GenerationConfig
        self.lock = threading.Lock()

    @exit()
    def exit():
        print("Exit llm")

    @method()
    def generate(
        self, prompt: str, gen_schema: str | None, gen_cfg: str | None
    ) -> dict:
        """
        Perform a generation action using the LLM
        """
        print(f"Generate {prompt=}")
        if gen_cfg:
            gen_cfg = self.GenerationConfig.from_dict(json.loads(gen_cfg))
            gen_cfg.pad_token_id = self.tokenizer.eos_token_id
            gen_cfg.eos_token_id = self.tokenizer.eos_token_id
        else:
            gen_cfg = self.gen_cfg

        # If a gen_schema is given, conform to gen_schema
        with self.lock:
            if gen_schema:
                import jsonformer

                print(f"Schema {gen_schema=}")
                jsonformer_llm = jsonformer.Jsonformer(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    json_schema=json.loads(gen_schema),
                    prompt=prompt,
                    max_string_token_length=gen_cfg.max_new_tokens,
                )
                response = jsonformer_llm()
            else:
                # If no gen_schema, perform prompt only generation

                # tokenize prompt
                input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(
                    self.model.device
                )
                output = self.model.generate(input_ids, generation_config=gen_cfg)

                # decode output
                response = self.tokenizer.decode(
                    output[0].cpu(), skip_special_tokens=True
                )
                response = response[len(prompt) :]
                response = {"long_summary": response}
        print(f"Generated {response=}")
        return {"text": response}


# -------------------------------------------------------------------
# Web API
# -------------------------------------------------------------------


@app.function(
    scaledown_window=60 * 10,
    timeout=60 * 5,
    allow_concurrent_inputs=30,
    secrets=[
        Secret.from_name("reflector-gpu"),
    ],
)
@asgi_app()
def web():
    from fastapi import Depends, FastAPI, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from pydantic import BaseModel

    llmstub = LLM()

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
        prompt: str
        gen_schema: Optional[dict] = None
        gen_cfg: Optional[dict] = None

    @app.post("/llm", dependencies=[Depends(apikey_auth)])
    def llm(
        req: LLMRequest,
    ):
        gen_schema = json.dumps(req.gen_schema) if req.gen_schema else None
        gen_cfg = json.dumps(req.gen_cfg) if req.gen_cfg else None
        func = llmstub.generate.spawn(
            prompt=req.prompt, gen_schema=gen_schema, gen_cfg=gen_cfg
        )
        result = func.get()
        return result

    return app
