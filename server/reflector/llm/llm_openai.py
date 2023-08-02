from reflector.llm.base import LLM
from reflector.logger import logger
from reflector.settings import settings
import httpx


class OpenAILLM(LLM):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.openai_key = settings.LLM_OPENAI_KEY
        self.openai_url = settings.LLM_URL
        self.openai_model = settings.LLM_OPENAI_MODEL
        self.openai_temperature = settings.LLM_OPENAI_TEMPERATURE
        self.timeout = settings.LLM_TIMEOUT
        self.max_tokens = settings.LLM_MAX_TOKENS
        logger.info(f"LLM use openai backend at {self.openai_url}")

    async def _generate(self, prompt: str, **kwargs) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}",
        }

        logger.debug(f"LLM openai prompt: {prompt}")

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
            logger.info(f"LLM openai result: {result}")
            return result["choices"][0]["text"]


LLM.register("openai", OpenAILLM)
