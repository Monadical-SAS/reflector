"""Tests for video_platforms.factory module."""

from unittest.mock import patch

from reflector.video_platforms.factory import get_platform


class TestGetPlatformF:
    """Test suite for get_platform function."""

    @patch("reflector.video_platforms.factory.settings")
    def test_with_room_platform(self, mock_settings):
        """When room_platform provided, should return room_platform."""
        mock_settings.DEFAULT_VIDEO_PLATFORM = "whereby"

        # Should return the room's platform when provided
        assert get_platform(room_platform="daily") == "daily"
        assert get_platform(room_platform="whereby") == "whereby"

    @patch("reflector.video_platforms.factory.settings")
    def test_without_room_platform_uses_default(self, mock_settings):
        """When no room_platform, should return DEFAULT_VIDEO_PLATFORM."""
        mock_settings.DEFAULT_VIDEO_PLATFORM = "whereby"

        # Should return default when room_platform is None
        assert get_platform(room_platform=None) == "whereby"

    @patch("reflector.video_platforms.factory.settings")
    def test_with_daily_default(self, mock_settings):
        """When DEFAULT_VIDEO_PLATFORM is 'daily', should return 'daily' when no room_platform."""
        mock_settings.DEFAULT_VIDEO_PLATFORM = "daily"

        # Should return default 'daily' when room_platform is None
        assert get_platform(room_platform=None) == "daily"

    @patch("reflector.video_platforms.factory.settings")
    def test_no_room_id_provided(self, mock_settings):
        """Should work correctly even when room_id is not provided."""
        mock_settings.DEFAULT_VIDEO_PLATFORM = "whereby"

        # Should use room_platform when provided
        assert get_platform(room_platform="daily") == "daily"

        # Should use default when room_platform not provided
        assert get_platform(room_platform=None) == "whereby"

    @patch("reflector.video_platforms.factory.settings")
    def test_room_platform_always_takes_precedence(self, mock_settings):
        """room_platform should always be used when provided."""
        mock_settings.DEFAULT_VIDEO_PLATFORM = "whereby"

        # room_platform should take precedence over default
        assert get_platform(room_platform="daily") == "daily"
        assert get_platform(room_platform="whereby") == "whereby"

        # Different default shouldn't matter when room_platform provided
        mock_settings.DEFAULT_VIDEO_PLATFORM = "daily"
        assert get_platform(room_platform="whereby") == "whereby"
