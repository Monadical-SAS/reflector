import json

import httpx
from reflector.llm.base import LLM
from reflector.settings import settings


class OobaboogaLLM(LLM):
    async def _generate(self, prompt: str, **kwargs):
        json_payload = {"prompt": prompt}
        if "schema" in kwargs:
            json_payload["schema"] = json.dumps(kwargs["schema"])
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.LLM_URL,
                headers={"Content-Type": "application/json"},
                json=json_payload,
            )
            response.raise_for_status()
            return response.json()


LLM.register("oobabooga", OobaboogaLLM)
