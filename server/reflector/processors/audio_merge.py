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

    def __init__(self, downsample_to_16k_mono: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.downsample_to_16k_mono = downsample_to_16k_mono

    async def _push(self, data: list[av.AudioFrame]):
        if not data:
            return

        # get audio information from first frame
        frame = data[0]
        original_channels = len(frame.layout.channels)
        original_sample_rate = frame.sample_rate
        original_sample_width = frame.format.bytes

        # determine output parameters
        if self.downsample_to_16k_mono:
            output_sample_rate = 16000
            output_channels = 1
            output_sample_width = 2  # 16-bit = 2 bytes
        else:
            output_sample_rate = original_sample_rate
            output_channels = original_channels
            output_sample_width = original_sample_width

        # create audio file
        uu = uuid4().hex
        fd = io.BytesIO()

        out_container = av.open(fd, "w", format="wav")
        out_stream = out_container.add_stream("pcm_s16le", rate=output_sample_rate)

        if self.downsample_to_16k_mono:
            # Configure resampler for downsampling to mono 16kHz
            out_stream.layout = "mono"

        if self.downsample_to_16k_mono:
            # Create a resampler for downsampling to mono 16kHz
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)

            for frame in data:
                # Resample and convert to mono
                resampled_frames = resampler.resample(frame)
                for resampled_frame in resampled_frames:
                    for packet in out_stream.encode(resampled_frame):
                        out_container.mux(packet)

            # Flush the resampler
            final_frames = resampler.resample(None)
            for final_frame in final_frames:
                for packet in out_stream.encode(final_frame):
                    out_container.mux(packet)
        else:
            # Use original frames
            for frame in data:
                for packet in out_stream.encode(frame):
                    out_container.mux(packet)

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
