from reflector.processors.base import Processor
from reflector.processors.types import AudioFile
from pathlib import Path
import wave
import av


class AudioMergeProcessor(Processor):
    """
    Merge audio frame into a single file
    """

    INPUT_TYPE = list[av.AudioFrame]
    OUTPUT_TYPE = AudioFile

    async def _push(self, data: list[av.AudioFrame]):
        if not data:
            return

        # get audio information from first frame
        frame = data[0]
        channels = len(frame.layout.channels)
        sample_rate = frame.sample_rate
        sample_width = frame.format.bytes

        # create audio file
        from time import monotonic_ns
        from uuid import uuid4

        uu = uuid4().hex
        path = Path(f"audio_{monotonic_ns()}_{uu}.wav")
        with wave.open(path.as_posix(), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            for frame in data:
                wf.writeframes(frame.to_ndarray().tobytes())

        # emit audio file
        audiofile = AudioFile(
            path=path,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=sample_width,
            timestamp=data[0].pts * data[0].time_base,
        )
        await self.emit(audiofile)
