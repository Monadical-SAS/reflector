import json
from pathlib import Path

from reflector.processors.base import Processor
from reflector.processors.types import TitleSummary
from reflector.utils.audio_waveform import get_audio_waveform


class AudioWaveformProcessor(Processor):
    """
    Write the waveform for the final audio
    """

    INPUT_TYPE = TitleSummary

    def __init__(self, audio_path: Path | str, waveform_path: str, **kwargs):
        super().__init__(**kwargs)
        if isinstance(audio_path, str):
            audio_path = Path(audio_path)
        if audio_path.suffix not in (".mp3", ".wav"):
            raise ValueError("Only mp3 and wav files are supported")
        self.audio_path = audio_path
        self.waveform_path = waveform_path

    async def _flush(self):
        self.waveform_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info("Waveform Processing Started")
        waveform = get_audio_waveform(path=self.audio_path, segments_count=255)

        with open(self.waveform_path, "w") as fd:
            json.dump(waveform, fd)
        self.logger.info("Waveform Processing Finished")
        await self.emit(waveform, name="waveform")

    async def _push(_self, _data):
        return
