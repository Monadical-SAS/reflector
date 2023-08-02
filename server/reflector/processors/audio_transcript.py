from reflector.processors.base import Processor
from reflector.processors.types import AudioFile, Transcript


class AudioTranscriptProcessor(Processor):
    """
    Transcript audio file
    """

    INPUT_TYPE = AudioFile
    OUTPUT_TYPE = Transcript

    async def _push(self, data: AudioFile):
        try:
            result = await self._transcript(data)
            if result:
                await self.emit(result)
        finally:
            data.release()

    async def _transcript(self, data: AudioFile):
        raise NotImplementedError
