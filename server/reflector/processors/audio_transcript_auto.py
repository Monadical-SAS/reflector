from reflector.processors.base import Processor
from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_whisper import (
    AudioTranscriptWhisperProcessor,
)
from reflector.processors.types import AudioFile


class AudioTranscriptAutoProcessor(AudioTranscriptProcessor):
    BACKENDS = {
        "whisper": AudioTranscriptWhisperProcessor,
    }
    BACKEND_DEFAULT = "whisper"

    def __init__(self, backend=None, **kwargs):
        self.processor = self.BACKENDS[backend or self.BACKEND_DEFAULT]()
        super().__init__(**kwargs)

    def connect(self, processor: Processor):
        self.processor.connect(processor)

    def disconnect(self, processor: Processor):
        self.processor.disconnect(processor)

    def on(self, callback):
        self.processor.on(callback)

    def off(self, callback):
        self.processor.off(callback)

    async def _push(self, data: AudioFile):
        return await self.processor._push(data)

    async def _flush(self):
        return await self.processor._flush()
