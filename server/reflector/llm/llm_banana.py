from reflector.llm.base import LLM
from reflector.settings import settings
from reflector.utils.retry import retry
import httpx


class BananaLLM(LLM):
    def __init__(self):
        super().__init__()
        self.timeout = settings.LLM_TIMEOUT
        self.headers = {
            "X-Banana-API-Key": settings.LLM_BANANA_API_KEY,
            "X-Banana-Model-Key": settings.LLM_BANANA_MODEL_KEY,
        }

    async def _generate(self, prompt: str, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await retry(client.post)(
                settings.LLM_URL,
                headers=self.headers,
                json={"prompt": prompt},
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json()["text"]
            text = text[len(prompt) :]  # remove prompt
            return text


LLM.register("banana", BananaLLM)

if __name__ == "__main__":

    async def main():
        llm = BananaLLM()
        result = await llm.generate("Hello, my name is")
        print(result)

    import asyncio

    asyncio.run(main())
