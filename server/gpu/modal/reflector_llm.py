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

        # Load NLTK
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

        # Generation configurations
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

        # LLM specific prompt template
        self.PROMPT_TEMPLATE = """
            ### Human:
            {user_prompt}

            {text}

            ### Assistant:
            """

        # Currently supported LLM generation operations. To add new task, add it to list
        # and create a new generation function i.e) _generate_<task> and the registry will
        # automatically pick this up.
        self.supported_tasks = ["title", "summary", "topic"]
        self.task_registry = {}

    def __exit__(self, *args):
        print("Exit llm")

    @method()
    def warmup(self):
        print("Warmup ok")
        return {"status": "ok"}

    def _registered_generator(self, task: str) -> Callable:
        """
        Populate a registry for generation tasks in the format: task -> generation function.
        Return the generation function for a given task
        """
        # If already registered
        if task in self.task_registry:
            return self.task_registry[task]

        # If not, try to register
        func_name = "_generate_" + str(task)
        func = getattr(self, func_name, None)
        if not func:
            raise NotImplementedError(f"Generation function for '{task}' is not implemented, but the task is "
                                      f"marked as supported. Either remove task from the supported tasks list or"
                                      f"add support by implementing its generation function i.e {func_name}")

        # Update registry
        self.task_registry[task] = func
        return self.task_registry[task]

    def _generation_swivel(self, user_prompt: str, text: str, task: str, schema: str | None) -> Callable:
        """
        Based on the requested task, call the corresponding generation function.
        """
        if task not in self.supported_tasks:
            raise NotImplementedError(f"The requested task: {task} is not supported.")
        return (self._registered_generator(task))(user_prompt=user_prompt, text=text, schema=schema)

    def _split_corpus(self, corpus: str, token_threshold: int = 800) -> List[str]:
        """
        Split the input to the LLM due to CUDA memory limitations and LLM context window
        restrictions.

        Accumulate tokens from full sentences till threshold and yield accumulated tokens.
        Reset accumulation and repeat process.
        """
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

    def _create_prompt(self, user_prompt: str, text: str) -> str:
        """
        Create a consumable prompt based on the prompt template
        """
        return self.PROMPT_TEMPLATE.format(user_prompt=user_prompt, text=text)

    def _generate_title(self, user_prompt: str, text: str, schema: str | None) -> str | dict:
        """
        Generate final title
        """
        titles = []
        for chunk in self._split_corpus(text):
            prompt = self._create_prompt(user_prompt=user_prompt, text=chunk)
            title = self._generate(prompt=prompt, schema=schema, gen_cfg=self.title_gen_cfg)
            titles.append(title)

        if len(titles) > 1:
            if schema:
                collected_titles = ".".join([title["title"] for title in titles])
            else:
                collected_titles = ".".join(titles)
            prompt = self._create_prompt(user_prompt=user_prompt, text=collected_titles)
            result = self._generate(prompt=prompt, schema=schema, gen_cfg=self.title_gen_cfg)
        else:
            result = titles[0]
        print(f"Generated title {result=}")
        return {"text": result}

    def _generate_topic(self, user_prompt: str, text: str, schema: str | None) -> str | dict:
        """
        Generate short topic and short summary
        """
        prompt = self._create_prompt(user_prompt=user_prompt, text=text)
        result = self._generate(prompt=prompt, schema=schema, gen_cfg=self.topic_gen_cfg)
        return {"text": result}

    def _generate_summary(self, user_prompt: str, text: str, schema: str | None) -> str | dict:
        """
        Generate final summary
        """
        chunk_summary = []
        for chunk in self._split_corpus(text):
            prompt = self._create_prompt(user_prompt=user_prompt, text=chunk)
            summary = self._generate(prompt=prompt, schema=schema, gen_cfg=self.summary_gen_cfg)
            summary = summary["summary"] if schema else summary
            chunk_summary.append(summary)

        final_summary = {"summary": "".join(chunk_summary)}
        print(f"Generated final summary {final_summary=}")
        return {"text": final_summary}

    def _generate(self, prompt: str, gen_cfg, schema: str | None) -> str | dict:
        """
        Perform a generation action using the LLM
        """
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
        return response

    @method()
    def generate(self, user_prompt: str, task: str, text: str, schema: str = None) -> str | dict:
        """
        Entry point to the LLM. Delegate generation, based on the type of generation task requested
        """
        return self._generation_swivel(user_prompt=user_prompt, text=text, task=task, schema=schema)

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
        if req.schema_:
            func = llmstub.generate.spawn(user_prompt=req.prompt,
                                          text=req.text,
                                          task=req.task,
                                          schema=json.dumps(req.schema_))
        else:
            func = llmstub.generate.spawn(user_prompt=req.prompt, text=req.text, task=req.task)
        result = func.get()
        return result

    @app.post("/warmup", dependencies=[Depends(apikey_auth)])
    async def warmup():
        return llmstub.warmup.spawn().get()

    return app
