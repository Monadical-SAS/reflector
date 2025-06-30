import importlib
import json
import re
from typing import TypeVar

import nltk
from prometheus_client import Counter, Histogram
from reflector.llm.llm_params import TaskParams
from reflector.logger import logger as reflector_logger
from reflector.settings import settings
from reflector.utils.retry import retry
from transformers import GenerationConfig

T = TypeVar("T", bound="LLM")


class LLM:
    _nltk_downloaded = False
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
    def ensure_nltk(cls):
        """
        Make sure NLTK package is installed. Searches in the cache and
        downloads only if needed.
        """
        if not cls._nltk_downloaded:
            nltk.download("punkt")
            # For POS tagging
            nltk.download("averaged_perceptron_tagger")
            cls._nltk_downloaded = True

    @classmethod
    def register(cls, name, klass):
        cls._registry[name] = klass

    @classmethod
    def get_instance(cls, model_name: str | None = None, name: str = None) -> T:
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
        cls.ensure_nltk()
        
        if model_name:
            temp_instance = cls._registry[name]()
            if hasattr(temp_instance, 'supported_models'):
                supported = temp_instance.supported_models
                if model_name not in supported:
                    reflector_logger.warning(
                        f"Requested model '{model_name}' not in supported_models for {name} backend. "
                        f"Supported models: {supported}. Using default model instead."
                    )
                    model_name = None
        
        return cls._registry[name](model_name)

    def get_model_name(self) -> str:
        """
        Get the currently set model name
        """
        return self._get_model_name()

    def _get_model_name(self) -> str:
        pass

    def set_model_name(self, model_name: str) -> bool:
        """
        Update the model name with the provided model name
        """
        return self._set_model_name(model_name)

    def _set_model_name(self, model_name: str) -> bool:
        raise NotImplementedError

    @property
    def template(self) -> str:
        """
        Return the LLM Prompt template
        """
        return """
        ### Human:
        {instruct}

        {text}

        ### Assistant:
        """

    def __init__(self):
        name = self.__class__.__name__
        self.m_generate = self.m_generate.labels(name)
        self.m_generate_call = self.m_generate_call.labels(name)
        self.m_generate_success = self.m_generate_success.labels(name)
        self.m_generate_failure = self.m_generate_failure.labels(name)
        self.detokenizer = nltk.tokenize.treebank.TreebankWordDetokenizer()

    @property
    def tokenizer(self):
        """
        Return the tokenizer instance used by LLM
        """
        return self._get_tokenizer()

    def _get_tokenizer(self):
        pass

    async def generate(
        self,
        prompt: str,
        logger: reflector_logger,
        gen_schema: dict | None = None,
        gen_cfg: GenerationConfig | None = None,
        **kwargs,
    ) -> dict:
        logger.info("LLM generate", prompt=repr(prompt))

        if gen_cfg:
            gen_cfg = gen_cfg.to_dict()
        self.m_generate_call.inc()
        try:
            with self.m_generate.time():
                result = await retry(self._generate)(
                    prompt=prompt,
                    gen_schema=gen_schema,
                    gen_cfg=gen_cfg,
                    **kwargs,
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

    async def completion(
        self, messages: list, logger: reflector_logger, **kwargs
    ) -> dict:
        """
        Use /v1/chat/completion Open-AI compatible endpoint from the URL
        It's up to the user to validate anything or transform the result
        """
        logger.info("LLM completions", messages=messages)

        try:
            with self.m_generate.time():
                result = await retry(self._completion)(messages=messages, **kwargs)
            self.m_generate_success.inc()
        except Exception:
            logger.exception("Failed to call llm after retrying")
            self.m_generate_failure.inc()
            raise

        logger.debug("LLM completion result", result=repr(result))
        return result

    def ensure_casing(self, title: str) -> str:
        """
        LLM takes care of word casing, but in rare cases this
        can falter. This is a fallback to ensure the casing of
        topics is in a proper format.

        We select nouns, verbs and adjectives and check if camel
         casing is present and fix it, if not. Will not perform
         any other changes.
        """
        tokens = nltk.word_tokenize(title)
        pos_tags = nltk.pos_tag(tokens)
        camel_cased = []

        whitelisted_pos_tags = [
            "NN",
            "NNS",
            "NNP",
            "NNPS",  # Noun POS
            "VB",
            "VBD",
            "VBG",
            "VBN",
            "VBP",
            "VBZ",  # Verb POS
            "JJ",
            "JJR",
            "JJS",  # Adjective POS
        ]

        # If at all there is an exception, do not block other reflector
        # processes. Return the LLM generated title, at the least.
        try:
            for word, pos in pos_tags:
                if pos in whitelisted_pos_tags and word[0].islower():
                    camel_cased.append(word[0].upper() + word[1:])
                else:
                    camel_cased.append(word)
            modified_title = self.detokenizer.detokenize(camel_cased)

            # Irrespective of casing changes, the starting letter
            # of title is always upper-cased
            title = modified_title[0].upper() + modified_title[1:]
        except Exception as e:
            reflector_logger.info(
                f"Failed to ensure casing on {title=} " f"with exception : {str(e)}"
            )

        return title

    def trim_title(self, title: str) -> str:
        """
        List of manual trimming to the title.

        Longer titles are prone to run into A prefix of phrases that don't
        really add any descriptive information and in some cases, this
        behaviour can be repeated for several consecutive topics. Trim the
        titles to maintain quality of titles.
        """
        phrases_to_remove = ["Discussing", "Discussion on", "Discussion about"]
        try:
            pattern = (
                r"\b(?:"
                + "|".join(re.escape(phrase) for phrase in phrases_to_remove)
                + r")\b"
            )
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)
        except Exception as e:
            reflector_logger.info(
                f"Failed to trim {title=} " f"with exception : {str(e)}"
            )
        return title

    async def _generate(
        self, prompt: str, gen_schema: dict | None, gen_cfg: dict | None, **kwargs
    ) -> str:
        raise NotImplementedError

    async def _completion(
        self, messages: list, logger: reflector_logger, **kwargs
    ) -> dict:
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

    def text_token_threshold(self, task_params: TaskParams | None) -> int:
        """
        Choose the token size to set as the threshold to pack the LLM calls
        """
        buffer_token_size = 100
        default_output_tokens = 1000
        context_window = self.tokenizer.model_max_length
        tokens = self.tokenizer.tokenize(
            self.create_prompt(instruct=task_params.instruct, text="")
        )
        threshold = context_window - len(tokens) - buffer_token_size
        if task_params.gen_cfg:
            threshold -= task_params.gen_cfg.max_new_tokens
        else:
            threshold -= default_output_tokens
        return threshold

    def split_corpus(
        self,
        corpus: str,
        task_params: TaskParams,
        token_threshold: int | None = None,
    ) -> list[str]:
        """
        Split the input to the LLM due to CUDA memory limitations and LLM context window
        restrictions.

        Accumulate tokens from full sentences till threshold and yield accumulated
        tokens. Reset accumulation when threshold is reached and repeat process.
        """
        if not token_threshold:
            token_threshold = self.text_token_threshold(task_params=task_params)

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

    def create_prompt(self, instruct: str, text: str) -> str:
        """
        Create a consumable prompt based on the prompt template
        """
        return self.template.format(instruct=instruct, text=text)
