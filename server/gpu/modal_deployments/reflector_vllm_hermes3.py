# # Run an OpenAI-Compatible vLLM Server

import modal

MODELS_DIR = "/llamas"
MODEL_NAME = "NousResearch/Hermes-3-Llama-3.1-8B"
N_GPU = 1


def download_llm():
    from huggingface_hub import snapshot_download

    print("Downloading LLM model")
    snapshot_download(
        MODEL_NAME,
        local_dir=f"{MODELS_DIR}/{MODEL_NAME}",
        ignore_patterns=[
            "*.pt",
            "*.bin",
            "*.pth",
            "original/*",
        ],  # Ensure safetensors
    )
    print("LLM model downloaded")


def move_cache():
    from transformers.utils import move_cache as transformers_move_cache

    transformers_move_cache()


vllm_image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("vllm==0.5.3post1")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .pip_install(
        # "accelerate==0.34.2",
        "einops==0.8.0",
        "hf-transfer~=0.1",
    )
    .run_function(download_llm)
    .run_function(move_cache)
    .pip_install(
        "bitsandbytes>=0.42.9",
    )
)

app = modal.App("reflector-vllm-hermes3")


@app.function(
    image=vllm_image,
    gpu=modal.gpu.A100(count=N_GPU, size="40GB"),
    timeout=60 * 5,
    container_idle_timeout=60 * 5,
    allow_concurrent_inputs=100,
    secrets=[
        modal.Secret.from_name("reflector-gpu"),
    ],
)
@modal.asgi_app()
def serve():
    import os

    import fastapi
    import vllm.entrypoints.openai.api_server as api_server
    from vllm.engine.arg_utils import AsyncEngineArgs
    from vllm.engine.async_llm_engine import AsyncLLMEngine
    from vllm.entrypoints.logger import RequestLogger
    from vllm.entrypoints.openai.serving_chat import OpenAIServingChat
    from vllm.entrypoints.openai.serving_completion import OpenAIServingCompletion
    from vllm.usage.usage_lib import UsageContext

    TOKEN = os.environ["REFLECTOR_GPU_APIKEY"]

    # create a fastAPI app that uses vLLM's OpenAI-compatible router
    web_app = fastapi.FastAPI(
        title=f"OpenAI-compatible {MODEL_NAME} server",
        description="Run an OpenAI-compatible LLM server with vLLM on modal.com",
        version="0.0.1",
        docs_url="/docs",
    )

    # security: CORS middleware for external requests
    http_bearer = fastapi.security.HTTPBearer(
        scheme_name="Bearer Token",
        description="See code for authentication details.",
    )
    web_app.add_middleware(
        fastapi.middleware.cors.CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # security: inject dependency on authed routes
    async def is_authenticated(api_key: str = fastapi.Security(http_bearer)):
        if api_key.credentials != TOKEN:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return {"username": "authenticated_user"}

    router = fastapi.APIRouter(dependencies=[fastapi.Depends(is_authenticated)])

    # wrap vllm's router in auth router
    router.include_router(api_server.router)
    # add authed vllm to our fastAPI app
    web_app.include_router(router)

    engine_args = AsyncEngineArgs(
        model=MODELS_DIR + "/" + MODEL_NAME,
        tensor_parallel_size=N_GPU,
        gpu_memory_utilization=0.90,
        # max_model_len=8096,
        enforce_eager=False,  # capture the graph for faster inference, but slower cold starts (30s > 20s)
        # --- 4 bits load
        # quantization="bitsandbytes",
        # load_format="bitsandbytes",
    )

    engine = AsyncLLMEngine.from_engine_args(
        engine_args, usage_context=UsageContext.OPENAI_API_SERVER
    )

    model_config = get_model_config(engine)

    request_logger = RequestLogger(max_log_len=2048)

    api_server.openai_serving_chat = OpenAIServingChat(
        engine,
        model_config=model_config,
        served_model_names=[MODEL_NAME],
        chat_template=None,
        response_role="assistant",
        lora_modules=[],
        prompt_adapters=[],
        request_logger=request_logger,
    )
    api_server.openai_serving_completion = OpenAIServingCompletion(
        engine,
        model_config=model_config,
        served_model_names=[MODEL_NAME],
        lora_modules=[],
        prompt_adapters=[],
        request_logger=request_logger,
    )

    return web_app


def get_model_config(engine):
    import asyncio

    try:  # adapted from vLLM source -- https://github.com/vllm-project/vllm/blob/507ef787d85dec24490069ffceacbd6b161f4f72/vllm/entrypoints/openai/api_server.py#L235C1-L247C1
        event_loop = asyncio.get_running_loop()
    except RuntimeError:
        event_loop = None

    if event_loop is not None and event_loop.is_running():
        # If the current is instanced by Ray Serve,
        # there is already a running event loop
        model_config = event_loop.run_until_complete(engine.get_model_config())
    else:
        # When using single vLLM without engine_use_ray
        model_config = asyncio.run(engine.get_model_config())

    return model_config
