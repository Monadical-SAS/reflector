from typing import Optional

import av

from reflector.processors.audio_chunker import AudioChunkerProcessor
from reflector.processors.audio_chunker_auto import AudioChunkerAutoProcessor


class AudioChunkerFramesProcessor(AudioChunkerProcessor):
    """
    Simple frame-based audio chunker that emits chunks after a fixed number of frames
    """

    def __init__(self, max_frames=256, **kwargs):
        super().__init__(**kwargs)
        self.max_frames = max_frames

    async def _chunk(self, data: av.AudioFrame) -> Optional[list[av.AudioFrame]]:
        self.frames.append(data)
        if len(self.frames) >= self.max_frames:
            frames_to_emit = self.frames[:]
            self.frames = []
            return frames_to_emit

        return None

    async def _flush(self):
        frames = self.frames[:]
        self.frames = []
        if frames:
            await self.emit(frames)


AudioChunkerAutoProcessor.register("frames", AudioChunkerFramesProcessor)
