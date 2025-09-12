"""
Tests for translation Model API endpoint (self-hosted service compatible shape).

Marked with the "model_api" marker and skipped unless TRANSLATION_URL is provided
or we fallback to TRANSCRIPT_URL base (same host for self-hosted).

Run locally against self-hosted server:
    TRANSLATION_API_KEY=dev-key \
    TRANSLATION_URL=http://localhost:8000 \
    uv run -m pytest -m model_api --no-cov tests/test_model_api_translation.py
"""

import os

import httpx
import pytest


def get_translation_url():
    url = os.environ.get("TRANSLATION_URL") or os.environ.get("TRANSCRIPT_URL")
    if not url:
        pytest.skip(
            "TRANSLATION_URL or TRANSCRIPT_URL environment variable is required for Model API tests"
        )
    return url


def get_auth_headers():
    api_key = os.environ.get("TRANSLATION_API_KEY") or os.environ.get(
        "REFLECTOR_GPU_APIKEY"
    )
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


@pytest.mark.model_api
class TestModelAPITranslation:
    def test_translate_text(self):
        url = get_translation_url()
        headers = get_auth_headers()

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{url}/translate",
                params={"text": "The meeting will start in five minutes."},
                json={"source_language": "en", "target_language": "fr"},
                headers=headers,
            )

            assert response.status_code == 200, f"Request failed: {response.text}"
            data = response.json()

            assert "text" in data and isinstance(data["text"], dict)
            assert data["text"].get("en") == "The meeting will start in five minutes."
            assert isinstance(data["text"].get("fr", ""), str)
            assert len(data["text"]["fr"]) > 0
            assert data["text"]["fr"] == "La réunion commencera dans cinq minutes."
