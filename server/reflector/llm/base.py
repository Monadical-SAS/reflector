import importlib
import json
import re
from time import monotonic
from typing import List

import nltk
from transformers import AutoTokenizer, GenerationConfig

from reflector.logger import logger as reflector_logger
from reflector.settings import settings
from reflector.utils.retry import retry

from .llm_params import LLMParams


class LLM:
    _registry = {}

    @classmethod
    def register(cls, name, klass):
        cls._registry[name] = klass

    @classmethod
    def get_instance(cls, model_name, name=None):
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
        cls.model_name = model_name
        cls.tokenizer = AutoTokenizer.from_pretrained(model_name)
        return cls._registry[name]()

    @property
    def template(self):
        return """
        ### Human:
        {user_prompt}

        {text}

        ### Assistant:
        """

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

    @property
    def tokenizer(self):
        return self.tokenizer

    async def generate(
        self,
        prompt: str,
        logger: reflector_logger,
        schema: dict | None = None,
        gen_cfg: GenerationConfig | None = None,
        **kwargs,
    ) -> dict:
        logger.info("LLM generate", prompt=repr(prompt))
        try:
            result = await retry(self._generate)(
                prompt=prompt, schema=schema, gen_cfg=gen_cfg.to_dict(), **kwargs
            )
        except Exception:
            logger.exception("Failed to call llm after retrying")
            raise

        logger.debug("LLM result [raw]", result=repr(result))
        if isinstance(result, str):
            result = self._parse_json(result)
        logger.debug("LLM result [parsed]", result=repr(result))

        return result

    async def _generate(
        self, prompt: str, schema: dict | None, gen_cfg: dict | None, **kwargs
    ) -> str:
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

    def text_token_threshold(
        self, prompt: str, gen_cfg: GenerationConfig | None
    ) -> int:
        """
        Choose the token size to set as the threshold to pack the LLM calls
        """
        buffer_token_size = 25
        default_output_tokens = 1000
        context_window = self.tokenizer.model_max_length
        tokens = self.tokenizer.tokenize(
            self.template.format(user_prompt=prompt, text="")
        )
        threshold = context_window - len(tokens) - buffer_token_size
        if gen_cfg:
            threshold -= gen_cfg.max_new_tokens
        else:
            threshold -= default_output_tokens
        return threshold

    def split_corpus(
        self,
        corpus: str,
        params: LLMParams,
        token_threshold: int | None = None,
    ) -> List[str]:
        """
        Split the input to the LLM due to CUDA memory limitations and LLM context window
        restrictions.

        Accumulate tokens from full sentences till threshold and yield accumulated
        tokens. Reset accumulation and repeat process.
        """
        nltk.download("punkt", quiet=True)

        if not token_threshold:
            token_threshold = self.text_token_threshold(
                prompt=self.template, gen_cfg=params.gen_cfg
            )

        accumulated_tokens = []
        accumulated_sentences = []
        accumulated_token_count = 0
        corpus_sentences = nltk.sent_tokenize(corpus)

        for sentence in corpus_sentences:
            tokens = self.tokenizer.tokenize(sentence)
            if accumulated_token_count + len(tokens) <= token_threshold:
                accumulated_token_count += len(tokens)
                accumulated_tokens.extend(tokens)
                accumulated_sentences.append(sentence)
            else:
                yield "".join(accumulated_sentences)
                accumulated_token_count = len(tokens)
                accumulated_tokens = tokens
                accumulated_sentences = [sentence]

        if accumulated_tokens:
            yield " ".join(accumulated_sentences)

    def create_prompt(self, user_prompt: str, text: str) -> str:
        """
        Create a consumable prompt based on the prompt template
        """
        return self.template.format(user_prompt=user_prompt, text=text)

    async def get_response(self, text, params, logger):
        prompt = self.create_prompt(user_prompt=params.instruct, text=text)
        response = await retry(self.generate)(
            prompt=prompt,
            gen_cfg=params.gen_cfg,
            schema=params.schema,
            logger=logger,
        )
        return response
