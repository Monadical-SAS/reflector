from reflector.logger import logger
from reflector.settings import settings
from reflector.utils.retry import retry
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

    async def generate(self, prompt: str, **kwargs) -> dict:
        try:
            result = await retry(self._generate)(prompt=prompt, **kwargs)
        except Exception:
            logger.exception("Failed to call llm after retrying")
            raise

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
        if matches:
            result = matches[0][1]

        else:
            # maybe the prompt has been started with ```json
            # so if text ends with ```, just remove it and use it as json
            if result.endswith("```"):
                result = result[:-3]

        return json.loads(result.strip())
