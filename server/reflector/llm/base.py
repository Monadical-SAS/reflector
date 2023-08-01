from reflector.logger import logger
from reflector.settings import settings
import asyncio
import json
import re


class LLM:
    _registry = {}

    @classmethod
    def register(cls, name, klass):
        cls._registry[name] = klass

    @classmethod
    def instance(cls):
        """
        Return an instance depending on the settings.
        Settings used:

        - `LLM_BACKEND`: key of the backend, defaults to `oobagooda`
        - `LLM_URL`: url of the backend
        """
        return cls._registry[settings.LLM_BACKEND]()

    async def generate(
        self, prompt: str, retry_count: int = 5, retry_interval: int = 1, **kwargs
    ) -> dict:
        while retry_count > 0:
            try:
                result = await self._generate(prompt=prompt, **kwargs)
                break
            except Exception:
                logger.exception("Failed to call llm")
                retry_count -= 1
                await asyncio.sleep(retry_interval)

        if retry_count == 0:
            raise Exception("Failed to call llm after retrying")

        if isinstance(result, str):
            result = self._parse_json(result)

        return result

    async def _generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    def _parse_json(self, result: str) -> dict:
        result = result.strip()
        # try detecting code block if exist
        # starts with ```json\n, ends with ```
        # or starts with ```\n, ends with ```
        # or starts with \n```javascript\n, ends with ```

        regex = r"```(json|javascript|)?(.*)```"
        matches = re.findall(regex, result.strip(), re.MULTILINE | re.DOTALL)
        if not matches:
            return result

        # we have a match, try to parse it
        result = matches[0][1]
        return json.loads(result.strip())
