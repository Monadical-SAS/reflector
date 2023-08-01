from reflector.llm.base import LLM
from reflector.settings import settings
import httpx


class OobagoodaLLM(LLM):
    async def _generate(self, prompt: str, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.LLM_URL,
                headers={"Content-Type": "application/json"},
                json={"prompt": prompt},
            )
            response.raise_for_status()
            return response.json()


LLM.register("oobagooda", OobagoodaLLM)
