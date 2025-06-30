import httpx
from reflector.llm.base import LLM
from reflector.logger import logger as reflector_logger
from reflector.settings import settings
from reflector.utils.retry import retry
from transformers import AutoTokenizer

supported_models = [
    "alsdjfalsdjfs/DeepSeek-R1-0528-IQ1_S",
    "~~Qwen/Qwen3-235B-A22B",
    "monadical/private/smart",  # (Phi-4 quant)
    "monadical/private/dumb",  # (Phi-4 quant)
    "monadical/private/reasoning",  # (Phi-4 quant)
    "openai/gpt-4o-mini",
    # Add more models as needed
]

class LiteLLMLLM(LLM):
    def __init__(self, model_name: str | None = None):
        super().__init__()
        self.timeout = settings.LLM_TIMEOUT
        self.litellm_url = settings.LITELLM_URL
        self.litellm_key = settings.LITELLM_PRIVATE_KEY
        self.litellm_temperature = settings.LITELLM_TEMPERATURE
        self.headers = {
            "Authorization": f"Bearer {self.litellm_key}",
            "Content-Type": "application/json",
        }

        # many calls use hardcoded NousResearch/Hermes-3-Llama-3.1-8B that isn't supported by all the providers
        # ideal solution is to remove hardcode and also remove this check altogether
        if model_name and model_name not in supported_models:
            reflector_logger.warning(
                f"Requested model '{model_name}' not in supported_models for litellm backend. "
                f"Supported models: {supported_models}. Using default model instead."
            )
            model_name = None


        default_model = model_name if model_name else settings.LITELLM_MODEL
        assert default_model is not None, "LITELLM_MODEL setting must not be None"
        self._set_model_name(default_model)

    @property
    def supported_models(self):
        """
        Runpod-hosted + openrouter/*, openai/*
        """
        # TODO: Query the specific GPU platform, and on ModalLLM too
        return supported_models

    def _apply_gen_cfg(self, gen_cfg: dict | None, kwargs: dict) -> None:
        """Apply generation configuration parameters to kwargs"""
        if gen_cfg:
            if "temperature" in gen_cfg:
                kwargs["temperature"] = gen_cfg["temperature"]
            if "max_new_tokens" in gen_cfg:
                kwargs["max_tokens"] = gen_cfg["max_new_tokens"]

    def has_structured_output(self):
        # if we want to make this check runtime, we need to make it async, and we need to add another entity custom_llm_provider
        # supports_response_schema(model="gemini-1.5-pro-preview-0215", custom_llm_provider="bedrock")
        # https://docs.litellm.ai/docs/completion/json_mode
        # easier to have a hardcoded mapping for now
        # from docs:
        # """
        # Works for:
        #
        # OpenAI models
        # Azure OpenAI models
        # xAI models (Grok-2 or later)
        # Google AI Studio - Gemini models
        # Vertex AI models (Gemini + Anthropic)
        # Bedrock Models
        # Anthropic API Models
        # Groq Models
        # Ollama Models
        # Databricks Models
        # """
        return "openai" in self.model_name # TODO more

    def _convert_gen_schema_to_response_format(self, gen_schema: dict) -> dict:
        """Convert gen_schema to LiteLLM response_format"""
        if not gen_schema:
            return None
            
        schema_copy = gen_schema.copy()
        
        # Required for OpenAI structured outputs
        if "additionalProperties" not in schema_copy:
            schema_copy["additionalProperties"] = False
        
        # Required array must include all property keys
        if "properties" in schema_copy and "required" not in schema_copy:
            schema_copy["required"] = list(schema_copy["properties"].keys())
            
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "response_schema",
                "schema": schema_copy,
                "strict": True
            }
        }

    async def _make_chat_completion(self, messages: list, response_format: dict = None, **kwargs) -> dict:
        """Common method for making chat completion requests"""
        kwargs.setdefault("temperature", self.litellm_temperature)
        kwargs.setdefault("max_tokens", 2048)
        kwargs.setdefault("stream", False)

        json_payload = {"model": self.model_name, "messages": messages, **kwargs}
        
        if response_format:
            json_payload["response_format"] = response_format

        async with httpx.AsyncClient() as client:
            response = await retry(lambda: client.post(
                f"{self.litellm_url}/v1/chat/completions",
                headers=self.headers,
                json=json_payload,
                timeout=self.timeout,
                follow_redirects=True,
            ))(retry_timeout=60 * 5)
            response.raise_for_status()
            return response.json()

    # returns text
    async def _generate(
        self, prompt: str, gen_schema: dict | None, gen_cfg: dict | None, **kwargs
    ):
        """
        Convert template-based generation to chat completion format
        """
        
        messages = [{"role": "user", "content": prompt}]
        self._apply_gen_cfg(gen_cfg, kwargs)
        
        response_format = self._convert_gen_schema_to_response_format(gen_schema)
        
        result = await self._make_chat_completion(messages, response_format=response_format, **kwargs)
        return result["choices"][0]["message"]["content"]

    # returns full api response
    async def _completion(
        self, messages: list, gen_cfg: dict | None = None, **kwargs
    ) -> dict:
        """
        Direct chat completion using LiteLLM
        """
        
        self._apply_gen_cfg(gen_cfg, kwargs)

        return await self._make_chat_completion(messages, **kwargs)


    def _set_model_name(self, model_name: str) -> bool:
        """
        Set the model name and load tokenizer
        """
        # For LiteLLM, we're more permissive with model names since it proxies many providers
        if hasattr(self, "model_name") and model_name == self._get_model_name():
            reflector_logger.info("No change in model. Setting model skipped.")
            return False

        self.model_name = model_name
        
        # Map LiteLLM model names to compatible Hugging Face tokenizers
        tokenizer_map = {
            "openai/gpt-4o-mini": "gpt2",
            "openai/gpt-4o": "gpt2", 
            "openai/gpt-3.5-turbo": "gpt2",
            "alsdjfalsdjfs/DeepSeek-R1-0528-IQ1_S": "gpt2"  # fallback to gpt2
        }
        
        tokenizer_name = tokenizer_map.get(self.model_name, "gpt2")  # default to gpt2
        self.llm_tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name, cache_dir=settings.CACHE_DIR
        )

        reflector_logger.info(f"Model set to {model_name=}. Tokenizer loaded.")
        return True

    # not required by the base class but will fail if not defined at the point of queue handling
    def _get_tokenizer(self):
        return self.llm_tokenizer

    def _get_model_name(self) -> str:
        """
        Return the current model name from the instance details
        """
        return self.model_name


# Register the LiteLLM backend
LLM.register("litellm", LiteLLMLLM)


if __name__ == "__main__":
    from reflector.logger import logger
    import asyncio

    async def main():
        llm = LiteLLMLLM()

        # Test basic generation
        prompt = llm.create_prompt(
            instruct="Generate a short title for this content",
            text="This is a meeting about project planning and timeline discussions.",
        )
        result = await llm.generate(prompt=prompt, logger=logger)
        print("Generate result:", result)

        # Test with schema
        gen_schema = {
            "type": "object",
            "properties": {"title": {"type": "string"}},
        }
        result = await llm.generate(prompt=prompt, gen_schema=gen_schema, logger=logger)
        print("Schema result:", result)

        # Test completion
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that creates concise titles.",
            },
            {
                "role": "user",
                "content": "Create a title for a meeting about project planning",
            },
        ]
        result = await llm.completion(messages=messages, logger=logger)
        print("Completion result:", result)

    asyncio.run(main())
