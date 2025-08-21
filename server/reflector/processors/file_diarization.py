from pydantic import BaseModel

from reflector.processors.base import Processor
from reflector.processors.types import DiarizationSegment


class FileDiarizationInput(BaseModel):
    """Input for file diarization containing audio URL"""

    audio_url: str


class FileDiarizationOutput(BaseModel):
    """Output for file diarization containing speaker segments"""

    diarization: list[DiarizationSegment]


class FileDiarizationProcessor(Processor):
    """
    Diarize complete audio files from URL
    """

    INPUT_TYPE = FileDiarizationInput
    OUTPUT_TYPE = FileDiarizationOutput

    async def _push(self, data: FileDiarizationInput):
        result = await self._diarize(data)
        if result:
            await self.emit(result)

    async def _diarize(self, data: FileDiarizationInput):
        raise NotImplementedError
