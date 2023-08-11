from reflector.llm.base import LLM
from reflector.settings import settings
from reflector.utils.retry import retry
import httpx


class ModalLLM(LLM):
    def __init__(self):
        super().__init__()
        self.timeout = settings.LLM_TIMEOUT
        self.llm_url = settings.LLM_URL + "/llm"
        self.llm_warmup_url = settings.LLM_URL + "/warmup"
        self.headers = {
            "Authorization": f"Bearer {settings.LLM_MODAL_API_KEY}",
        }

    async def _warmup(self, logger):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.llm_warmup_url,
                headers=self.headers,
                timeout=60 * 5,
            )
            response.raise_for_status()

    async def _generate(self, prompt: str, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await retry(client.post)(
                self.llm_url,
                headers=self.headers,
                json={"prompt": prompt},
                timeout=self.timeout,
                retry_timeout=60 * 5,
            )
            response.raise_for_status()
            text = response.json()["text"]
            text = text[len(prompt) :]  # remove prompt
            return text


LLM.register("modal", ModalLLM)

if __name__ == "__main__":
    from reflector.logger import logger

    async def main():
        llm = ModalLLM()
        result = await llm.generate("Hello, my name is", logger=logger)
        print(result)

    import asyncio

    asyncio.run(main())
