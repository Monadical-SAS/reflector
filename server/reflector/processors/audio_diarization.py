from reflector.processors.base import Processor
from reflector.processors.types import AudioDiarizationInput, TitleSummary


class AudioDiarizationProcessor(Processor):
    INPUT_TYPE = AudioDiarizationInput
    OUTPUT_TYPE = TitleSummary

    async def _push(self, data: AudioDiarizationInput):
        try:
            self.logger.info("Diarization started", audio_file_url=data.audio_url)
            diarization = await self._diarize(data)
            self.logger.info("Diarization finished")
        except Exception:
            self.logger.exception("Diarization failed after retrying")
            raise

        # now reapply speaker to topics (if any)
        # topics is a list[BaseModel] with an attribute words
        # words is a list[BaseModel] with text, start and speaker attribute

        # mutate in place
        for topic in data.topics:
            for word in topic.transcript.words:
                for d in diarization:
                    if d["start"] <= word.start <= d["end"]:
                        word.speaker = d["speaker"]

        # emit them
        for topic in data.topics:
            await self.emit(topic)

    async def _diarize(self, data: AudioDiarizationInput):
        raise NotImplementedError
