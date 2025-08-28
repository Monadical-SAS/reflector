from typing import Optional

import av
from prometheus_client import Counter, Histogram

from reflector.processors.base import Processor


class AudioChunkerProcessor(Processor):
    """
    Base class for assembling audio frames into chunks
    """

    INPUT_TYPE = av.AudioFrame
    OUTPUT_TYPE = list[av.AudioFrame]

    m_chunk = Histogram(
        "audio_chunker",
        "Time spent in AudioChunker.chunk",
        ["backend"],
    )
    m_chunk_call = Counter(
        "audio_chunker_call",
        "Number of calls to AudioChunker.chunk",
        ["backend"],
    )
    m_chunk_success = Counter(
        "audio_chunker_success",
        "Number of successful calls to AudioChunker.chunk",
        ["backend"],
    )
    m_chunk_failure = Counter(
        "audio_chunker_failure",
        "Number of failed calls to AudioChunker.chunk",
        ["backend"],
    )

    def __init__(self, *args, **kwargs):
        name = self.__class__.__name__
        self.m_chunk = self.m_chunk.labels(name)
        self.m_chunk_call = self.m_chunk_call.labels(name)
        self.m_chunk_success = self.m_chunk_success.labels(name)
        self.m_chunk_failure = self.m_chunk_failure.labels(name)
        super().__init__(*args, **kwargs)
        self.frames: list[av.AudioFrame] = []

    async def _push(self, data: av.AudioFrame):
        """Process incoming audio frame"""
        # Validate audio format on first frame
        if len(self.frames) == 0:
            if data.sample_rate != 16000 or len(data.layout.channels) != 1:
                raise ValueError(
                    f"AudioChunkerProcessor expects 16kHz mono audio, got {data.sample_rate}Hz "
                    f"with {len(data.layout.channels)} channel(s). "
                    f"Use AudioDownscaleProcessor before this processor."
                )

        try:
            self.m_chunk_call.inc()
            with self.m_chunk.time():
                result = await self._chunk(data)
            self.m_chunk_success.inc()
            if result:
                await self.emit(result)
        except Exception:
            self.m_chunk_failure.inc()
            raise

    async def _chunk(self, data: av.AudioFrame) -> Optional[list[av.AudioFrame]]:
        """
        Process audio frame and return chunk when ready.
        Subclasses should implement their chunking logic here.
        """
        raise NotImplementedError

    async def _flush(self):
        """Flush any remaining frames when processing ends"""
        raise NotImplementedError
