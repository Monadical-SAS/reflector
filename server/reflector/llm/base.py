import importlib
import json
import re
from time import monotonic

from prometheus_client import Counter, Histogram
from reflector.logger import logger as reflector_logger
from reflector.settings import settings
from reflector.utils.retry import retry


class LLM:
    _registry = {}
    m_generate = Histogram(
        "llm_generate",
        "Time spent in LLM.generate",
        ["backend"],
    )
    m_generate_call = Counter(
        "llm_generate_call",
        "Number of calls to LLM.generate",
        ["backend"],
    )
    m_generate_success = Counter(
        "llm_generate_success",
        "Number of successful calls to LLM.generate",
        ["backend"],
    )
    m_generate_failure = Counter(
        "llm_generate_failure",
        "Number of failed calls to LLM.generate",
        ["backend"],
    )

    @classmethod
    def register(cls, name, klass):
        cls._registry[name] = klass

    @classmethod
    def get_instance(cls, name=None):
        """
        Return an instance depending on the settings.
        Settings used:

        - `LLM_BACKEND`: key of the backend, defaults to `oobabooga`
        - `LLM_URL`: url of the backend
        """
        if name is None:
            name = settings.LLM_BACKEND
        if name not in cls._registry:
            module_name = f"reflector.llm.llm_{name}"
            importlib.import_module(module_name)
        return cls._registry[name]()

    def __init__(self):
        name = self.__class__.__name__
        self.m_generate = self.m_generate.labels(name)
        self.m_generate_call = self.m_generate_call.labels(name)
        self.m_generate_success = self.m_generate_success.labels(name)
        self.m_generate_failure = self.m_generate_failure.labels(name)

    async def warmup(self, logger: reflector_logger):
        start = monotonic()
        name = self.__class__.__name__
        logger.info(f"LLM[{name}] warming up...")
        try:
            await self._warmup(logger=logger)
            duration = monotonic() - start
            logger.info(f"LLM[{name}] warmup took {duration:.2f} seconds")
        except Exception:
            logger.exception(f"LLM[{name}] warmup failed, ignoring")

    async def _warmup(self, logger: reflector_logger):
        pass

    async def generate(
        self,
        prompt: str,
        logger: reflector_logger,
        schema: dict | None = None,
        **kwargs,
    ) -> dict:
        logger.info("LLM generate", prompt=repr(prompt))
        self.m_generate_call.inc()
        try:
            with self.m_generate.time():
                result = await retry(self._generate)(
                    prompt=prompt, schema=schema, **kwargs
                )
            self.m_generate_success.inc()
        except Exception:
            logger.exception("Failed to call llm after retrying")
            self.m_generate_failure.inc()
            raise

        logger.debug("LLM result [raw]", result=repr(result))
        if isinstance(result, str):
            result = self._parse_json(result)
        logger.debug("LLM result [parsed]", result=repr(result))

        return result

    async def _generate(self, prompt: str, schema: dict | None, **kwargs) -> str:
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
