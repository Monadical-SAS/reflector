"""
Tests for GPU Modal-compatible diarization endpoint (self-hosted service compatible shape).

Marked with the "gpu_modal" marker and skipped unless DIARIZATION_URL is provided.

Run with for local self-hosted server:
    REFLECTOR_GPU_APIKEY=dev-key \
    DIARIZATION_URL=http://localhost:8000 \
    uv run -m pytest -m gpu_modal --no-cov tests/test_gpu_modal_diarization.py
"""

import os

import httpx
import pytest

# Public test audio file hosted on S3 specifically for reflector pytests
TEST_AUDIO_URL = (
    "https://reflector-github-pytest.s3.us-east-1.amazonaws.com/test_mathieu_hello.mp3"
)


def get_modal_diarization_url():
    url = os.environ.get("DIARIZATION_URL")
    if not url:
        pytest.skip(
            "DIARIZATION_URL environment variable is required for GPU Modal tests"
        )
    return url


def get_auth_headers():
    api_key = os.environ.get("DIARIZATION_MODAL_API_KEY") or os.environ.get(
        "REFLECTOR_GPU_APIKEY"
    )
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


@pytest.mark.gpu_modal
class TestGPUModalDiarization:
    def test_diarize_from_url(self):
        url = get_modal_diarization_url()
        headers = get_auth_headers()

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{url}/diarize",
                params={"audio_file_url": TEST_AUDIO_URL, "timestamp": 0.0},
                headers=headers,
            )

            assert response.status_code == 200, f"Request failed: {response.text}"
            result = response.json()

            assert "diarization" in result
            assert isinstance(result["diarization"], list)
            assert len(result["diarization"]) > 0

            for seg in result["diarization"]:
                assert "start" in seg and "end" in seg and "speaker" in seg
                assert isinstance(seg["start"], (int, float))
                assert isinstance(seg["end"], (int, float))
                assert seg["start"] <= seg["end"]
