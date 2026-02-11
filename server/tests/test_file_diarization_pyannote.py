import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from reflector.processors.file_diarization_pyannote import (
    FileDiarizationPyannoteProcessor,
)

ORIGINAL_CONFIG = {
    "version": "3.1.0",
    "pipeline": {
        "name": "pyannote.audio.pipelines.SpeakerDiarization",
        "params": {
            "clustering": "AgglomerativeClustering",
            "embedding": "pyannote/wespeaker-voxceleb-resnet34-LM",
            "embedding_batch_size": 32,
            "embedding_exclude_overlap": True,
            "segmentation": "pyannote/segmentation-3.0",
            "segmentation_batch_size": 32,
        },
    },
    "params": {
        "clustering": {
            "method": "centroid",
            "min_cluster_size": 12,
            "threshold": 0.7045654963945799,
        },
        "segmentation": {"min_duration_off": 0.0},
    },
}


def _make_model_tarball(tarball_path: Path) -> None:
    """Create a fake model tarball matching real structure."""
    build_dir = tarball_path.parent / "_build"
    dirs = {
        "pyannote-speaker-diarization-3.1": {"config.yaml": yaml.dump(ORIGINAL_CONFIG)},
        "pyannote-segmentation-3.0": {
            "config.yaml": "model: {}\n",
            "pytorch_model.bin": b"fake",
        },
        "pyannote-wespeaker-voxceleb-resnet34-LM": {
            "config.yaml": "model: {}\n",
            "pytorch_model.bin": b"fake",
        },
    }
    for dirname, files in dirs.items():
        d = build_dir / dirname
        d.mkdir(parents=True, exist_ok=True)
        for fname, content in files.items():
            p = d / fname
            if isinstance(content, bytes):
                p.write_bytes(content)
            else:
                p.write_text(content)

    with tarfile.open(tarball_path, "w:gz") as tar:
        for dirname in dirs:
            tar.add(build_dir / dirname, arcname=dirname)


def _make_mock_processor() -> MagicMock:
    proc = MagicMock()
    proc.logger = MagicMock()
    return proc


class TestEnsureModel:
    """Test model download, extraction, and config patching."""

    def test_extracts_and_patches_config(self, tmp_path: Path) -> None:
        """Downloads tarball, extracts, patches config to local paths."""
        cache_dir = tmp_path / "cache"
        tarball_path = tmp_path / "model.tar.gz"
        _make_model_tarball(tarball_path)
        tarball_bytes = tarball_path.read_bytes()

        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [tarball_bytes]
        mock_response.raise_for_status = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value = mock_response

        proc = _make_mock_processor()
        proc._patch_config = lambda model_dir, cache_dir: (
            FileDiarizationPyannoteProcessor._patch_config(proc, model_dir, cache_dir)
        )

        with patch(
            "reflector.processors.file_diarization_pyannote.httpx.Client",
            return_value=mock_client,
        ):
            result = FileDiarizationPyannoteProcessor._ensure_model(
                proc, "http://fake/model.tar.gz", cache_dir
            )

        assert result == str(cache_dir / "pyannote-speaker-diarization-3.1")

        patched_config_path = (
            cache_dir / "pyannote-speaker-diarization-3.1" / "config.yaml"
        )
        with open(patched_config_path) as f:
            config = yaml.safe_load(f)

        assert config["pipeline"]["params"]["segmentation"] == str(
            cache_dir / "pyannote-segmentation-3.0" / "pytorch_model.bin"
        )
        assert config["pipeline"]["params"]["embedding"] == str(
            cache_dir / "pyannote-wespeaker-voxceleb-resnet34-LM" / "pytorch_model.bin"
        )
        # Non-patched fields preserved
        assert config["pipeline"]["params"]["clustering"] == "AgglomerativeClustering"
        assert config["params"]["clustering"]["threshold"] == pytest.approx(
            0.7045654963945799
        )

    def test_uses_cache_on_second_call(self, tmp_path: Path) -> None:
        """Skips download if model dir already exists."""
        cache_dir = tmp_path / "cache"
        model_dir = cache_dir / "pyannote-speaker-diarization-3.1"
        model_dir.mkdir(parents=True)
        (model_dir / "config.yaml").write_text("cached: true")

        proc = _make_mock_processor()

        with patch(
            "reflector.processors.file_diarization_pyannote.httpx.Client"
        ) as mock_httpx:
            result = FileDiarizationPyannoteProcessor._ensure_model(
                proc, "http://fake/model.tar.gz", cache_dir
            )
            mock_httpx.assert_not_called()

        assert result == str(model_dir)


class TestDiarizeSegmentParsing:
    """Test that pyannote output is correctly converted to DiarizationSegment."""

    @pytest.mark.asyncio
    async def test_parses_speaker_segments(self) -> None:
        proc = _make_mock_processor()

        mock_seg_0 = MagicMock()
        mock_seg_0.start = 0.123456
        mock_seg_0.end = 1.789012
        mock_seg_1 = MagicMock()
        mock_seg_1.start = 2.0
        mock_seg_1.end = 3.5

        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = [
            (mock_seg_0, None, "SPEAKER_00"),
            (mock_seg_1, None, "SPEAKER_01"),
        ]
        proc.diarization_pipeline = MagicMock(return_value=mock_diarization)

        mock_input = MagicMock()
        mock_input.audio_url = "http://fake/audio.mp3"

        mock_response = AsyncMock()
        mock_response.content = b"fake audio"
        mock_response.raise_for_status = MagicMock()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.get = AsyncMock(return_value=mock_response)

        with (
            patch(
                "reflector.processors.file_diarization_pyannote.httpx.AsyncClient",
                return_value=mock_async_client,
            ),
            patch(
                "reflector.processors.file_diarization_pyannote.torchaudio.load",
                return_value=(MagicMock(), 16000),
            ),
        ):
            result = await FileDiarizationPyannoteProcessor._diarize(proc, mock_input)

        assert len(result.diarization) == 2
        assert result.diarization[0] == {"start": 0.123, "end": 1.789, "speaker": 0}
        assert result.diarization[1] == {"start": 2.0, "end": 3.5, "speaker": 1}
