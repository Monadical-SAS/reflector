import io
from time import monotonic_ns
from uuid import uuid4

import av

from reflector.processors.base import Processor
from reflector.processors.types import AudioFile


class AudioMergeProcessor(Processor):
    """
    Merge audio frame into a single file
    """

    INPUT_TYPE = list[av.AudioFrame]
    OUTPUT_TYPE = AudioFile

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def _push(self, data: list[av.AudioFrame]):
        if not data:
            return

        # get audio information from first frame
        frame = data[0]
        output_channels = len(frame.layout.channels)
        output_sample_rate = frame.sample_rate
        output_sample_width = frame.format.bytes

        # create audio file
        uu = uuid4().hex
        fd = io.BytesIO()

        # Use PyAV to write frames
        out_container = av.open(fd, "w", format="wav")
        out_stream = out_container.add_stream("pcm_s16le", rate=output_sample_rate)
        out_stream.layout = frame.layout.name

        for frame in data:
            for packet in out_stream.encode(frame):
                out_container.mux(packet)

        # Flush the encoder
        for packet in out_stream.encode(None):
            out_container.mux(packet)
        out_container.close()

        fd.seek(0)

        # emit audio file
        audiofile = AudioFile(
            name=f"{monotonic_ns()}-{uu}.wav",
            fd=fd,
            sample_rate=output_sample_rate,
            channels=output_channels,
            sample_width=output_sample_width,
            timestamp=data[0].pts * data[0].time_base,
        )

        await self.emit(audiofile)
