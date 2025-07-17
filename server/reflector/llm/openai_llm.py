import httpx
from transformers import AutoTokenizer
from reflector.logger import logger


def apply_gen_config(payload: dict, gen_cfg) -> None:
    """Apply generation config overrides to the payload."""
    config_mapping = {
        "temperature": "temperature",
        "max_new_tokens": "max_tokens",
        "max_tokens": "max_tokens",
        "top_p": "top_p",
        "frequency_penalty": "frequency_penalty",
        "presence_penalty": "presence_penalty",
    }

    for cfg_attr, payload_key in config_mapping.items():
        value = getattr(gen_cfg, cfg_attr, None)
        if value is not None:
            payload[payload_key] = value
            if cfg_attr == "max_new_tokens":  # Handle max_new_tokens taking precedence
                break


class OpenAILLM:
    def __init__(self, config_prefix: str, settings):
        self.config_prefix = config_prefix
        self.settings_obj = settings
        self.model_name = getattr(settings, f"{config_prefix}_MODEL")
        self.url = getattr(settings, f"{config_prefix}_LLM_URL")
        self.api_key = getattr(settings, f"{config_prefix}_LLM_API_KEY")

        timeout = getattr(settings, f"{config_prefix}_LLM_TIMEOUT", 300)
        self.temperature = getattr(settings, f"{config_prefix}_LLM_TEMPERATURE", 0.7)
        self.max_tokens = getattr(settings, f"{config_prefix}_LLM_MAX_TOKENS", 1024)
        self.client = httpx.AsyncClient(timeout=timeout)

        # Use a tokenizer that approximates OpenAI token counting
        tokenizer_name = getattr(settings, f"{config_prefix}_TOKENIZER", "gpt2")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        except Exception:
            logger.debug(
                f"Failed to load tokenizer '{tokenizer_name}', falling back to default 'gpt2' tokenizer"
            )
            self.tokenizer = AutoTokenizer.from_pretrained("gpt2")

    async def generate(
        self, prompt: str, gen_schema=None, gen_cfg=None, logger=None
    ) -> str:
        if logger:
            logger.debug(
                "OpenAI LLM generate",
                prompt=repr(prompt[:100] + "..." if len(prompt) > 100 else prompt),
            )

        messages = [{"role": "user", "content": prompt}]
        result = await self.completion(
            messages, gen_schema=gen_schema, gen_cfg=gen_cfg, logger=logger
        )
        return result["choices"][0]["message"]["content"]

    async def completion(
        self, messages: list, gen_schema=None, gen_cfg=None, logger=None, **kwargs
    ) -> dict:
        if logger:
            logger.info("OpenAI LLM completion", messages_count=len(messages))

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Apply generation config overrides
        if gen_cfg:
            apply_gen_config(payload, gen_cfg)

        # Apply structured output schema
        if gen_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": gen_schema},
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        url = f"{self.url.rstrip('/')}/chat/completions"

        if logger:
            logger.debug(
                "OpenAI API request", url=url, payload_keys=list(payload.keys())
            )

        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()

        if logger:
            logger.debug(
                "OpenAI API response",
                status_code=response.status_code,
                choices_count=len(result.get("choices", [])),
            )

        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
