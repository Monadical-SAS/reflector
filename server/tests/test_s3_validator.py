"""Tests for S3 object validation functionality in reflector.tools.process"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from reflector.tools.process import validate_s3_objects


class TestValidateS3Objects:
    """Test cases for validate_s3_objects function"""

    @pytest.mark.asyncio
    async def test_validate_existing_objects(self):
        """Test successful validation of existing S3 objects"""
        # Mock storage and S3 client
        mock_storage = MagicMock()
        mock_client = AsyncMock()
        mock_client.head_object = AsyncMock(return_value={"ContentLength": 1024})

        # Mock the context manager
        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        # Test with multiple bucket/key pairs
        bucket_keys = [
            ("bucket1", "path/to/file1.webm"),
            ("bucket2", "path/to/file2.webm"),
            ("bucket1", "another/file.webm"),
        ]

        # Should not raise any exception
        await validate_s3_objects(mock_storage, bucket_keys)

        # Verify head_object was called for each object
        assert mock_client.head_object.call_count == 3
        mock_client.head_object.assert_any_call(
            Bucket="bucket1", Key="path/to/file1.webm"
        )
        mock_client.head_object.assert_any_call(
            Bucket="bucket2", Key="path/to/file2.webm"
        )
        mock_client.head_object.assert_any_call(
            Bucket="bucket1", Key="another/file.webm"
        )

    @pytest.mark.asyncio
    async def test_validate_missing_object_error(self):
        """Test validation raises error for missing S3 object"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        # Simulate 404 error
        error = Exception()
        error.response = {"Error": {"Code": "404"}}
        mock_client.head_object = AsyncMock(side_effect=error)

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [("test-bucket", "missing/file.webm")]

        with pytest.raises(
            ValueError, match="S3 object not found: s3://test-bucket/missing/file.webm"
        ):
            await validate_s3_objects(mock_storage, bucket_keys)

    @pytest.mark.asyncio
    async def test_validate_no_such_key_error(self):
        """Test validation handles NoSuchKey error code"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        # Simulate NoSuchKey error (alternative to 404)
        error = Exception()
        error.response = {"Error": {"Code": "NoSuchKey"}}
        mock_client.head_object = AsyncMock(side_effect=error)

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [("test-bucket", "nonexistent/file.webm")]

        with pytest.raises(
            ValueError,
            match="S3 object not found: s3://test-bucket/nonexistent/file.webm",
        ):
            await validate_s3_objects(mock_storage, bucket_keys)

    @pytest.mark.asyncio
    async def test_validate_access_denied_error(self):
        """Test validation raises specific error for access denied"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        # Simulate 403 Forbidden error
        error = Exception()
        error.response = {"Error": {"Code": "403"}}
        mock_client.head_object = AsyncMock(side_effect=error)

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [("restricted-bucket", "private/file.webm")]

        with pytest.raises(
            ValueError,
            match="Access denied for S3 object: s3://restricted-bucket/private/file.webm. Check AWS credentials and permissions",
        ):
            await validate_s3_objects(mock_storage, bucket_keys)

    @pytest.mark.asyncio
    async def test_validate_forbidden_error(self):
        """Test validation handles Forbidden error code"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        # Simulate Forbidden error (alternative to 403)
        error = Exception()
        error.response = {"Error": {"Code": "Forbidden"}}
        mock_client.head_object = AsyncMock(side_effect=error)

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [("restricted-bucket", "forbidden/file.webm")]

        with pytest.raises(
            ValueError,
            match="Access denied for S3 object: s3://restricted-bucket/forbidden/file.webm. Check AWS credentials and permissions",
        ):
            await validate_s3_objects(mock_storage, bucket_keys)

    @pytest.mark.asyncio
    async def test_validate_other_s3_error(self):
        """Test validation handles other S3 error codes"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        # Simulate other S3 error
        error = Exception()
        error.response = {"Error": {"Code": "ServiceUnavailable"}}
        mock_client.head_object = AsyncMock(side_effect=error)

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [("test-bucket", "path/file.webm")]

        with pytest.raises(
            ValueError,
            match="Error accessing S3 object s3://test-bucket/path/file.webm: ServiceUnavailable",
        ):
            await validate_s3_objects(mock_storage, bucket_keys)

    @pytest.mark.asyncio
    async def test_validate_network_error_handling(self):
        """Test validation handles network errors gracefully"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        # Simulate network error (no response attribute)
        mock_client.head_object = AsyncMock(
            side_effect=ConnectionError("Network unreachable")
        )

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [("test-bucket", "path/file.webm")]

        with pytest.raises(
            ValueError,
            match="Failed to validate S3 object s3://test-bucket/path/file.webm: Network unreachable",
        ):
            await validate_s3_objects(mock_storage, bucket_keys)

    @pytest.mark.asyncio
    async def test_validate_mixed_buckets(self):
        """Test validation works with objects from different buckets"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()
        mock_client.head_object = AsyncMock(return_value={"ContentLength": 1024})

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [
            ("bucket-a", "file1.webm"),
            ("bucket-b", "file2.webm"),
            ("bucket-c", "file3.webm"),
        ]

        # Should validate all objects successfully
        await validate_s3_objects(mock_storage, bucket_keys)

        # Verify each bucket was checked
        assert mock_client.head_object.call_count == 3
        calls = mock_client.head_object.call_args_list
        assert any(call[1]["Bucket"] == "bucket-a" for call in calls)
        assert any(call[1]["Bucket"] == "bucket-b" for call in calls)
        assert any(call[1]["Bucket"] == "bucket-c" for call in calls)

    @pytest.mark.asyncio
    async def test_validate_empty_list(self):
        """Test validation with empty bucket_keys list"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        # Should not raise any exception for empty list
        await validate_s3_objects(mock_storage, [])

        # head_object should not be called
        mock_client.head_object.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_fails_on_first_error(self):
        """Test validation stops and raises error on first failure"""
        mock_storage = MagicMock()
        mock_client = AsyncMock()

        # First call fails, subsequent calls would succeed
        error = Exception()
        error.response = {"Error": {"Code": "404"}}
        mock_client.head_object = AsyncMock(
            side_effect=[error, {"ContentLength": 1024}, {"ContentLength": 2048}]
        )

        mock_storage.session.client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_storage.session.client.return_value.__aexit__ = AsyncMock()

        bucket_keys = [
            ("bucket1", "missing.webm"),
            ("bucket2", "exists1.webm"),
            ("bucket3", "exists2.webm"),
        ]

        with pytest.raises(
            ValueError, match="S3 object not found: s3://bucket1/missing.webm"
        ):
            await validate_s3_objects(mock_storage, bucket_keys)

        # Should only call head_object once (fails on first)
        assert mock_client.head_object.call_count == 1
