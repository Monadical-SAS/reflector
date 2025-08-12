from reflector.processors.base import Processor
from reflector.processors.types import DiarizationSegment


class FileDiarizationInput:
    """Input for file diarization containing audio URL"""

    def __init__(self, audio_url: str):
        self.audio_url = audio_url


class FileDiarizationOutput:
    """Output for file diarization containing speaker segments"""

    def __init__(self, diarization: list[DiarizationSegment]):
        self.diarization = diarization


class FileDiarizationProcessor(Processor):
    """
    Diarize complete audio files from URL
    """

    INPUT_TYPE = FileDiarizationInput
    OUTPUT_TYPE = FileDiarizationOutput

    m_diarization = Histogram(
        "file_diarization",
        "Time spent in FileDiarization.diarize",
        ["backend"],
    )
    m_diarization_call = Counter(
        "file_diarization_call",
        "Number of calls to FileDiarization.diarize",
        ["backend"],
    )
    m_diarization_success = Counter(
        "file_diarization_success",
        "Number of successful calls to FileDiarization.diarize",
        ["backend"],
    )
    m_diarization_failure = Counter(
        "file_diarization_failure",
        "Number of failed calls to FileDiarization.diarize",
        ["backend"],
    )

    def __init__(self, *args, **kwargs):
        name = self.__class__.__name__
        self.m_diarization = self.m_diarization.labels(name)
        self.m_diarization_call = self.m_diarization_call.labels(name)
        self.m_diarization_success = self.m_diarization_success.labels(name)
        self.m_diarization_failure = self.m_diarization_failure.labels(name)
        super().__init__(*args, **kwargs)

    async def _push(self, data: FileDiarizationInput):
        try:
            self.m_diarization_call.inc()
            with self.m_diarization.time():
                result = await self._diarize(data)
            self.m_diarization_success.inc()
            if result:
                await self.emit(result)
        except Exception:
            self.m_diarization_failure.inc()
            raise

    async def _diarize(self, data: FileDiarizationInput):
        raise NotImplementedError
