"""Tests for S3 download functionality in audio_tasks"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from reflector.worker.audio_tasks import parse_s3_url, download_audio_file, _download_from_s3, _download_from_http


class TestS3URLParsing:
    """Test S3 URL parsing"""
    
    def test_s3_protocol_url(self):
        """Test s3:// protocol URLs"""
        assert parse_s3_url("s3://my-bucket/path/to/file.mp4") == ("my-bucket", "path/to/file.mp4")
        assert parse_s3_url("s3://bucket/file.wav") == ("bucket", "file.wav")
    
    def test_virtual_hosted_style_url(self):
        """Test virtual-hosted-style S3 URLs"""
        assert parse_s3_url("https://my-bucket.s3.amazonaws.com/path/to/file.mp4") == ("my-bucket", "path/to/file.mp4")
        assert parse_s3_url("https://bucket.s3.us-west-2.amazonaws.com/file.wav") == ("bucket", "file.wav")
    
    def test_path_style_url(self):
        """Test path-style S3 URLs"""
        assert parse_s3_url("https://s3.amazonaws.com/my-bucket/path/to/file.mp4") == ("my-bucket", "path/to/file.mp4")
        assert parse_s3_url("https://s3-us-west-2.amazonaws.com/bucket/file.wav") == ("bucket", "file.wav")
    
    def test_non_s3_url(self):
        """Test non-S3 URLs return None"""
        assert parse_s3_url("https://example.com/file.mp4") is None
        assert parse_s3_url("http://localhost:8080/test.wav") is None
        assert parse_s3_url("ftp://server.com/file.mp3") is None


class TestAudioFileDownload:
    """Test audio file download functionality"""
    
    @pytest.mark.asyncio
    @patch('reflector.worker.audio_tasks._download_from_s3')
    @patch('reflector.worker.audio_tasks.tempfile.NamedTemporaryFile')
    async def test_download_s3_url(self, mock_tempfile, mock_s3_download):
        """Test downloading from S3 URL"""
        # Setup
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_abc123.mp4"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        mock_s3_download.return_value = None
        
        # Test
        result = await download_audio_file("s3://my-bucket/audio/test.mp4")
        
        # Verify
        assert result == "/tmp/test_abc123.mp4"
        mock_s3_download.assert_called_once_with("s3://my-bucket/audio/test.mp4", "/tmp/test_abc123.mp4")
    
    @pytest.mark.asyncio
    @patch('reflector.worker.audio_tasks._download_from_http')
    @patch('reflector.worker.audio_tasks.tempfile.NamedTemporaryFile')
    async def test_download_http_url(self, mock_tempfile, mock_http_download):
        """Test downloading from HTTP URL"""
        # Setup
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_xyz789.mp4"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        mock_http_download.return_value = None
        
        # Test
        result = await download_audio_file("https://example.com/audio/test.mp4")
        
        # Verify
        assert result == "/tmp/test_xyz789.mp4"
        mock_http_download.assert_called_once_with("https://example.com/audio/test.mp4", "/tmp/test_xyz789.mp4")
    
    @pytest.mark.asyncio
    @patch('reflector.worker.audio_tasks._download_from_s3')
    @patch('reflector.worker.audio_tasks.settings')
    @patch('reflector.worker.audio_tasks.tempfile.NamedTemporaryFile')
    async def test_download_storage_key(self, mock_tempfile, mock_settings, mock_s3_download):
        """Test downloading using storage key (no protocol)"""
        # Setup
        mock_settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME = "reflector-media"
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_key123.mp4"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        mock_s3_download.return_value = None
        
        # Test
        result = await download_audio_file("audio/uploads/test.mp4")
        
        # Verify
        assert result == "/tmp/test_key123.mp4"
        mock_s3_download.assert_called_once_with("s3://reflector-media/audio/uploads/test.mp4", "/tmp/test_key123.mp4")


class TestS3Download:
    """Test S3-specific download functionality"""
    
    @pytest.mark.asyncio
    @patch('reflector.worker.audio_tasks.aioboto3.Session')
    @patch('builtins.open', new_callable=mock_open)
    async def test_s3_download_success(self, mock_file, mock_session):
        """Test successful S3 download"""
        # Setup
        mock_s3_client = AsyncMock()
        mock_s3_client.download_fileobj = AsyncMock()
        mock_session.return_value.client.return_value.__aenter__.return_value = mock_s3_client
        
        # Test
        await _download_from_s3("s3://my-bucket/path/to/file.mp4", "/tmp/output.mp4")
        
        # Verify
        mock_s3_client.download_fileobj.assert_called_once_with("my-bucket", "path/to/file.mp4", mock_file())
    
    @pytest.mark.asyncio
    @patch('reflector.worker.audio_tasks._download_from_http')
    @patch('reflector.worker.audio_tasks.aioboto3.Session')
    @patch('builtins.open', new_callable=mock_open)
    async def test_s3_download_fallback(self, mock_file, mock_session, mock_http):
        """Test fallback to HTTP when S3 download fails"""
        # Setup
        mock_s3_client = AsyncMock()
        mock_s3_client.download_fileobj = AsyncMock(side_effect=Exception("Access Denied"))
        mock_session.return_value.client.return_value.__aenter__.return_value = mock_s3_client
        mock_http.return_value = None
        
        # Test
        await _download_from_s3("s3://my-bucket/file.mp4", "/tmp/output.mp4")
        
        # Verify - should fall back to HTTP
        mock_http.assert_called_once_with("s3://my-bucket/file.mp4", "/tmp/output.mp4")
    
    @pytest.mark.asyncio
    @patch('reflector.worker.audio_tasks._download_from_http')
    async def test_s3_download_unparseable_url(self, mock_http):
        """Test handling of unparseable S3 URLs"""
        # Test with a presigned URL that can't be parsed
        presigned_url = "https://my-bucket.s3.amazonaws.com/file.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=..."
        
        await _download_from_s3(presigned_url, "/tmp/output.mp4")
        
        # Should fall back to HTTP download
        mock_http.assert_called_once_with(presigned_url, "/tmp/output.mp4")