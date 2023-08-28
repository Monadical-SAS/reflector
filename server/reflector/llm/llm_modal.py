import httpx

from reflector.llm.base import LLM
from reflector.settings import settings
from reflector.utils.retry import retry


class ModalLLM(LLM):
    def __init__(self):
        super().__init__()
        self.timeout = settings.LLM_TIMEOUT
        self.llm_name = "lmsys/vicuna-13b-v1.5"
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

    async def _generate(
        self, prompt: str, text: str, task: str, schema: dict | None, **kwargs
    ):
        json_payload = {"prompt": prompt, "text": text, "task": task}
        if schema:
            json_payload["schema"] = schema
        async with httpx.AsyncClient() as client:
            response = await retry(client.post)(
                self.llm_url,
                headers=self.headers,
                json=json_payload,
                timeout=self.timeout,
                retry_timeout=60 * 5,
            )
            response.raise_for_status()
            text = response.json()["text"]
            return text


LLM.register("modal", ModalLLM)

if __name__ == "__main__":
    from reflector.logger import logger

    async def main():
        llm = ModalLLM()
        prompt = "Complete the following task."
        task = "chat"
        result = await llm.generate(
            prompt=prompt,
            task=task,
            text="Tell me a joke about programming",
            logger=logger,
        )
        print(result)

        schema = {
            "type": "object",
            "properties": {"response": {"type": "string"}},
        }

        result = await llm.generate(
            prompt=prompt,
            task=task,
            text="Tell me a joke about programming",
            schema=schema,
            logger=logger,
        )
        print(result)

    import asyncio

    asyncio.run(main())
