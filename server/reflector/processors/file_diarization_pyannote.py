import os
import tarfile
import tempfile
from pathlib import Path

import httpx
import torch
import torchaudio
import yaml
from pyannote.audio import Pipeline

from reflector.processors.file_diarization import (
    FileDiarizationInput,
    FileDiarizationOutput,
    FileDiarizationProcessor,
)
from reflector.processors.file_diarization_auto import FileDiarizationAutoProcessor
from reflector.processors.types import DiarizationSegment

DEFAULT_MODEL_URL = "https://reflector-public.s3.us-east-1.amazonaws.com/pyannote-speaker-diarization-3.1.tar.gz"
DEFAULT_CACHE_DIR = "/tmp/pyannote-cache"


class FileDiarizationPyannoteProcessor(FileDiarizationProcessor):
    """File diarization using local pyannote.audio pipeline.

    Downloads model bundle from URL (or uses HuggingFace), runs speaker diarization.
    """

    def __init__(
        self,
        pyannote_model_url: str = DEFAULT_MODEL_URL,
        pyannote_model_name: str | None = None,
        pyannote_auth_token: str | None = None,
        pyannote_device: str | None = None,
        pyannote_cache_dir: str = DEFAULT_CACHE_DIR,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.auth_token = pyannote_auth_token or os.environ.get("HF_TOKEN")
        self.device = pyannote_device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        if pyannote_model_name:
            model_path = pyannote_model_name
        else:
            model_path = self._ensure_model(
                pyannote_model_url, Path(pyannote_cache_dir)
            )

        self.logger.info("Loading pyannote model", model=model_path, device=self.device)
        # from_pretrained needs a file path (config.yaml) for local models,
        # or a HuggingFace repo ID for remote ones
        config_path = Path(model_path) / "config.yaml"
        load_path = str(config_path) if config_path.is_file() else model_path
        self.diarization_pipeline = Pipeline.from_pretrained(
            load_path, use_auth_token=self.auth_token
        )
        self.diarization_pipeline.to(torch.device(self.device))

    def _ensure_model(self, model_url: str, cache_dir: Path) -> str:
        """Download and extract model bundle if not cached."""
        model_dir = cache_dir / "pyannote-speaker-diarization-3.1"
        config_path = model_dir / "config.yaml"

        if config_path.exists():
            self.logger.info("Using cached model", path=str(model_dir))
            return str(model_dir)

        cache_dir.mkdir(parents=True, exist_ok=True)
        tarball_path = cache_dir / "model.tar.gz"

        self.logger.info("Downloading model bundle", url=model_url)
        with httpx.Client() as client:
            with client.stream("GET", model_url, follow_redirects=True) as response:
                response.raise_for_status()
                with open(tarball_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        self.logger.info("Extracting model bundle")
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=cache_dir, filter="data")
        tarball_path.unlink()

        self._patch_config(model_dir, cache_dir)
        return str(model_dir)

    def _patch_config(self, model_dir: Path, cache_dir: Path) -> None:
        """Rewrite config.yaml to reference local model paths."""
        config_path = model_dir / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        config["pipeline"]["params"]["segmentation"] = str(
            cache_dir / "pyannote-segmentation-3.0" / "pytorch_model.bin"
        )
        config["pipeline"]["params"]["embedding"] = str(
            cache_dir / "pyannote-wespeaker-voxceleb-resnet34-LM" / "pytorch_model.bin"
        )

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        self.logger.info("Patched config.yaml with local model paths")

    async def _diarize(self, data: FileDiarizationInput) -> FileDiarizationOutput:
        self.logger.info("Downloading audio for diarization", audio_url=data.audio_url)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
            async with httpx.AsyncClient() as client:
                response = await client.get(data.audio_url, follow_redirects=True)
                response.raise_for_status()
                tmp.write(response.content)
                tmp.flush()

            waveform, sample_rate = torchaudio.load(tmp.name)

        audio_input = {"waveform": waveform, "sample_rate": sample_rate}
        diarization = self.diarization_pipeline(audio_input)

        segments: list[DiarizationSegment] = []
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            speaker_id = 0
            if speaker.startswith("SPEAKER_"):
                try:
                    speaker_id = int(speaker.split("_")[-1])
                except (ValueError, IndexError):
                    speaker_id = hash(speaker) % 1000

            segments.append(
                {
                    "start": round(segment.start, 3),
                    "end": round(segment.end, 3),
                    "speaker": speaker_id,
                }
            )

        self.logger.info("Diarization complete", segment_count=len(segments))
        return FileDiarizationOutput(diarization=segments)


FileDiarizationAutoProcessor.register("pyannote", FileDiarizationPyannoteProcessor)
