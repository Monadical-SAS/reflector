"""
Reflector GPU backend - LLM
===========================

"""
import json
import os
from typing import Callable, List, Optional

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
        "huggingface_hub==0.16.4",
        "nltk"
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
        import nltk
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

        print("Downloading NLTK model")
        nltk.download('punkt')

        # move model to gpu
        print("Move llm model to GPU")
        model = model.cuda()

        print("Warmup llm done")
        self.model = model
        self.tokenizer = tokenizer
        self.sentence_tokenizer = nltk.sent_tokenize
        self.json_former = jsonformer.Jsonformer
        self.summary_gen_cfg = GenerationConfig(
                max_new_tokens=1300,
                num_beams=3,
                use_cache=True,
                temperature=0.3
        )
        self.title_gen_cfg = GenerationConfig(
                max_new_tokens=200,
                num_beams=5,
                use_cache=True,
                temperature=0.5
        )
        self.topic_gen_cfg = GenerationConfig(
                max_new_tokens=300,
                num_beams=3,
                use_cache=True,
                temperature=0.9
        )

        self.PROMPT_TEMPLATE = """
            ### Human:
            {user_prompt}

            {text}

            ### Assistant:
            """

        self.final_title_prompt = "Combine the following individual titles into one single " \
                                  "title that condenses the essence of all titles."

    def __exit__(self, *args):
        print("Exit llm")

    @method()
    def warmup(self):
        print("Warmup ok")
        return {"status": "ok"}

    @property
    def supported_tasks(self) -> List[str]:
        return ["title", "summary", "topic"]

    @property
    def generate_registry(self) -> None:
        if not self._generate_registry:
            self._init_generate_registry()
        return self._generate_registry

    def _init_generate_registry(self) -> None:
        for task in self.supported_tasks:
            func_name = "_generate_" + task
            func = getattr(self, func_name, None)
            if not func:
                raise NotImplementedError(f"Generation function for '{task}' is not implemented, but the task is "
                                          f"marked as supported. Either remove task from the supported tasks list or"
                                          f"add support by implementing its generation function i.e {func_name}")
            self._generate_registry[task] = func

    def _generation_swivel(self, task: str) -> Callable:
        if task not in self.supported_tasks:
            raise NotImplementedError(f"Task: '{task}' is not supported, but requested by client.")
        return self.generate_registry[task]

    def split_corpus(self, corpus: str, token_threshold: int = 1000) -> List[str]:
        accumulated_tokens = []
        accumulated_sentences = []
        accumulated_token_count = 0
        corpus_sentences = self.sentence_tokenizer(corpus)

        for sentence in corpus_sentences:
            tokens = self.tokenizer.tokenize(sentence)
            if accumulated_token_count + len(tokens) <= token_threshold:
                accumulated_token_count += len(tokens)
                accumulated_tokens.extend(tokens)
                accumulated_sentences.append(sentence)
            else:
                yield "".join(accumulated_sentences)
                accumulated_token_count = len(tokens)
                accumulated_tokens = tokens
                accumulated_sentences = [sentence]

        if accumulated_tokens:
            yield " ".join(accumulated_sentences)

    def create_prompt(self, user_prompt: str, text: str) -> str:
        return self.PROMPT_TEMPLATE.format(user_prompt=user_prompt, text=text)

    @method()
    def _generate_title(self, user_prompt: str, text: str, schema: str = None) -> str | dict:
        chunk_titles = []
        for chunk in self.split_corpus(text, token_threshold=1000):
            prompt = self.create_prompt(user_prompt=user_prompt, text=chunk)
            title = self._generate(prompt=prompt, schema=schema, gen_cfg=self.title_gen_cfg)
            title = title["result"]["title"] if schema else title["result"]
            chunk_titles.append(title)

        collected_titles = ". ".join(chunk_titles)
        prompt = self.create_prompt(user_prompt=self.final_title_prompt, text=collected_titles)
        return self._generate(prompt=prompt, schema=schema, gen_cfg=self.title_gen_cfg)

    @method()
    def _generate_topic(self, user_prompt: str, text: str, schema: str = None) -> str | dict:
        prompt = self.create_prompt(user_prompt=user_prompt, text=text)
        return self._generate(prompt=prompt, schema=schema, gen_cfg=self.topic_gen_cfg)

    @method()
    def _generate_summary(self, user_prompt: str, text: str, schema: str = None) -> str | dict:
        chunk_summary = []
        for chunk in self.split_corpus(text):
            prompt = self.create_prompt(user_prompt=user_prompt, text=chunk)
            summary = self._generate(prompt=prompt, schema=schema, gen_cfg=self.summary_gen_cfg)
            summary = summary["result"]["summary"] if schema else summary["result"]
            chunk_summary.append(summary)

        collected_summaries = " ".join(chunk_summary)
        return collected_summaries

    def _generate(self, prompt: str, gen_cfg, schema: str = None) -> str | dict:
        print(f"Generate {prompt=}")
        # If a schema is given, conform to schema
        if schema:
            print(f"Schema {schema=}")
            jsonformer_llm = self.json_former(model=self.model,
                                              tokenizer=self.tokenizer,
                                              json_schema=json.loads(schema),
                                              prompt=prompt,
                                              max_string_token_length=self.topic_gen_cfg.max_new_tokens)
            response = jsonformer_llm()
        else:
            # If no schema, perform prompt only generation

            # tokenize prompt
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(
                    self.model.device
            )
            output = self.model.generate(input_ids, generation_config=gen_cfg)

            # decode output
            response = self.tokenizer.decode(output[0].cpu(), skip_special_tokens=True)
            response = response[len(prompt):]
        print(f"Generated {response=}")
        return {"result": response}

    @method()
    def generate(self, user_prompt: str, task: str, text: str, schema: dict | None) -> str | dict:
        try:
            return self._generation_swivel(task)(user_prompt=user_prompt, text=text, schema=schema)
        except NotImplementedError as e:
            return f"Unsupported LLM task requested: {str(e)}"

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
    from pydantic import BaseModel, Field

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
        text: str
        task: str
        schema_: Optional[dict] = Field(None, alias="schema")

    @app.post("/llm", dependencies=[Depends(apikey_auth)])
    async def llm(
            req: LLMRequest,
    ):
        return llmstub.generate(user_prompt=req.prompt, text=req.text, task=req.task, schema=req.schema_)

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        return llmstub.warmup.spawn().get()

    return app
