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
        self, prompt: str, gen_schema: dict | None, gen_cfg: dict | None, **kwargs
    ):
        json_payload = {"prompt": prompt}
        if gen_schema:
            json_payload["gen_schema"] = gen_schema
        if gen_cfg:
            json_payload["gen_cfg"] = gen_cfg
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
        prompt = "Tell me a joke about programming"
        result = await llm.generate(prompt=prompt, logger=logger)
        print(result)

        gen_schema = {
            "type": "object",
            "properties": {"response": {"type": "string"}},
        }

        result = await llm.generate(
            prompt=prompt,
            gen_schema=gen_schema,
            logger=logger,
        )
        print(result)

    import asyncio

    asyncio.run(main())
