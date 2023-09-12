import re

import nltk

from reflector.llm import LLM, LLMTaskParams
from reflector.processors.base import Processor
from reflector.processors.types import TitleSummary, Transcript


class TranscriptTopicDetectorProcessor(Processor):
    """
    Detect topic and summary from the transcript
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = TitleSummary
    TASK = "topic"

    def __init__(self, min_transcript_length: int = 750, **kwargs):
        super().__init__(**kwargs)
        self.transcript = None
        self.min_transcript_length = min_transcript_length
        self.llm = LLM.get_instance()
        self.params = LLMTaskParams.get_instance(self.TASK).task_params
        self.whitelisted_pos_tags = [
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

    async def _warmup(self):
        await self.llm.warmup(logger=self.logger)

    async def _push(self, data: Transcript):
        if self.transcript is None:
            self.transcript = data
        else:
            self.transcript.merge(data)
        text_length = len(self.transcript.text)
        required_length = self.min_transcript_length
        if text_length <= required_length:
            self.logger.info(f"Topic detector {text_length}/{required_length}")
            return
        await self.flush()

    async def get_topic(self, text: str) -> dict:
        """
        Generate a topic and description for a transcription excerpt
        """
        prompt = self.llm.create_prompt(instruct=self.params.instruct, text=text)
        topic_result = await self.llm.generate(
            prompt=prompt,
            gen_schema=self.params.gen_schema,
            gen_cfg=self.params.gen_cfg,
            logger=self.logger,
        )
        return topic_result

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

        # If at all there is an exception, do not block other reflector
        # processes. Return the LLM generated title, at the least.
        try:
            for word, pos in pos_tags:
                if pos in self.whitelisted_pos_tags and word[0].islower():
                    camel_cased.append(word[0].upper() + word[1:])
                else:
                    camel_cased.append(word)
            modified_title = " ".join(camel_cased)

            # The result can have words in braces with additional space.
            # Change ( ABC ), [ ABC ], etc. ==> (ABC), [ABC], etc.
            pattern = r"(?<=[\[\{\(])\s+|\s+(?=[\]\}\)])"
            title = re.sub(pattern, "", modified_title)
        except Exception as e:
            self.logger.info(
                f"Failed to ensure casing on {title=} " f"with exception : {str(e)}"
            )

        return title

    async def _flush(self):
        if not self.transcript:
            return

        text = self.transcript.text
        self.logger.info(f"Topic detector got {len(text)} length transcript")
        topic_result = await self.get_topic(text=text)

        summary = TitleSummary(
            title=self.ensure_casing(topic_result["title"]),
            summary=topic_result["summary"],
            timestamp=self.transcript.timestamp,
            duration=self.transcript.duration,
            transcript=self.transcript,
        )
        self.transcript = None
        await self.emit(summary)
