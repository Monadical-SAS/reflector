from reflector.processors.base import Processor
import av
import wave
from pathlib import Path


class AudioFileWriterProcessor(Processor):
    """
    Write audio frames to a file.
    """

    INPUT_TYPE = av.AudioFrame
    OUTPUT_TYPE = av.AudioFrame

    def __init__(self, path: Path | str):
        super().__init__()
        if isinstance(path, str):
            path = Path(path)
        self.path = path
        self.fd = None

    async def _push(self, data: av.AudioFrame):
        if not self.fd:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.fd = wave.open(self.path.as_posix(), "wb")
            self.fd.setnchannels(len(data.layout.channels))
            self.fd.setsampwidth(data.format.bytes)
            self.fd.setframerate(data.sample_rate)
        self.fd.writeframes(data.to_ndarray().tobytes())
        await self.emit(data)

    async def _flush(self):
        if self.fd:
            self.fd.close()
            self.fd = None
