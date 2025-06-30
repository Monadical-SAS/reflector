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
            "monadical/private/smart",  # (Phi-4 quant)
            "monadical/private/dumb",  # (Phi-4 quant)
            "monadical/private/reasoning",  # (Phi-4 quant)
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

        json_payload = {"model": self.model_name, "messages": messages, **kwargs}

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

        result = await self._make_chat_completion(messages, **kwargs)
        content = result["choices"][0]["message"]["content"]
        
        # Ensure response matches expected schema if gen_schema is provided
        if gen_schema and isinstance(gen_schema, dict):
            content = self._ensure_schema_compliance(content, gen_schema)
            
        return content

    # returns full api response
    async def _completion(
        self, messages: list, gen_cfg: dict | None = None, **kwargs
    ) -> dict:
        """
        Direct chat completion using LiteLLM
        """
        
        self._apply_gen_cfg(gen_cfg, kwargs)

        return await self._make_chat_completion(messages, **kwargs)

    def _ensure_schema_compliance(self, content: str, gen_schema: dict) -> str:
        """Ensure the LLM response matches the expected JSON schema"""
        import json
        
        # Remove code block markers first
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Try to parse as JSON
        try:
            parsed = json.loads(content)
            
            # Check if LLM returned a schema definition instead of data
            if isinstance(parsed, dict) and "$schema" in parsed:
                reflector_logger.warning(f"LLM returned schema definition instead of data: {parsed}")
                
                # If expecting an array, return empty array
                if gen_schema.get("type") == "array":
                    return json.dumps([])
                # If expecting an object, return minimal object matching schema
                elif gen_schema.get("type") == "object" and "properties" in gen_schema:
                    properties = gen_schema["properties"]
                    result = {}
                    for prop_name, prop_schema in properties.items():
                        if prop_schema.get("type") == "string":
                            result[prop_name] = ""
                        elif prop_schema.get("type") == "array":
                            result[prop_name] = []
                    return json.dumps(result)
                    
            # If it's valid JSON and not a schema, return as-is
            return json.dumps(parsed)
            
        except json.JSONDecodeError:
            pass
            
        # If JSON parsing fails, try to wrap in expected schema structure
        if gen_schema.get("type") == "array":
            # For array schema, try to extract content as array items
            if content:
                # Simple case: wrap single item in array
                wrapped = [content.strip('"')]
                return json.dumps(wrapped)
            else:
                return json.dumps([])
                
        elif gen_schema.get("type") == "object" and "properties" in gen_schema:
            properties = gen_schema["properties"]
            
            # Common case: single string property
            if len(properties) == 1:
                prop_name = list(properties.keys())[0]
                prop_schema = properties[prop_name]
                
                if prop_schema.get("type") == "string":
                    # Wrap the content in the expected JSON structure
                    wrapped = {prop_name: content.strip('"')}
                    return json.dumps(wrapped)
        
        # As a last resort, return the original content and let the caller handle it
        reflector_logger.warning(f"Could not ensure schema compliance for: {content}")
        return content

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
