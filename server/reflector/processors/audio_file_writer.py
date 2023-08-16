from reflector.processors.base import Processor
import av
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
        self.out_container = None
        self.out_stream = None

    async def _push(self, data: av.AudioFrame):
        if not self.out_container:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.out_container = av.open(self.path.as_posix(), "w", format="wav")
            self.out_stream = self.out_container.add_stream(
                "pcm_s16le", rate=data.sample_rate
            )
            for packet in self.out_stream.encode(data):
                self.out_container.mux(packet)
        await self.emit(data)

    async def _flush(self):
        if self.out_container:
            for packet in self.out_stream.encode(None):
                self.out_container.mux(packet)
            self.out_container.close()
            self.out_container = None
            self.out_stream = None
