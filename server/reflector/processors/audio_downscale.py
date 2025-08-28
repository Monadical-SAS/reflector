from typing import Optional

import av
from av.audio.resampler import AudioResampler

from reflector.processors.base import Processor


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


class AudioDownscaleProcessor(Processor):
    """
    Downscale audio frames to 16kHz mono format
    """

    INPUT_TYPE = av.AudioFrame
    OUTPUT_TYPE = av.AudioFrame

    def __init__(self, target_rate: int = 16000, target_layout: str = "mono", **kwargs):
        super().__init__(**kwargs)
        self.target_rate = target_rate
        self.target_layout = target_layout
        self.resampler: Optional[AudioResampler] = None
        self.needs_resampling: Optional[bool] = None

    async def _push(self, data: av.AudioFrame):
        if self.needs_resampling is None:
            self.needs_resampling = (
                data.sample_rate != self.target_rate
                or data.layout.name != self.target_layout
            )

            if self.needs_resampling:
                self.resampler = AudioResampler(
                    format="s16", layout=self.target_layout, rate=self.target_rate
                )

        if not self.needs_resampling or not self.resampler:
            await self.emit(data)
            return

        resampled_frames = self.resampler.resample(copy_frame(data))
        for resampled_frame in resampled_frames:
            await self.emit(resampled_frame)

    async def _flush(self):
        if self.needs_resampling and self.resampler:
            final_frames = self.resampler.resample(None)
            for frame in final_frames:
                await self.emit(frame)
