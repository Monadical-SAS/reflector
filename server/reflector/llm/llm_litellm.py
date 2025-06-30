import httpx
from reflector.llm.base import LLM
from reflector.logger import logger as reflector_logger
from reflector.settings import settings
from reflector.utils.retry import retry
from transformers import AutoTokenizer


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
        self._set_model_name(model_name if model_name else settings.LITELLM_MODEL)

    @property
    def supported_models(self):
        """
        Runpod-hosted + openrouter/*, openai/*

        """
        # TODO: Query the specific GPU platform, and on ModalLLM too
        return [
            "alsdjfalsdjfs/DeepSeek-R1-0528-IQ1_S",
            "~~Qwen/Qwen3-235B-A22B",
            "monadical/private/smart", # (Phi-4 quant)
            "monadical/private/dumb", # (Phi-4 quant)
            "monadical/private/reasoning", # (Phi-4 quant)
            "openai/gpt-4o-mini",
            # Add more models as needed
        ]

    def _apply_gen_cfg(self, gen_cfg: dict | None, kwargs: dict) -> None:
        """Apply generation configuration parameters to kwargs"""
        if gen_cfg:
            if "temperature" in gen_cfg:
                kwargs["temperature"] = gen_cfg["temperature"]
            if "max_new_tokens" in gen_cfg:
                kwargs["max_tokens"] = gen_cfg["max_new_tokens"]

    async def _make_chat_completion(self, messages: list, **kwargs) -> dict:
        """Common method for making chat completion requests"""
        kwargs.setdefault("temperature", self.litellm_temperature)
        kwargs.setdefault("max_tokens", 2048)
        kwargs.setdefault("stream", False)
        
        json_payload = {
            "model": self.model_name,
            "messages": messages,
            **kwargs
        }

        async with httpx.AsyncClient() as client:
            response = await retry(client.post)(
                f"{self.litellm_url}/v1/chat/completions",
                headers=self.headers,
                json=json_payload,
                timeout=self.timeout,
                retry_timeout=60 * 5,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.json()

    # returns text
    async def _generate(
        self, prompt: str, gen_schema: dict | None, gen_cfg: dict | None, **kwargs
    ):
        """
        Convert template-based generation to chat completion format
        """
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        self._apply_gen_cfg(gen_cfg, kwargs)
        
        result = await self._make_chat_completion(messages, **kwargs)
        return result["choices"][0]["message"]["content"]

    # returns full api response
    async def _completion(self, messages: list, gen_cfg: dict | None = None, **kwargs) -> dict:
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

        try:
            self.llm_tokenizer = AutoTokenizer.from_pretrained(
                model_name, cache_dir=settings.CACHE_DIR
            )
            if self.llm_tokenizer.pad_token is None:
                self.llm_tokenizer.pad_token = self.llm_tokenizer.eos_token
                
        except Exception as e:
            reflector_logger.warning(f"Failed to load tokenizer for {model_name}: {e}")
            self.llm_tokenizer = AutoTokenizer.from_pretrained(
                "gpt2", cache_dir=settings.CACHE_DIR
            )
            self.llm_tokenizer.pad_token = self.llm_tokenizer.eos_token
            
        reflector_logger.info(f"Model set to {model_name=}. Tokenizer loaded.")
        return True

    def _get_tokenizer(self) -> AutoTokenizer:
        """
        Return the currently used LLM tokenizer
        """
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
            {"role": "system", "content": "You are a helpful assistant that creates concise titles."},
            {"role": "user", "content": "Create a title for a meeting about project planning"}
        ]
        result = await llm.completion(messages=messages, logger=logger)
        print("Completion result:", result)

    asyncio.run(main())