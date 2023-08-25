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
        self, prompt: str, text: str, task: str, schema: dict | None, **kwargs
    ):
        json_payload = {"prompt": prompt, "text": text, "task": task}
        if schema:
            json_payload["schema"] = schema
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
        prompt = "Complete the following sentence."
        result = await llm.generate(prompt=prompt, text="Hello, my name is")
        print(result)

    import asyncio

    asyncio.run(main())
