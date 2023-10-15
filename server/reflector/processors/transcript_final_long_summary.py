import nltk
from reflector.llm import LLM, LLMTaskParams
from reflector.processors.base import Processor
from reflector.processors.types import FinalLongSummary, TitleSummary


class TranscriptFinalLongSummaryProcessor(Processor):
    """
    Get the final long summary
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalLongSummary

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance(model_name="HuggingFaceH4/zephyr-7b-alpha")

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_bullet_summary(self, text: str) -> str:
        params = LLMTaskParams.get_instance("bullet_summary").task_params
        chunks = list(self.llm.split_corpus(corpus=text, task_params=params))

        bullet_summary = ""
        for chunk in chunks:
            prompt = self.llm.create_prompt(instruct=params.instruct, text=chunk)
            summary_result = await self.llm.generate(
                prompt=prompt,
                gen_schema=params.gen_schema,
                gen_cfg=params.gen_cfg,
                logger=self.logger,
            )
            bullet_summary += summary_result["long_summary"]
        return bullet_summary

    async def get_merged_summary(self, text: str) -> str:
        params = LLMTaskParams.get_instance("merged_summary").task_params
        chunks = list(self.llm.split_corpus(corpus=text, task_params=params))

        merged_summary = ""
        for chunk in chunks:
            prompt = self.llm.create_prompt(instruct=params.instruct, text=chunk)
            summary_result = await self.llm.generate(
                prompt=prompt,
                gen_schema=params.gen_schema,
                gen_cfg=params.gen_cfg,
                logger=self.logger,
            )
            merged_summary += summary_result["long_summary"]
        return merged_summary

    async def get_long_summary(self, text: str) -> str:
        """
        Generate a long version of the final summary
        """
        bullet_summary = await self.get_bullet_summary(text)
        merged_summary = await self.get_merged_summary(bullet_summary)

        return merged_summary

    def sentence_tokenize(self, text: str) -> [str]:
        return nltk.sent_tokenize(text)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_summaries = " ".join([chunk.summary for chunk in self.chunks])
        long_summary = await self.get_long_summary(accumulated_summaries)

        # Format the output as much as possible to be handled
        # by front-end for displaying
        summary_sentences = []
        for sentence in self.sentence_tokenize(long_summary):
            sentence = str(sentence).strip()
            if sentence.startswith("- "):
                sentence.replace("- ", "* ")
            elif not sentence.startswith("*"):
                sentence = "* " + sentence
            sentence += " \n"
            summary_sentences.append(sentence)

        formatted_long_summary = "".join(summary_sentences)

        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        final_long_summary = FinalLongSummary(
            long_summary=formatted_long_summary,
            duration=duration,
        )
        await self.emit(final_long_summary)
