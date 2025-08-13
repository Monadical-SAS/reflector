import os

import torch
import torchaudio
from pyannote.audio import Pipeline

from reflector.processors.audio_diarization import AudioDiarizationProcessor
from reflector.processors.audio_diarization_auto import AudioDiarizationAutoProcessor
from reflector.processors.types import AudioDiarizationInput, DiarizationSegment


class AudioDiarizationPyannoteProcessor(AudioDiarizationProcessor):
    """Local diarization processor using pyannote.audio library"""

    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-3.1",
        use_auth_token: str | None = None,
        device: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.use_auth_token = use_auth_token or os.environ.get("HF_TOKEN")

        # Auto-detect device if not specified
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self._pipeline = None

    @property
    def pipeline(self):
        """Lazy load the diarization pipeline"""
        if self._pipeline is None:
            self.logger.info(f"Loading pyannote diarization model: {self.model_name}")
            self._pipeline = Pipeline.from_pretrained(
                self.model_name, use_auth_token=self.use_auth_token
            )
            self._pipeline.to(torch.device(self.device))
            self.logger.info(f"Diarization model loaded on device: {self.device}")
        return self._pipeline

    async def _diarize(self, data: AudioDiarizationInput) -> list[DiarizationSegment]:
        """
        Perform speaker diarization on local audio file using pyannote.audio

        Args:
            data: AudioDiarizationInput containing audio_url (local file path) and topics

        Returns:
            List of DiarizationSegment with start, end, and speaker information
        """
        try:
            # Load audio file (audio_url is assumed to be a local file path)
            self.logger.info(f"Loading local audio file: {data.audio_url}")
            waveform, sample_rate = torchaudio.load(data.audio_url)

            # Prepare audio input for pyannote
            audio_input = {"waveform": waveform, "sample_rate": sample_rate}

            # Perform diarization
            self.logger.info("Running speaker diarization")
            diarization = self.pipeline(audio_input)

            # Convert pyannote diarization output to our format
            segments = []
            for segment, _, speaker in diarization.itertracks(yield_label=True):
                # Extract speaker number from label (e.g., "SPEAKER_00" -> 0)
                speaker_id = 0
                if speaker.startswith("SPEAKER_"):
                    try:
                        speaker_id = int(speaker.split("_")[-1])
                    except (ValueError, IndexError):
                        # Fallback to hash-based ID if parsing fails
                        speaker_id = hash(speaker) % 1000

                segments.append(
                    {
                        "start": round(segment.start, 3),
                        "end": round(segment.end, 3),
                        "speaker": speaker_id,
                    }
                )

            self.logger.info(f"Diarization completed with {len(segments)} segments")
            return segments

        except Exception as e:
            self.logger.exception(f"Diarization failed: {e}")
            raise


# Register the processor with the auto processor
AudioDiarizationAutoProcessor.register("pyannote", AudioDiarizationPyannoteProcessor)
