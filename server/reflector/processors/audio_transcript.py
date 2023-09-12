from prometheus_client import Counter, Histogram
from reflector.processors.base import Processor
from reflector.processors.types import AudioFile, Transcript


class AudioTranscriptProcessor(Processor):
    """
    Transcript audio file
    """

    INPUT_TYPE = AudioFile
    OUTPUT_TYPE = Transcript

    m_transcript = Histogram(
        "audio_transcript",
        "Time spent in AudioTranscript.transcript",
        ["backend"],
    )
    m_transcript_call = Counter(
        "audio_transcript_call",
        "Number of calls to AudioTranscript.transcript",
        ["backend"],
    )
    m_transcript_success = Counter(
        "audio_transcript_success",
        "Number of successful calls to AudioTranscript.transcript",
        ["backend"],
    )
    m_transcript_failure = Counter(
        "audio_transcript_failure",
        "Number of failed calls to AudioTranscript.transcript",
        ["backend"],
    )

    def __init__(self, *args, **kwargs):
        name = self.__class__.__name__
        self.m_transcript = self.m_transcript.labels(name)
        self.m_transcript_call = self.m_transcript_call.labels(name)
        self.m_transcript_success = self.m_transcript_success.labels(name)
        self.m_transcript_failure = self.m_transcript_failure.labels(name)
        super().__init__(*args, **kwargs)

    async def _push(self, data: AudioFile):
        try:
            self.m_transcript_call.inc()
            with self.m_transcript.time():
                result = await self._transcript(data)
            self.m_transcript_success.inc()
            if result:
                await self.emit(result)
        except Exception:
            self.m_transcript_failure.inc()
            raise
        finally:
            data.release()

    async def _transcript(self, data: AudioFile):
        raise NotImplementedError
