import httpx

from reflector.llm.base import LLM
from reflector.settings import settings
from reflector.utils.retry import retry


class BananaLLM(LLM):
    def __init__(self):
        super().__init__()
        self.timeout = settings.LLM_TIMEOUT
        self.headers = {
            "X-Banana-API-Key": settings.LLM_BANANA_API_KEY,
            "X-Banana-Model-Key": settings.LLM_BANANA_MODEL_KEY,
        }

    async def _generate(
        self, prompt: str, gen_schema: dict | None, gen_cfg: dict | None, **kwargs
    ):
        json_payload = {"prompt": prompt}
        if gen_schema:
            json_payload["gen_schema"] = gen_schema
        if gen_cfg:
            json_payload["gen_cfg"] = gen_cfg
        async with httpx.AsyncClient() as client:
            response = await retry(client.post)(
                settings.LLM_URL,
                headers=self.headers,
                json=json_payload,
                timeout=self.timeout,
                retry_timeout=300,  # as per their sdk
            )
            response.raise_for_status()
            text = response.json()["text"]
            return text


LLM.register("banana", BananaLLM)

if __name__ == "__main__":

    async def main():
        llm = BananaLLM()
        prompt = "Complete the following task."
        task = "chat"
        result = await llm.generate(
            prompt=prompt, task=task, text="Tell me a joke about programming"
        )
        print(result)

    import asyncio

    asyncio.run(main())
