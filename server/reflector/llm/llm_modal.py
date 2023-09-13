import httpx
from transformers import AutoTokenizer, GenerationConfig

from reflector.llm.base import LLM
from reflector.logger import logger as reflector_logger
from reflector.settings import settings
from reflector.utils.retry import retry


class ModalLLM(LLM):
    def __init__(self, model_name: str | None = None):
        super().__init__()
        self.timeout = settings.LLM_TIMEOUT
        self.llm_url = settings.LLM_URL + "/llm"
        self.llm_warmup_url = settings.LLM_URL + "/warmup"
        self.headers = {
            "Authorization": f"Bearer {settings.LLM_MODAL_API_KEY}",
        }
        self._set_model_name(model_name if model_name else settings.DEFAULT_LLM)

    @property
    def supported_models(self):
        """
        List of currently supported models on this GPU platform
        """
        # TODO: Query the specific GPU platform
        # Replace this with a HTTP call
        return ["lmsys/vicuna-13b-v1.5"]

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

    def _set_model_name(self, model_name: str) -> bool:
        """
        Set the model name
        """
        # Abort, if the model is not supported
        if model_name not in self.supported_models:
            reflector_logger.info(
                f"Attempted to change {model_name=}, but is not supported."
                f"Setting model and tokenizer failed !"
            )
            return False
        # Abort, if the model is already set
        elif hasattr(self, "model_name") and model_name == self._get_model_name():
            reflector_logger.info("No change in model. Setting model skipped.")
            return False
        # Update model name and tokenizer
        self.model_name = model_name
        self.llm_tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, cache_dir=settings.CACHE_DIR
        )
        reflector_logger.info(f"Model set to {model_name=}. Tokenizer updated.")
        return True

    def _get_tokenizer(self) -> AutoTokenizer:
        """
        Return the currently used LLM tokenizer
        """
        return self.llm_tokenizer

    def _get_model_name(self) -> str:
        """
        Return the current model name from the instance details
        """
        return self.model_name


LLM.register("modal", ModalLLM)

if __name__ == "__main__":
    from reflector.logger import logger

    async def main():
        llm = ModalLLM()
        prompt = llm.create_prompt(
            instruct="Complete the following task",
            text="Tell me a joke about programming.",
        )
        result = await llm.generate(prompt=prompt, logger=logger)
        print(result)

        gen_schema = {
            "type": "object",
            "properties": {"response": {"type": "string"}},
        }

        result = await llm.generate(prompt=prompt, gen_schema=gen_schema, logger=logger)
        print(result)

        gen_cfg = GenerationConfig(max_new_tokens=150)
        result = await llm.generate(
            prompt=prompt, gen_cfg=gen_cfg, gen_schema=gen_schema, logger=logger
        )
        print(result)

    import asyncio

    asyncio.run(main())
