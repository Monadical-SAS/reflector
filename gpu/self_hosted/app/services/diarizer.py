import os
import threading

import torch
import torchaudio
from pyannote.audio import Pipeline


class PyannoteDiarizationService:
    def __init__(self):
        self._pipeline = None
        self._device = "cpu"
        self._lock = threading.Lock()

    def load(self):
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.environ.get("HF_TOKEN"),
        )
        self._pipeline.to(torch.device(self._device))

    def diarize_file(self, file_path: str, timestamp: float = 0.0) -> dict:
        if self._pipeline is None:
            self.load()
        waveform, sample_rate = torchaudio.load(file_path)
        with self._lock:
            diarization = self._pipeline(
                {"waveform": waveform, "sample_rate": sample_rate}
            )
        words = []
        for diarization_segment, _, speaker in diarization.itertracks(yield_label=True):
            words.append(
                {
                    "start": round(timestamp + diarization_segment.start, 3),
                    "end": round(timestamp + diarization_segment.end, 3),
                    "speaker": int(speaker[-2:])
                    if speaker and speaker[-2:].isdigit()
                    else 0,
                }
            )
        return {"diarization": words}
