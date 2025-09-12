"""
Tests for transcription Model API endpoints.

These tests are marked with the "model_api" group and will not run by default.
Run them with: pytest -m model_api tests/test_model_api_transcript.py

Required environment variables:
- TRANSCRIPT_URL: URL to the Model API endpoint (required)
- TRANSCRIPT_API_KEY: API key for authentication (optional)
- TRANSCRIPT_MODEL: Model name to use (optional, defaults to nvidia/parakeet-tdt-0.6b-v2)

Example with pytest (override default addopts to run ONLY model_api tests):
    TRANSCRIPT_URL=https://monadical-sas--reflector-transcriber-parakeet-web-dev.modal.run \
    TRANSCRIPT_API_KEY=your-api-key \
    uv run -m pytest -m model_api --no-cov tests/test_model_api_transcript.py

    # Or with completely clean options:
    uv run -m pytest -m model_api -o addopts="" tests/

Running Modal locally for testing:
    modal serve gpu/modal_deployments/reflector_transcriber_parakeet.py
    # This will give you a local URL like https://xxxxx--reflector-transcriber-parakeet-web-dev.modal.run to test against
"""

import os
import tempfile
from pathlib import Path

import httpx
import pytest

# Test audio file URL for testing
TEST_AUDIO_URL = (
    "https://reflector-github-pytest.s3.us-east-1.amazonaws.com/test_mathieu_hello.mp3"
)


def get_modal_transcript_url():
    """Get and validate the Modal transcript URL from environment."""
    url = os.environ.get("TRANSCRIPT_URL")
    if not url:
        pytest.skip(
            "TRANSCRIPT_URL environment variable is required for Model API tests"
        )
    return url


def get_auth_headers():
    """Get authentication headers if API key is available."""
    api_key = os.environ.get("TRANSCRIPT_API_KEY") or os.environ.get(
        "REFLECTOR_GPU_APIKEY"
    )
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


def get_model_name():
    """Get the model name from environment or use default."""
    return os.environ.get("TRANSCRIPT_MODEL", "nvidia/parakeet-tdt-0.6b-v2")


@pytest.mark.model_api
class TestModelAPITranscript:
    """Test suite for GPU Modal transcription endpoints."""

    def test_transcriptions_from_url(self):
        """Test the /v1/audio/transcriptions-from-url endpoint."""
        url = get_modal_transcript_url()
        headers = get_auth_headers()

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{url}/v1/audio/transcriptions-from-url",
                json={
                    "audio_file_url": TEST_AUDIO_URL,
                    "model": get_model_name(),
                    "language": "en",
                    "timestamp_offset": 0.0,
                },
                headers=headers,
            )

            assert response.status_code == 200, f"Request failed: {response.text}"
            result = response.json()

            # Verify response structure
            assert "text" in result
            assert "words" in result
            assert isinstance(result["text"], str)
            assert isinstance(result["words"], list)

            # Verify content is meaningful
            assert len(result["text"]) > 0, "Transcript text should not be empty"
            assert len(result["words"]) > 0, "Words list must not be empty"

            # Verify word structure
            for word in result["words"]:
                assert "word" in word
                assert "start" in word
                assert "end" in word
                assert isinstance(word["start"], (int, float))
                assert isinstance(word["end"], (int, float))
                assert word["start"] <= word["end"]

    def test_transcriptions_single_file(self):
        """Test the /v1/audio/transcriptions endpoint with a single file."""
        url = get_modal_transcript_url()
        headers = get_auth_headers()

        # Download test audio file to upload
        with httpx.Client(timeout=60.0) as client:
            audio_response = client.get(TEST_AUDIO_URL)
            audio_response.raise_for_status()

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_response.content)
                tmp_file_path = tmp_file.name

            try:
                # Upload the file for transcription
                with open(tmp_file_path, "rb") as f:
                    files = {"file": ("test_audio.mp3", f, "audio/mpeg")}
                    data = {
                        "model": get_model_name(),
                        "language": "en",
                        "batch": "false",
                    }

                    response = client.post(
                        f"{url}/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=headers,
                    )

                assert response.status_code == 200, f"Request failed: {response.text}"
                result = response.json()

                # Verify response structure for single file
                assert "text" in result
                assert "words" in result
                assert "filename" in result
                assert isinstance(result["text"], str)
                assert isinstance(result["words"], list)

                # Verify content
                assert len(result["text"]) > 0, "Transcript text should not be empty"

            finally:
                Path(tmp_file_path).unlink(missing_ok=True)

    def test_transcriptions_multiple_files(self):
        """Test the /v1/audio/transcriptions endpoint with multiple files (non-batch mode)."""
        url = get_modal_transcript_url()
        headers = get_auth_headers()

        # Create multiple test files (we'll use the same audio content for simplicity)
        with httpx.Client(timeout=60.0) as client:
            audio_response = client.get(TEST_AUDIO_URL)
            audio_response.raise_for_status()
            audio_content = audio_response.content

            temp_files = []
            try:
                # Create 3 temporary files
                for i in range(3):
                    tmp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    tmp_file.write(audio_content)
                    tmp_file.close()
                    temp_files.append(tmp_file.name)

                # Upload multiple files for transcription (non-batch)
                files = [
                    ("files", (f"test_audio_{i}.mp3", open(f, "rb"), "audio/mpeg"))
                    for i, f in enumerate(temp_files)
                ]
                data = {
                    "model": get_model_name(),
                    "language": "en",
                    "batch": "false",
                }

                response = client.post(
                    f"{url}/v1/audio/transcriptions",
                    files=files,
                    data=data,
                    headers=headers,
                )

                # Close file handles
                for _, file_tuple in files:
                    file_tuple[1].close()

                assert response.status_code == 200, f"Request failed: {response.text}"
                result = response.json()

                # Verify response structure for multiple files (non-batch)
                assert "results" in result
                assert isinstance(result["results"], list)
                assert len(result["results"]) == 3

                for idx, file_result in enumerate(result["results"]):
                    assert "text" in file_result
                    assert "words" in file_result
                    assert "filename" in file_result
                    assert isinstance(file_result["text"], str)
                    assert isinstance(file_result["words"], list)
                    assert len(file_result["text"]) > 0

            finally:
                for f in temp_files:
                    Path(f).unlink(missing_ok=True)

    def test_transcriptions_multiple_files_batch(self):
        """Test the /v1/audio/transcriptions endpoint with multiple files in batch mode."""
        url = get_modal_transcript_url()
        headers = get_auth_headers()

        # Create multiple test files
        with httpx.Client(timeout=60.0) as client:
            audio_response = client.get(TEST_AUDIO_URL)
            audio_response.raise_for_status()
            audio_content = audio_response.content

            temp_files = []
            try:
                # Create 3 temporary files
                for i in range(3):
                    tmp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    tmp_file.write(audio_content)
                    tmp_file.close()
                    temp_files.append(tmp_file.name)

                # Upload multiple files for batch transcription
                files = [
                    ("files", (f"test_audio_{i}.mp3", open(f, "rb"), "audio/mpeg"))
                    for i, f in enumerate(temp_files)
                ]
                data = {
                    "model": get_model_name(),
                    "language": "en",
                    "batch": "true",
                }

                response = client.post(
                    f"{url}/v1/audio/transcriptions",
                    files=files,
                    data=data,
                    headers=headers,
                )

                # Close file handles
                for _, file_tuple in files:
                    file_tuple[1].close()

                assert response.status_code == 200, f"Request failed: {response.text}"
                result = response.json()

                # Verify response structure for batch mode
                assert "results" in result
                assert isinstance(result["results"], list)
                assert len(result["results"]) == 3

                for idx, batch_result in enumerate(result["results"]):
                    assert "text" in batch_result
                    assert "words" in batch_result
                    assert "filename" in batch_result
                    assert isinstance(batch_result["text"], str)
                    assert isinstance(batch_result["words"], list)
                    assert len(batch_result["text"]) > 0

            finally:
                for f in temp_files:
                    Path(f).unlink(missing_ok=True)

    @pytest.mark.skipif(
        not "parakeet" in get_model_name(), reason="Parakeet only supports English"
    )
    def test_transcriptions_error_handling(self):
        """Test error handling for invalid requests."""
        url = get_modal_transcript_url()
        headers = get_auth_headers()

        with httpx.Client(timeout=60.0) as client:
            # Test with unsupported language
            response = client.post(
                f"{url}/v1/audio/transcriptions-from-url",
                json={
                    "audio_file_url": TEST_AUDIO_URL,
                    "model": get_model_name(),
                    "language": "fr",  # Parakeet only supports English
                    "timestamp_offset": 0.0,
                },
                headers=headers,
            )

            assert response.status_code == 400
            assert "only supports English" in response.text

    def test_transcriptions_with_timestamp_offset(self):
        """Test transcription with timestamp offset parameter."""
        url = get_modal_transcript_url()
        headers = get_auth_headers()

        with httpx.Client(timeout=60.0) as client:
            # Test with timestamp offset
            response = client.post(
                f"{url}/v1/audio/transcriptions-from-url",
                json={
                    "audio_file_url": TEST_AUDIO_URL,
                    "model": get_model_name(),
                    "language": "en",
                    "timestamp_offset": 10.0,  # Add 10 second offset
                },
                headers=headers,
            )

            assert response.status_code == 200, f"Request failed: {response.text}"
            result = response.json()

            # Verify response structure
            assert "text" in result
            assert "words" in result
            assert len(result["words"]) > 0, "Words list must not be empty"

            # Verify that timestamps have been offset
            for word in result["words"]:
                # All timestamps should be >= 10.0 due to offset
                assert (
                    word["start"] >= 10.0
                ), f"Word start time {word['start']} should be >= 10.0"
                assert (
                    word["end"] >= 10.0
                ), f"Word end time {word['end']} should be >= 10.0"
