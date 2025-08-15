import io
from time import monotonic_ns
from uuid import uuid4

import av
from av.audio.resampler import AudioResampler

from reflector.processors.base import Processor
from reflector.processors.types import AudioFile


def copy_frame(frame: av.AudioFrame) -> av.AudioFrame:
    frame_copy = frame.from_ndarray(
        frame.to_ndarray(),
        format=frame.format.name,
        layout=frame.layout.name,
    )
    frame_copy.sample_rate = frame.sample_rate
    frame_copy.pts = frame.pts
    frame_copy.time_base = frame.time_base
    return frame_copy


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

        # determine if we need processing
        needs_processing = self.downsample_to_16k_mono and (
            original_sample_rate != 16000 or original_channels != 1
        )

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

        if needs_processing:
            # Process with PyAV resampler
            out_container = av.open(fd, "w", format="wav")
            out_stream = out_container.add_stream("pcm_s16le", rate=16000)
            out_stream.layout = "mono"

            # Create resampler if needed
            resampler = None
            if original_sample_rate != 16000 or original_channels != 1:
                resampler = AudioResampler(format="s16", layout="mono", rate=16000)

            for frame in data:
                if resampler:
                    # Resample and convert to mono
                    # XXX for an unknown reason, if we don't use a copy of the frame, we get
                    # Invalid Argumment from resample. Debugging indicate that when a previous processor
                    # already used the frame (like AudioFileWriter), it make it invalid argument here.
                    resampled_frames = resampler.resample(copy_frame(frame))
                    for resampled_frame in resampled_frames:
                        for packet in out_stream.encode(resampled_frame):
                            out_container.mux(packet)
                else:
                    # Direct encoding without resampling
                    for packet in out_stream.encode(frame):
                        out_container.mux(packet)

            # Flush the encoder
            for packet in out_stream.encode(None):
                out_container.mux(packet)
            out_container.close()
        else:
            # Use PyAV for original frames (no processing needed)
            out_container = av.open(fd, "w", format="wav")
            out_stream = out_container.add_stream("pcm_s16le", rate=output_sample_rate)
            out_stream.layout = "mono" if output_channels == 1 else frame.layout

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
            timestamp=0,
        )

        await self.emit(audiofile)
