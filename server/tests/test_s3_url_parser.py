"""Tests for S3 URL parsing functionality in reflector.tools.process"""

import pytest

from reflector.tools.process import parse_s3_url


class TestParseS3URL:
    """Test cases for parse_s3_url function"""

    def test_parse_s3_protocol(self):
        """Test parsing s3:// protocol URLs"""
        bucket, key = parse_s3_url("s3://my-bucket/path/to/file.webm")
        assert bucket == "my-bucket"
        assert key == "path/to/file.webm"

    def test_parse_s3_protocol_deep_path(self):
        """Test s3:// with deeply nested paths"""
        bucket, key = parse_s3_url("s3://bucket-name/very/deep/path/to/audio.mp4")
        assert bucket == "bucket-name"
        assert key == "very/deep/path/to/audio.mp4"

    def test_parse_https_subdomain_format(self):
        """Test parsing https://bucket.s3.amazonaws.com/key format"""
        bucket, key = parse_s3_url("https://my-bucket.s3.amazonaws.com/path/file.webm")
        assert bucket == "my-bucket"
        assert key == "path/file.webm"

    def test_parse_https_regional_subdomain(self):
        """Test parsing regional endpoint with subdomain"""
        bucket, key = parse_s3_url(
            "https://my-bucket.s3.us-west-2.amazonaws.com/path/file.webm"
        )
        assert bucket == "my-bucket"
        assert key == "path/file.webm"

    def test_parse_https_path_style(self):
        """Test parsing https://s3.amazonaws.com/bucket/key format"""
        bucket, key = parse_s3_url("https://s3.amazonaws.com/my-bucket/path/file.webm")
        assert bucket == "my-bucket"
        assert key == "path/file.webm"

    def test_parse_https_regional_path_style(self):
        """Test parsing regional endpoint with path style"""
        bucket, key = parse_s3_url(
            "https://s3.us-east-1.amazonaws.com/my-bucket/path/file.webm"
        )
        assert bucket == "my-bucket"
        assert key == "path/file.webm"

    def test_parse_url_encoded_keys(self):
        """Test parsing URL-encoded keys"""
        bucket, key = parse_s3_url(
            "s3://my-bucket/path%20with%20spaces/file%2Bname.webm"
        )
        assert bucket == "my-bucket"
        assert key == "path with spaces/file+name.webm"  # Should be decoded

    def test_parse_url_encoded_https(self):
        """Test URL-encoded keys with HTTPS format"""
        bucket, key = parse_s3_url(
            "https://my-bucket.s3.amazonaws.com/file%20with%20spaces.webm"
        )
        assert bucket == "my-bucket"
        assert key == "file with spaces.webm"

    def test_invalid_url_no_scheme(self):
        """Test that URLs without scheme raise ValueError"""
        with pytest.raises(ValueError, match="Invalid S3 URL scheme"):
            parse_s3_url("my-bucket/path/file.webm")

    def test_invalid_url_wrong_scheme(self):
        """Test that non-S3 schemes raise ValueError"""
        with pytest.raises(ValueError, match="Invalid S3 URL scheme"):
            parse_s3_url("ftp://my-bucket/path/file.webm")

    def test_invalid_s3_missing_bucket(self):
        """Test s3:// URL without bucket raises ValueError"""
        with pytest.raises(ValueError, match="missing bucket or key"):
            parse_s3_url("s3:///path/file.webm")

    def test_invalid_s3_missing_key(self):
        """Test s3:// URL without key raises ValueError"""
        with pytest.raises(ValueError, match="missing bucket or key"):
            parse_s3_url("s3://my-bucket/")

    def test_invalid_s3_empty_key(self):
        """Test s3:// URL with empty key raises ValueError"""
        with pytest.raises(ValueError, match="missing bucket or key"):
            parse_s3_url("s3://my-bucket")

    def test_invalid_https_not_s3(self):
        """Test HTTPS URL that's not S3 raises ValueError"""
        with pytest.raises(ValueError, match="not recognized as S3 URL"):
            parse_s3_url("https://example.com/path/file.webm")

    def test_invalid_https_subdomain_missing_key(self):
        """Test HTTPS subdomain format without key raises ValueError"""
        with pytest.raises(ValueError, match="missing bucket or key"):
            parse_s3_url("https://my-bucket.s3.amazonaws.com/")

    def test_invalid_https_path_style_missing_parts(self):
        """Test HTTPS path style with missing bucket/key raises ValueError"""
        with pytest.raises(ValueError, match="missing bucket or key"):
            parse_s3_url("https://s3.amazonaws.com/")

    def test_bucket_with_dots(self):
        """Test parsing bucket names with dots"""
        bucket, key = parse_s3_url("s3://my.bucket.name/path/file.webm")
        assert bucket == "my.bucket.name"
        assert key == "path/file.webm"

    def test_bucket_with_hyphens(self):
        """Test parsing bucket names with hyphens"""
        bucket, key = parse_s3_url("s3://my-bucket-name-123/path/file.webm")
        assert bucket == "my-bucket-name-123"
        assert key == "path/file.webm"

    def test_key_with_special_chars(self):
        """Test keys with various special characters"""
        # Note: # is treated as URL fragment separator, not part of key
        bucket, key = parse_s3_url("s3://bucket/2024-01-01_12:00:00/file.webm")
        assert bucket == "bucket"
        assert key == "2024-01-01_12:00:00/file.webm"

    def test_fragment_handling(self):
        """Test that URL fragments are properly ignored"""
        bucket, key = parse_s3_url("s3://bucket/path/to/file.webm#fragment123")
        assert bucket == "bucket"
        assert key == "path/to/file.webm"  # Fragment not included

    def test_http_scheme_s3_url(self):
        """Test that HTTP (not HTTPS) S3 URLs are supported"""
        bucket, key = parse_s3_url("http://my-bucket.s3.amazonaws.com/path/file.webm")
        assert bucket == "my-bucket"
        assert key == "path/file.webm"
