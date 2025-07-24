"""
Local diarization processor using pyannote-audio
================================================

This processor runs diarization locally using pyannote-audio library.
It's designed for development and testing without requiring Modal infrastructure.
"""

import tempfile
from pathlib import Path
from typing import Dict, List

import httpx
from reflector.logger import logger
from reflector.processors.audio_diarization import AudioDiarizationProcessor
from reflector.processors.audio_diarization_auto import AudioDiarizationAutoProcessor
from reflector.processors.types import AudioDiarizationInput, TitleSummary


class AudioDiarizationLocalProcessor(AudioDiarizationProcessor):
    """Local diarization processor using pyannote-audio"""

    INPUT_TYPE = AudioDiarizationInput
    OUTPUT_TYPE = TitleSummary

    def __init__(self, model_name: str = "pyannote/speaker-diarization-3.1", **kwargs):
        super().__init__(**kwargs)
        self.model_name = model_name
        self._pipeline = None

    def _get_pipeline(self):
        """Lazy load the pyannote pipeline"""
        if self._pipeline is None:
            try:
                import torch
                from pyannote.audio import Pipeline
            except ImportError:
                raise ImportError(
                    "pyannote.audio is not installed. Install it with: "
                    "pip install pyannote.audio torch torchaudio"
                )

            self.logger.info(f"Loading pyannote model: {self.model_name}")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Check if we need HuggingFace token for this model
            import os
            hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
            
            if "pyannote" in self.model_name and not hf_token:
                self.logger.warning(
                    "No HuggingFace token found. Some pyannote models require authentication. "
                    "Set HF_TOKEN or HUGGINGFACE_TOKEN environment variable if needed."
                )
            
            try:
                self._pipeline = Pipeline.from_pretrained(
                    self.model_name,
                    use_auth_token=hf_token
                )
            except Exception as e:
                if "authentication" in str(e).lower():
                    raise RuntimeError(
                        f"Failed to load model {self.model_name}. "
                        "This model requires authentication. Please set HF_TOKEN environment variable."
                    )
                raise
            
            self._pipeline.to(torch.device(device))
            self.logger.info(f"Model loaded on device: {device}")

        return self._pipeline

    async def _diarize(self, data: AudioDiarizationInput):
        """Run diarization on the audio file"""
        # Download audio file if it's a URL
        audio_path = await self._get_audio_file(data.audio_url)
        
        try:
            # Run diarization
            self.logger.info("Starting local diarization")
            pipeline = self._get_pipeline()
            diarization = pipeline(str(audio_path))
            
            # Convert pyannote output to expected format
            segments = []
            for segment, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "start": round(segment.start, 3),
                    "end": round(segment.end, 3),
                    "speaker": int(speaker.split("_")[-1])  # Convert SPEAKER_00 to 0
                })
            
            self.logger.info(f"Diarization complete, found {len(segments)} segments")
            return segments
            
        finally:
            # Clean up downloaded file if it was temporary
            if str(audio_path).startswith("/tmp"):
                audio_path.unlink(missing_ok=True)

    async def _get_audio_file(self, audio_url: str) -> Path:
        """Download audio file from URL or return local path"""
        if audio_url.startswith(("http://", "https://")):
            # Download the file
            self.logger.info(f"Downloading audio from: {audio_url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url, timeout=300.0)
                response.raise_for_status()
                
                # Save to temporary file
                suffix = Path(audio_url).suffix or ".wav"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(response.content)
                    return Path(tmp.name)
        else:
            # Local file path
            return Path(audio_url)


# Register the local backend
AudioDiarizationAutoProcessor.register("local", AudioDiarizationLocalProcessor)