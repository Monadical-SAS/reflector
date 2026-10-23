import io
import zipfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.db.recordings import Recording, recordings_controller
from reflector.db.transcripts import SourceKind, transcripts_controller


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


async def _create_transcript_with_tracks(user_id, share_mode):
    recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="recording",
            recorded_at=datetime.now(timezone.utc),
            track_keys=["recording/track-a.webm", "recording/track-b.webm"],
        )
    )
    return await transcripts_controller.add(
        name="Room meeting",
        source_kind=SourceKind.ROOM,
        user_id=user_id,
        share_mode=share_mode,
        recording_id=recording.id,
    )


@pytest.fixture
def mock_source_storage():
    storage = MagicMock()
    storage.get_file = AsyncMock(return_value=b"track-bytes")
    with patch(
        "reflector.views.transcripts_download.get_source_storage",
        return_value=storage,
    ):
        yield storage


def _zip_names(response):
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return zf.namelist()


@pytest.mark.asyncio
async def test_download_zip_owner_gets_tracks(
    authenticated_client, client, mock_source_storage
):
    transcript = await _create_transcript_with_tracks("randomuserid", "semi-private")
    response = await client.get(f"/transcripts/{transcript.id}/download/zip")
    assert response.status_code == 200
    names = _zip_names(response)
    assert "metadata.json" in names
    assert "tracks/track-a.webm" in names
    assert "tracks/track-b.webm" in names


@pytest.mark.asyncio
async def test_download_zip_non_owner_gets_reduced_zip(
    authenticated_client2, client, mock_source_storage
):
    transcript = await _create_transcript_with_tracks("randomuserid", "semi-private")
    response = await client.get(f"/transcripts/{transcript.id}/download/zip")
    assert response.status_code == 200
    names = _zip_names(response)
    assert "metadata.json" in names
    assert not any(n.startswith("tracks/") for n in names)
    assert "cloud_video.mp4" not in names
    mock_source_storage.get_file.assert_not_called()


@pytest.mark.asyncio
async def test_download_zip_non_owner_private_forbidden(
    authenticated_client2, client, mock_source_storage
):
    transcript = await _create_transcript_with_tracks("randomuserid", "private")
    response = await client.get(f"/transcripts/{transcript.id}/download/zip")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_download_zip_anonymous_transcript_gets_reduced_zip(
    authenticated_client, client, mock_source_storage
):
    transcript = await _create_transcript_with_tracks(None, "private")
    response = await client.get(f"/transcripts/{transcript.id}/download/zip")
    assert response.status_code == 200
    names = _zip_names(response)
    assert "metadata.json" in names
    assert not any(n.startswith("tracks/") for n in names)
