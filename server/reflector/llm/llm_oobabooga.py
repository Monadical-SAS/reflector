import httpx

from reflector.llm.base import LLM
from reflector.settings import settings


class OobaboogaLLM(LLM):
    def __init__(self, model_name: str | None = None):
        super().__init__()

    async def _generate(
        self, prompt: str, gen_schema: dict | None, gen_cfg: dict | None, **kwargs
    ):
        json_payload = {"prompt": prompt}
        if gen_schema:
            json_payload["gen_schema"] = gen_schema
        if gen_cfg:
            json_payload["gen_cfg"] = gen_cfg
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.LLM_URL,
                headers={"Content-Type": "application/json"},
                json=json_payload,
            )
            response.raise_for_status()
            return response.json()


LLM.register("oobabooga", OobaboogaLLM)
