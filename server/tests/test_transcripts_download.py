import io
import zipfile

import pytest


@pytest.mark.asyncio
async def test_download_zip_returns_valid_zip(
    authenticated_client, client, fake_transcript_with_topics
):
    """Test that the zip download endpoint returns a valid zip file."""
    transcript = fake_transcript_with_topics
    response = await client.get(f"/transcripts/{transcript.id}/download/zip")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    # Verify it's a valid zip
    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer) as zf:
        names = zf.namelist()
        assert "metadata.json" in names
        assert "audio.mp3" in names


@pytest.mark.asyncio
async def test_download_zip_requires_auth(client):
    """Test that zip download requires authentication."""
    response = await client.get("/transcripts/nonexistent/download/zip")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_download_zip_not_found(authenticated_client, client):
    """Test 404 for non-existent transcript."""
    response = await client.get("/transcripts/nonexistent-id/download/zip")
    assert response.status_code == 404
