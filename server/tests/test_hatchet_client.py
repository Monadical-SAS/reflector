"""
Tests for HatchetClientManager error handling and validation.

Only tests that catch real bugs - not mock verification tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_hatchet_client_can_replay_handles_exception():
    """Test can_replay returns False when status check fails.

    Useful: Ensures network/API errors don't crash the system and
    gracefully allow reprocessing when workflow state is unknown.
    """
    from reflector.hatchet.client import HatchetClientManager

    HatchetClientManager._instance = None

    with patch("reflector.hatchet.client.settings") as mock_settings:
        mock_settings.HATCHET_CLIENT_TOKEN = "test-token"
        mock_settings.HATCHET_DEBUG = False

        with patch("reflector.hatchet.client.Hatchet") as mock_hatchet_class:
            mock_client = MagicMock()
            mock_hatchet_class.return_value = mock_client

            mock_client.runs.aio_get_status = AsyncMock(
                side_effect=Exception("Network error")
            )

            can_replay = await HatchetClientManager.can_replay("workflow-123")

            # Should return False on error (workflow might be gone)
            assert can_replay is False

    HatchetClientManager._instance = None


def test_hatchet_client_raises_without_token():
    """Test that get_client raises ValueError without token.

    Useful: Catches if someone removes the token validation,
    which would cause cryptic errors later.
    """
    from reflector.hatchet.client import HatchetClientManager

    HatchetClientManager._instance = None

    with patch("reflector.hatchet.client.settings") as mock_settings:
        mock_settings.HATCHET_CLIENT_TOKEN = None

        with pytest.raises(ValueError, match="HATCHET_CLIENT_TOKEN must be set"):
            HatchetClientManager.get_client()

    HatchetClientManager._instance = None
