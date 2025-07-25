"""
Tests for S3 temporary file context manager.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from reflector.utils.s3_temp_file import S3TemporaryFile


@pytest.mark.asyncio
async def test_successful_upload_and_cleanup():
    """Test that file is uploaded and cleaned up on success."""
    # Mock storage
    mock_storage = Mock()
    mock_storage.put_file = AsyncMock()
    mock_storage.get_file_url = AsyncMock(return_value="https://example.com/file.wav")
    mock_storage.delete_file = AsyncMock()

    # Use context manager
    async with S3TemporaryFile(mock_storage, "test/file.wav") as s3_file:
        url = await s3_file.upload(b"test data")
        assert url == "https://example.com/file.wav"
        assert s3_file.url == "https://example.com/file.wav"

    # Verify operations
    mock_storage.put_file.assert_called_once_with("test/file.wav", b"test data")
    mock_storage.get_file_url.assert_called_once_with("test/file.wav")
    mock_storage.delete_file.assert_called_once_with("test/file.wav")


@pytest.mark.asyncio
async def test_cleanup_on_exception():
    """Test that cleanup happens even when an exception occurs."""
    # Mock storage
    mock_storage = Mock()
    mock_storage.put_file = AsyncMock()
    mock_storage.get_file_url = AsyncMock(return_value="https://example.com/file.wav")
    mock_storage.delete_file = AsyncMock()

    # Use context manager with exception
    with pytest.raises(ValueError):
        async with S3TemporaryFile(mock_storage, "test/file.wav") as s3_file:
            await s3_file.upload(b"test data")
            raise ValueError("Simulated error during processing")

    # Verify cleanup still happened
    mock_storage.delete_file.assert_called_once_with("test/file.wav")


@pytest.mark.asyncio
async def test_no_cleanup_if_not_uploaded():
    """Test that cleanup is skipped if file was never uploaded."""
    # Mock storage
    mock_storage = Mock()
    mock_storage.delete_file = AsyncMock()

    # Use context manager without uploading
    async with S3TemporaryFile(mock_storage, "test/file.wav"):
        pass  # Don't upload anything

    # Verify no cleanup attempted
    mock_storage.delete_file.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_failure_is_logged_not_raised():
    """Test that cleanup failures are logged but don't raise exceptions."""
    # Mock storage
    mock_storage = Mock()
    mock_storage.put_file = AsyncMock()
    mock_storage.get_file_url = AsyncMock(return_value="https://example.com/file.wav")
    mock_storage.delete_file = AsyncMock(side_effect=Exception("Delete failed"))

    # Use context manager - should not raise
    async with S3TemporaryFile(mock_storage, "test/file.wav") as s3_file:
        await s3_file.upload(b"test data")

    # Verify delete was attempted (3 times due to retry)
    assert mock_storage.delete_file.call_count == 3


@pytest.mark.asyncio
async def test_upload_retry_on_failure():
    """Test that upload is retried on failure."""
    # Mock storage with failures then success
    mock_storage = Mock()
    mock_storage.put_file = AsyncMock(
        side_effect=[Exception("Network error"), None]  # Fail once, then succeed
    )
    mock_storage.get_file_url = AsyncMock(return_value="https://example.com/file.wav")
    mock_storage.delete_file = AsyncMock()

    # Use context manager
    async with S3TemporaryFile(mock_storage, "test/file.wav") as s3_file:
        url = await s3_file.upload(b"test data")
        assert url == "https://example.com/file.wav"

    # Verify upload was retried
    assert mock_storage.put_file.call_count == 2


@pytest.mark.asyncio
async def test_delete_retry_on_failure():
    """Test that delete is retried on failure."""
    # Mock storage
    mock_storage = Mock()
    mock_storage.put_file = AsyncMock()
    mock_storage.get_file_url = AsyncMock(return_value="https://example.com/file.wav")
    mock_storage.delete_file = AsyncMock(
        side_effect=[Exception("Network error"), None]  # Fail once, then succeed
    )

    # Use context manager
    async with S3TemporaryFile(mock_storage, "test/file.wav") as s3_file:
        await s3_file.upload(b"test data")

    # Verify delete was retried
    assert mock_storage.delete_file.call_count == 2


@pytest.mark.asyncio
async def test_properties_before_upload():
    """Test that properties work correctly before upload."""
    mock_storage = Mock()

    async with S3TemporaryFile(mock_storage, "test/file.wav") as s3_file:
        assert s3_file.url is None
        assert s3_file.uploaded is False
