import httpx
from transformers import GenerationConfig

from reflector.llm.base import LLM
from reflector.logger import logger
from reflector.settings import settings


class OpenAILLM(LLM):
    def __init__(self, model_name: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.openai_key = settings.LLM_OPENAI_KEY
        self.openai_url = settings.LLM_URL
        self.openai_model = settings.LLM_OPENAI_MODEL
        self.openai_temperature = settings.LLM_OPENAI_TEMPERATURE
        self.timeout = settings.LLM_TIMEOUT
        self.max_tokens = settings.LLM_MAX_TOKENS
        logger.info(f"LLM use openai backend at {self.openai_url}")

    async def _generate(
        self,
        prompt: str,
        gen_schema: dict | None,
        gen_cfg: GenerationConfig | None,
        **kwargs,
    ) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.openai_url,
                headers=headers,
                json={
                    "model": self.openai_model,
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": self.openai_temperature,
                },
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["text"]


LLM.register("openai", OpenAILLM)
