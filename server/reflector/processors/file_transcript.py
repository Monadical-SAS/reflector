from prometheus_client import Counter, Histogram

from reflector.processors.base import Processor
from reflector.processors.types import Transcript


class FileTranscriptInput:
    """Input for file transcription containing audio URL and language settings"""

    def __init__(self, audio_url: str, language: str = "en"):
        self.audio_url = audio_url
        self.language = language


class FileTranscriptProcessor(Processor):
    """
    Transcript complete audio files from URL
    """

    INPUT_TYPE = FileTranscriptInput
    OUTPUT_TYPE = Transcript

    m_transcript = Histogram(
        "file_transcript",
        "Time spent in FileTranscript.transcript",
        ["backend"],
    )
    m_transcript_call = Counter(
        "file_transcript_call",
        "Number of calls to FileTranscript.transcript",
        ["backend"],
    )
    m_transcript_success = Counter(
        "file_transcript_success",
        "Number of successful calls to FileTranscript.transcript",
        ["backend"],
    )
    m_transcript_failure = Counter(
        "file_transcript_failure",
        "Number of failed calls to FileTranscript.transcript",
        ["backend"],
    )

    def __init__(self, *args, **kwargs):
        name = self.__class__.__name__
        self.m_transcript = self.m_transcript.labels(name)
        self.m_transcript_call = self.m_transcript_call.labels(name)
        self.m_transcript_success = self.m_transcript_success.labels(name)
        self.m_transcript_failure = self.m_transcript_failure.labels(name)
        super().__init__(*args, **kwargs)

    async def _push(self, data: FileTranscriptInput):
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

    async def _transcript(self, data: FileTranscriptInput):
        raise NotImplementedError
