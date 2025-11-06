"""
Tests for AWS Storage implementation - unified put_file and extended get_file_url
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.storage.storage_aws import AwsStorage


@pytest.fixture
def mock_aioboto3_session():
    """Mock aioboto3 session with client context manager"""
    session = MagicMock()
    mock_client = AsyncMock()

    # Mock the async context manager for session.client()
    async def async_enter(self):
        return mock_client

    async def async_exit(self, *args):
        pass

    session.client.return_value.__aenter__ = async_enter
    session.client.return_value.__aexit__ = async_exit

    return session, mock_client


@pytest.fixture
def aws_storage(mock_aioboto3_session):
    """Create AwsStorage instance with mocked session"""
    session, mock_client = mock_aioboto3_session

    with patch("reflector.storage.storage_aws.aioboto3.Session") as mock_session_class:
        mock_session_class.return_value = session

        storage = AwsStorage(
            aws_access_key_id="test_key_id",
            aws_secret_access_key="test_secret_key",
            aws_bucket_name="test-bucket",
            aws_region="us-east-1",
        )

        # Store mock_client for test assertions
        storage._mock_client = mock_client

        yield storage


@pytest.mark.asyncio
async def test_get_file_url_default_parameters(aws_storage):
    """Test get_file_url with default parameters (backwards compatibility)"""
    filename = "test/file.txt"
    expected_url = "https://test-bucket.s3.amazonaws.com/test/file.txt?signed=true"

    aws_storage._mock_client.generate_presigned_url.return_value = expected_url

    result = await aws_storage.get_file_url(filename)

    assert result == expected_url

    # Verify default parameters were used
    aws_storage._mock_client.generate_presigned_url.assert_called_once_with(
        "get_object", Params={"Bucket": "test-bucket", "Key": filename}, ExpiresIn=3600
    )


@pytest.mark.asyncio
async def test_get_file_url_custom_operation(aws_storage):
    """Test get_file_url with custom operation (e.g., put_object)"""
    filename = "upload/file.txt"
    expected_url = "https://test-bucket.s3.amazonaws.com/upload/file.txt?signed=true"

    aws_storage._mock_client.generate_presigned_url.return_value = expected_url

    result = await aws_storage.get_file_url(
        filename, operation="put_object", expires_in=7200
    )

    assert result == expected_url

    # Verify custom parameters were used
    aws_storage._mock_client.generate_presigned_url.assert_called_once_with(
        "put_object",
        Params={"Bucket": "test-bucket", "Key": filename},
        ExpiresIn=7200,
    )


@pytest.mark.asyncio
async def test_get_file_url_custom_expires_in(aws_storage):
    """Test get_file_url with custom expiration time"""
    filename = "test.txt"
    expected_url = "https://test-bucket.s3.amazonaws.com/test.txt?signed=true"

    aws_storage._mock_client.generate_presigned_url.return_value = expected_url

    result = await aws_storage.get_file_url(
        filename, operation="get_object", expires_in=1800
    )

    assert result == expected_url

    # Verify custom expiration was used
    call_args = aws_storage._mock_client.generate_presigned_url.call_args
    assert call_args[1]["ExpiresIn"] == 1800


@pytest.mark.asyncio
async def test_get_file_url_with_folder_prefix(aws_storage):
    """Test get_file_url with folder prefix in bucket name"""
    # Reinitialize with folder in bucket name
    with patch("reflector.storage.storage_aws.aioboto3.Session"):
        storage = AwsStorage(
            aws_access_key_id="test_key_id",
            aws_secret_access_key="test_secret_key",
            aws_bucket_name="test-bucket/prefix",
            aws_region="us-east-1",
        )

        session = MagicMock()
        mock_client = AsyncMock()

        async def async_enter(self):
            return mock_client

        async def async_exit(self, *args):
            pass

        session.client.return_value.__aenter__ = async_enter
        session.client.return_value.__aexit__ = async_exit
        storage.session = session

        expected_url = (
            "https://test-bucket.s3.amazonaws.com/prefix/file.txt?signed=true"
        )
        mock_client.generate_presigned_url.return_value = expected_url

        result = await storage.get_file_url(
            "file.txt", operation="get_object", expires_in=1800
        )

        assert result == expected_url

        # Verify folder prefix is added to key
        call_args = mock_client.generate_presigned_url.call_args
        assert call_args[1]["Params"]["Key"] == "prefix/file.txt"


@pytest.mark.asyncio
async def test_put_file_with_bytes(aws_storage):
    """Test put_file with bytes data uses put_object"""
    data = b"test file content"
    filename = "test/file.txt"

    aws_storage._mock_client.generate_presigned_url.return_value = (
        "https://test-bucket.s3.amazonaws.com/test/file.txt?signed=true"
    )

    result = await aws_storage.put_file(filename, data)

    aws_storage._mock_client.put_object.assert_called_once()
    call_kwargs = aws_storage._mock_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "test-bucket"
    assert call_kwargs["Key"] == filename
    assert call_kwargs["Body"] == data

    assert result.filename == filename
    assert (
        result.url == "https://test-bucket.s3.amazonaws.com/test/file.txt?signed=true"
    )


@pytest.mark.asyncio
async def test_put_file_with_fileobj(aws_storage):
    """Test put_file with file-like object uses upload_fileobj"""
    fileobj = io.BytesIO(b"large file content")
    filename = "stream/file.webm"

    aws_storage._mock_client.generate_presigned_url.return_value = (
        "https://test-bucket.s3.amazonaws.com/stream/file.webm?signed=true"
    )

    result = await aws_storage.put_file(filename, fileobj)

    aws_storage._mock_client.upload_fileobj.assert_called_once()
    call_kwargs = aws_storage._mock_client.upload_fileobj.call_args[1]
    assert call_kwargs["Bucket"] == "test-bucket"
    assert call_kwargs["Key"] == filename

    call_args = aws_storage._mock_client.upload_fileobj.call_args[0]
    assert call_args[0] == fileobj

    assert result.filename == filename
    assert (
        result.url
        == "https://test-bucket.s3.amazonaws.com/stream/file.webm?signed=true"
    )


@pytest.mark.asyncio
async def test_put_file_fileobj_with_folder_prefix(aws_storage):
    """Test put_file with file-like object and folder prefix"""
    with patch("reflector.storage.storage_aws.aioboto3.Session"):
        storage = AwsStorage(
            aws_access_key_id="test_key_id",
            aws_secret_access_key="test_secret_key",
            aws_bucket_name="test-bucket/my-folder",
            aws_region="us-east-1",
        )

        session = MagicMock()
        mock_client = AsyncMock()

        async def async_enter(self):
            return mock_client

        async def async_exit(self, *args):
            pass

        session.client.return_value.__aenter__ = async_enter
        session.client.return_value.__aexit__ = async_exit
        storage.session = session
        storage.boto_config = aws_storage.boto_config

        mock_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/my-folder/test.webm?signed=true"
        )

        fileobj = io.BytesIO(b"test data")
        filename = "test.webm"

        await storage.put_file(filename, fileobj)

        call_kwargs = mock_client.upload_fileobj.call_args[1]
        assert call_kwargs["Key"] == "my-folder/test.webm"
