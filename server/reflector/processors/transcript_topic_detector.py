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

    def __init__(self, min_transcript_length: int = 500, **kwargs):
        super().__init__(**kwargs)
        self.transcript = None
        self.min_transcript_length = min_transcript_length
        self.llm = LLM.get_instance(model_name="lmsys/vicuna-13b-v1.5")
        self.params = LLMTaskParams.get_instance(self.TASK).task_params

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

    async def _flush(self):
        if not self.transcript:
            return

        text = self.transcript.text
        self.logger.info(f"Topic detector got {len(text)} length transcript")
        topic_result = await self.get_topic(text=text)

        summary = TitleSummary(
            title=topic_result["title"],
            summary=topic_result["summary"],
            timestamp=self.transcript.timestamp,
            duration=self.transcript.duration,
            transcript=self.transcript,
        )
        self.transcript = None
        await self.emit(summary)
