from reflector.settings import settings
from reflector.utils.retry import retry
from reflector.logger import logger as reflector_logger
import importlib
import json
import re


class LLM:
    _registry = {}

    @classmethod
    def register(cls, name, klass):
        cls._registry[name] = klass

    @classmethod
    def get_instance(cls, name=None):
        """
        Return an instance depending on the settings.
        Settings used:

        - `LLM_BACKEND`: key of the backend, defaults to `oobagooda`
        - `LLM_URL`: url of the backend
        """
        if name is None:
            name = settings.LLM_BACKEND
        if name not in cls._registry:
            module_name = f"reflector.llm.llm_{name}"
            importlib.import_module(module_name)
        return cls._registry[name]()

    async def generate(self, prompt: str, logger: reflector_logger, **kwargs) -> dict:
        logger.info("LLM generate", prompt=repr(prompt))
        try:
            result = await retry(self._generate)(prompt=prompt, **kwargs)
        except Exception:
            logger.exception("Failed to call llm after retrying")
            raise

        logger.debug("LLM result [raw]", result=repr(result))
        if isinstance(result, str):
            result = self._parse_json(result)
        logger.debug("LLM result [parsed]", result=repr(result))

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
