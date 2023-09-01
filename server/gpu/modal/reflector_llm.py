"""
Reflector GPU backend - LLM
===========================

"""
import json
import os
from typing import Optional

from modal import Image, Secret, Stub, asgi_app, method

# LLM
LLM_MODEL: str = "lmsys/vicuna-13b-v1.5"
LLM_LOW_CPU_MEM_USAGE: bool = True
LLM_TORCH_DTYPE: str = "bfloat16"
LLM_MAX_NEW_TOKENS: int = 300

IMAGE_MODEL_DIR = "/model"

stub = Stub(name="reflector-test")


def download_llm():
    from huggingface_hub import snapshot_download

    print("Downloading LLM model")
    snapshot_download(LLM_MODEL, local_dir=IMAGE_MODEL_DIR)
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
    move_cache()
    print("LLM cache moved")


llm_image = (
    Image.debian_slim(python_version="3.10.8")
    .apt_install("git")
    .pip_install(
        "transformers",
        "torch",
        "sentencepiece",
        "protobuf",
        "jsonformer==0.12.0",
        "accelerate==0.21.0",
        "einops==0.6.1",
        "hf-transfer~=0.1",
        "huggingface_hub==0.16.4"
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(download_llm)
    .run_function(migrate_cache_llm)
)


@stub.cls(
    gpu="A100",
    timeout=60 * 5,
    container_idle_timeout=60 * 5,
    concurrency_limit=2,
    image=llm_image,
)
class LLM:
    def __enter__(self):
        import jsonformer
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from transformers.generation import GenerationConfig

        print("Instance llm model")
        model = AutoModelForCausalLM.from_pretrained(
            IMAGE_MODEL_DIR,
            torch_dtype=getattr(torch, LLM_TORCH_DTYPE),
            low_cpu_mem_usage=LLM_LOW_CPU_MEM_USAGE,
        )

        # generation configuration
        print("Instance llm generation config")
        # JSONFormer doesn't yet support generation configs, but keeping for future usage
        model.config.max_new_tokens = LLM_MAX_NEW_TOKENS
        gen_cfg = GenerationConfig.from_model_config(model.config)
        gen_cfg.max_new_tokens = LLM_MAX_NEW_TOKENS

        # load tokenizer
        print("Instance llm tokenizer")
        tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)

        # move model to gpu
        print("Move llm model to GPU")
        model = model.cuda()

        print("Warmup llm done")
        self.model = model
        self.tokenizer = tokenizer
        self.gen_cfg = gen_cfg
        self.json_former = jsonformer.Jsonformer

    def __exit__(self, *args):
        print("Exit llm")

    @method()
    def warmup(self):
        print("Warmup ok")
        return {"status": "ok"}

    @method()
    def generate(self, prompt: str, gen_schema: str | None, gen_cfg: str | None) -> dict:
        """
        Perform a generation action using the LLM
        """
        print(f"Generate {prompt=}")
        if gen_cfg:
            # Update the base gen cfg with the supplied gen cfg
            self.gen_cfg.update(**json.loads(gen_cfg))

        # If a gen_schema is given, conform to gen_schema
        if gen_schema:
            print(f"Schema {gen_schema=}")
            jsonformer_llm = self.json_former(model=self.model,
                                              tokenizer=self.tokenizer,
                                              json_schema=json.loads(gen_schema),
                                              prompt=prompt,
                                              max_string_token_length=self.gen_cfg.max_new_tokens)
            response = jsonformer_llm()
        else:
            # If no gen_schema, perform prompt only generation

            # tokenize prompt
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(
                self.model.device
            )
            output = self.model.generate(input_ids, generation_config=self.gen_cfg)

            # decode output
            response = self.tokenizer.decode(output[0].cpu(), skip_special_tokens=True)
            response = response[len(prompt):]
        print(f"Generated {response=}")
        return {"text": response}

# -------------------------------------------------------------------
# Web API
# -------------------------------------------------------------------


@stub.function(
    container_idle_timeout=60 * 10,
    timeout=60 * 5,
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
    async def llm(
        req: LLMRequest,
    ):
        gen_schema = json.dumps(req.gen_schema) if req.gen_schema else None
        gen_cfg = json.dumps(req.gen_cfg) if req.gen_cfg else None
        func = llmstub.generate.spawn(prompt=req.prompt, gen_schema=gen_schema, gen_cfg=gen_cfg)
        result = func.get()
        return result

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        return llmstub.warmup.spawn().get()

    return app
