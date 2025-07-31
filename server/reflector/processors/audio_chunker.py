from reflector.processors.base import Processor
import av


class AudioChunkerProcessor(Processor):
    """
    Assemble audio frames into chunks
    """

    INPUT_TYPE = av.AudioFrame
    OUTPUT_TYPE = list[av.AudioFrame]

    def __init__(self, max_frames=256):
        super().__init__()
        self.frames: list[av.AudioFrame] = []
        self.max_frames = max_frames

    async def _push(self, data: av.AudioFrame):
        self.frames.append(data)
        if len(self.frames) >= self.max_frames:
            await self.flush()

    async def _flush(self):
        frames = self.frames[:]
        self.frames = []
        if frames:
            await self.emit(frames)
