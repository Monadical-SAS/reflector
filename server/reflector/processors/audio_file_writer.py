from pathlib import Path

import av
from reflector.processors.base import Processor


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
        if path.suffix not in (".mp3", ".wav"):
            raise ValueError("Only mp3 and wav files are supported")
        self.path = path
        self.out_container = None
        self.out_stream = None

    async def _push(self, data: av.AudioFrame):
        if not self.out_container:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            suffix = self.path.suffix
            if suffix == ".mp3":
                self.out_container = av.open(self.path.as_posix(), "w", format="mp3")
                self.out_stream = self.out_container.add_stream(
                    "libmp3lame", rate=data.sample_rate
                )
            elif suffix == ".wav":
                self.out_container = av.open(self.path.as_posix(), "w", format="wav")
                self.out_stream = self.out_container.add_stream(
                    "pcm_s16le", rate=data.sample_rate
                )
            else:
                raise ValueError("Only mp3 and wav files are supported")
        for packet in self.out_stream.encode(data):
            self.out_container.mux(packet)
        await self.emit(data)

    async def _flush(self):
        if self.out_container:
            for packet in self.out_stream.encode():
                self.out_container.mux(packet)
            self.out_container.close()
            self.out_container = None
            self.out_stream = None
