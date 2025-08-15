import io
import wave
from time import monotonic_ns
from uuid import uuid4

import av
import torch
import torchaudio.functional

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
            # Process with torchaudio and write WAV directly
            all_audio_data = []
            for frame in data:
                audio_tensor = torch.from_numpy(frame.to_ndarray()).float()

                # Convert to mono if needed
                if audio_tensor.dim() == 2:
                    audio_tensor = audio_tensor.mean(dim=0, keepdim=True)
                elif audio_tensor.dim() == 1:
                    audio_tensor = audio_tensor.unsqueeze(0)

                all_audio_data.append(audio_tensor)

            # Concatenate and resample if needed
            full_audio = torch.cat(all_audio_data, dim=1)
            if original_sample_rate != 16000:
                full_audio = torchaudio.functional.resample(
                    full_audio, original_sample_rate, 16000
                )

            # Convert to int16 and write WAV directly
            audio_int16 = (full_audio * 32767).clamp(-32768, 32767).to(torch.int16)
            audio_bytes = audio_int16.numpy().tobytes()

            # Write WAV header directly
            with wave.open(fd, "wb") as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_bytes)
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
            timestamp=data[0].pts * data[0].time_base
            if data[0].pts and data[0].time_base
            else 0,
        )

        await self.emit(audiofile)
