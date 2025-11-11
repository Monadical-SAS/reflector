"""Tests for storage abstraction layer."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from reflector.storage.base import StoragePermissionError
from reflector.storage.storage_aws import AwsStorage


@pytest.mark.asyncio
async def test_aws_storage_stream_to_fileobj():
    """Test that AWS storage can stream directly to a file object without loading into memory."""
    # Setup
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock AWS response with streaming body
    mock_body = MagicMock()
    mock_body.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", b""])

    mock_response = {"Body": mock_body}
    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Patch the session client
    with patch.object(storage.session, "client", return_value=mock_client):
        # Create a file-like object to stream to
        output = io.BytesIO()

        # Act - stream to file object
        await storage.stream_to_fileobj("test-file.mp4", output, bucket="test-bucket")

        # Assert
        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="test-file.mp4"
        )

        # Check that data was written to output without being fully loaded in memory first
        output.seek(0)
        assert output.read() == b"chunk1chunk2"


@pytest.mark.asyncio
async def test_aws_storage_stream_to_fileobj_with_folder():
    """Test streaming with folder prefix in bucket name."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket/recordings",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    mock_body = MagicMock()
    mock_body.read = AsyncMock(side_effect=[b"data", b""])

    mock_response = {"Body": mock_body}
    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(storage.session, "client", return_value=mock_client):
        output = io.BytesIO()
        await storage.stream_to_fileobj("file.mp4", output, bucket="other-bucket")

        # Should use folder prefix from instance config
        mock_client.get_object.assert_called_once_with(
            Bucket="other-bucket", Key="recordings/file.mp4"
        )


@pytest.mark.asyncio
async def test_storage_base_class_stream_to_fileobj():
    """Test that base Storage class has stream_to_fileobj method."""
    from reflector.storage.base import Storage

    # Verify method exists in base class
    assert hasattr(Storage, "stream_to_fileobj")

    # Create a mock storage instance
    storage = MagicMock(spec=Storage)
    storage.stream_to_fileobj = AsyncMock()

    # Should be callable
    await storage.stream_to_fileobj("file.mp4", io.BytesIO())
    storage.stream_to_fileobj.assert_called_once()


@pytest.mark.asyncio
async def test_aws_storage_stream_closes_body_on_write_error():
    """Test that S3 body is properly closed even if write fails."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock body that will provide data
    mock_body = MagicMock()
    mock_body.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", b""])
    mock_body.close = MagicMock()

    mock_response = {"Body": mock_body}
    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Create a fileobj that fails on second write
    class FailingFileObj:
        def __init__(self):
            self.write_count = 0

        def write(self, data):
            self.write_count += 1
            if self.write_count == 2:
                raise IOError("Disk full")

        def flush(self):
            pass

    failing_fileobj = FailingFileObj()

    with patch.object(storage.session, "client", return_value=mock_client):
        with pytest.raises(IOError, match="Disk full"):
            await storage.stream_to_fileobj("test.mp4", failing_fileobj)

        # Verify body.close() was called even though write failed
        mock_body.close.assert_called_once()


@pytest.mark.asyncio
async def test_aws_storage_stream_flushes_fileobj_on_success():
    """Test that fileobj is flushed after successful streaming."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    mock_body = MagicMock()
    mock_body.read = AsyncMock(side_effect=[b"data", b""])
    mock_body.close = MagicMock()

    mock_response = {"Body": mock_body}
    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Track flush calls
    class TrackingFileObj(io.BytesIO):
        def __init__(self):
            super().__init__()
            self.flush_called = False

        def flush(self):
            self.flush_called = True
            super().flush()

    tracking_fileobj = TrackingFileObj()

    with patch.object(storage.session, "client", return_value=mock_client):
        await storage.stream_to_fileobj("test.mp4", tracking_fileobj)

        # Verify flush was called
        assert tracking_fileobj.flush_called
        # Verify body was closed
        mock_body.close.assert_called_once()


@pytest.mark.asyncio
async def test_aws_storage_handles_access_denied_error():
    """Test that AccessDenied errors are caught and wrapped in StoragePermissionError."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock ClientError with AccessDenied
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_client = AsyncMock()
    mock_client.put_object = AsyncMock(
        side_effect=ClientError(error_response, "PutObject")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(storage.session, "client", return_value=mock_client):
        with pytest.raises(StoragePermissionError) as exc_info:
            await storage.put_file("test.txt", b"data")

        # Verify error message contains expected information
        error_msg = str(exc_info.value)
        assert "AccessDenied" in error_msg
        assert "default bucket 'test-bucket'" in error_msg
        assert "S3 upload failed" in error_msg


@pytest.mark.asyncio
async def test_aws_storage_handles_no_such_bucket_error():
    """Test that NoSuchBucket errors are caught and wrapped in StoragePermissionError."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock ClientError with NoSuchBucket
    error_response = {
        "Error": {
            "Code": "NoSuchBucket",
            "Message": "The specified bucket does not exist",
        }
    }
    mock_client = AsyncMock()
    mock_client.delete_object = AsyncMock(
        side_effect=ClientError(error_response, "DeleteObject")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(storage.session, "client", return_value=mock_client):
        with pytest.raises(StoragePermissionError) as exc_info:
            await storage.delete_file("test.txt")

        # Verify error message contains expected information
        error_msg = str(exc_info.value)
        assert "NoSuchBucket" in error_msg
        assert "default bucket 'test-bucket'" in error_msg
        assert "S3 delete failed" in error_msg


@pytest.mark.asyncio
async def test_aws_storage_error_message_with_bucket_override():
    """Test that error messages correctly show overridden bucket."""
    storage = AwsStorage(
        aws_bucket_name="default-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock ClientError with AccessDenied
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(
        side_effect=ClientError(error_response, "GetObject")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(storage.session, "client", return_value=mock_client):
        with pytest.raises(StoragePermissionError) as exc_info:
            await storage.get_file("test.txt", bucket="override-bucket")

        # Verify error message shows overridden bucket, not default
        error_msg = str(exc_info.value)
        assert "overridden bucket 'override-bucket'" in error_msg
        assert "default-bucket" not in error_msg
        assert "S3 download failed" in error_msg


@pytest.mark.asyncio
async def test_aws_storage_reraises_non_handled_errors():
    """Test that non-AccessDenied/NoSuchBucket errors are re-raised as-is."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock ClientError with different error code
    error_response = {
        "Error": {"Code": "InternalError", "Message": "Internal Server Error"}
    }
    mock_client = AsyncMock()
    mock_client.put_object = AsyncMock(
        side_effect=ClientError(error_response, "PutObject")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(storage.session, "client", return_value=mock_client):
        # Should raise ClientError, not StoragePermissionError
        with pytest.raises(ClientError) as exc_info:
            await storage.put_file("test.txt", b"data")

        # Verify it's the original ClientError
        assert exc_info.value.response["Error"]["Code"] == "InternalError"


@pytest.mark.asyncio
async def test_aws_storage_presign_url_handles_errors():
    """Test that presigned URL generation handles permission errors."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock ClientError with AccessDenied during presign operation
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_client = AsyncMock()
    mock_client.generate_presigned_url = AsyncMock(
        side_effect=ClientError(error_response, "GeneratePresignedUrl")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(storage.session, "client", return_value=mock_client):
        with pytest.raises(StoragePermissionError) as exc_info:
            await storage.get_file_url("test.txt")

        # Verify error message
        error_msg = str(exc_info.value)
        assert "S3 presign failed" in error_msg
        assert "AccessDenied" in error_msg


@pytest.mark.asyncio
async def test_aws_storage_list_objects_handles_errors():
    """Test that list_objects handles permission errors."""
    storage = AwsStorage(
        aws_bucket_name="test-bucket",
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
    )

    # Mock ClientError during list operation
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_paginator = MagicMock()

    async def mock_paginate(*args, **kwargs):
        raise ClientError(error_response, "ListObjectsV2")
        yield  # Make it an async generator

    mock_paginator.paginate = mock_paginate

    mock_client = AsyncMock()
    mock_client.get_paginator = MagicMock(return_value=mock_paginator)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(storage.session, "client", return_value=mock_client):
        with pytest.raises(StoragePermissionError) as exc_info:
            await storage.list_objects(prefix="test/")

        error_msg = str(exc_info.value)
        assert "S3 list_objects failed" in error_msg
        assert "AccessDenied" in error_msg


def test_aws_storage_constructor_rejects_mixed_auth():
    """Test that constructor rejects both role_arn and access keys."""
    with pytest.raises(ValueError, match="cannot use both.*role_arn.*access keys"):
        AwsStorage(
            aws_bucket_name="test-bucket",
            aws_region="us-east-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            aws_role_arn="arn:aws:iam::123456789012:role/test-role",
        )
