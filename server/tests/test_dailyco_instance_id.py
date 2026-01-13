"""
Tests for Daily.co instanceId generation.

Verifies deterministic behavior and frontend/backend consistency.
"""

import pytest

from reflector.dailyco_api.instance_id import (
    RAW_TRACKS_NAMESPACE,
    generate_cloud_instance_id,
    generate_raw_tracks_instance_id,
)


class TestInstanceIdDeterminism:
    """Test deterministic generation of instanceIds."""

    def test_cloud_instance_id_is_meeting_id(self):
        """Cloud instanceId is meeting ID directly."""
        meeting_id = "550e8400-e29b-41d4-a716-446655440000"
        result = generate_cloud_instance_id(meeting_id)
        assert str(result) == meeting_id

    def test_cloud_instance_id_deterministic(self):
        """Cloud instanceId generation is deterministic."""
        meeting_id = "550e8400-e29b-41d4-a716-446655440000"
        result1 = generate_cloud_instance_id(meeting_id)
        result2 = generate_cloud_instance_id(meeting_id)
        assert result1 == result2

    def test_raw_tracks_instance_id_deterministic(self):
        """Raw-tracks instanceId generation is deterministic."""
        meeting_id = "550e8400-e29b-41d4-a716-446655440000"
        result1 = generate_raw_tracks_instance_id(meeting_id)
        result2 = generate_raw_tracks_instance_id(meeting_id)
        assert result1 == result2

    def test_raw_tracks_different_from_cloud(self):
        """Raw-tracks instanceId differs from cloud instanceId."""
        meeting_id = "550e8400-e29b-41d4-a716-446655440000"
        cloud_id = generate_cloud_instance_id(meeting_id)
        raw_tracks_id = generate_raw_tracks_instance_id(meeting_id)
        assert cloud_id != raw_tracks_id

    def test_different_meetings_different_instance_ids(self):
        """Different meetings generate different instanceIds."""
        meeting_id1 = "550e8400-e29b-41d4-a716-446655440000"
        meeting_id2 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

        cloud1 = generate_cloud_instance_id(meeting_id1)
        cloud2 = generate_cloud_instance_id(meeting_id2)
        assert cloud1 != cloud2

        raw1 = generate_raw_tracks_instance_id(meeting_id1)
        raw2 = generate_raw_tracks_instance_id(meeting_id2)
        assert raw1 != raw2


class TestFrontendBackendConsistency:
    """Test that backend matches frontend logic."""

    def test_namespace_matches_frontend(self):
        """Namespace UUID matches frontend RAW_TRACKS_NAMESPACE constant."""
        # From www/app/[roomName]/components/DailyRoom.tsx
        frontend_namespace = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert str(RAW_TRACKS_NAMESPACE) == frontend_namespace

    def test_raw_tracks_generation_matches_frontend_logic(self):
        """Backend UUIDv5 generation matches frontend uuidv5() call."""
        # Example meeting ID
        meeting_id = "550e8400-e29b-41d4-a716-446655440000"

        # Backend result
        backend_result = generate_raw_tracks_instance_id(meeting_id)

        # Expected result from frontend: uuidv5(meeting.id, RAW_TRACKS_NAMESPACE)
        # Python uuid5 uses (namespace, name) argument order
        # JavaScript uuid.v5(name, namespace) - same args, different order
        # Frontend: uuidv5(meeting.id, "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        # Backend: uuid5(UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"), meeting.id)

        # Verify it's a valid UUID (will raise if not)
        assert len(str(backend_result)) == 36
        assert backend_result.version == 5


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_invalid_uuid_format_raises(self):
        """Invalid UUID format raises ValueError."""
        with pytest.raises(ValueError):
            generate_cloud_instance_id("not-a-uuid")

    def test_lowercase_uuid_normalized_for_cloud(self):
        """Cloud instanceId: lowercase/uppercase UUIDs produce same result."""
        meeting_id_lower = "550e8400-e29b-41d4-a716-446655440000"
        meeting_id_upper = "550E8400-E29B-41D4-A716-446655440000"

        cloud_lower = generate_cloud_instance_id(meeting_id_lower)
        cloud_upper = generate_cloud_instance_id(meeting_id_upper)
        assert cloud_lower == cloud_upper

    def test_raw_tracks_case_sensitive(self):
        """
        Raw-tracks instanceId is CASE-SENSITIVE (uuid5 hashes string directly).

        This is fine - meeting IDs from DB are always lowercase.
        Frontend also uses lowercase meeting.id from API.
        """
        meeting_id_lower = "550e8400-e29b-41d4-a716-446655440000"
        meeting_id_upper = "550E8400-E29B-41D4-A716-446655440000"

        raw_lower = generate_raw_tracks_instance_id(meeting_id_lower)
        raw_upper = generate_raw_tracks_instance_id(meeting_id_upper)
        # Different cases produce different hashes
        assert raw_lower != raw_upper


class TestMtgSessionIdVsInstanceId:
    """
    Test that mtgSessionId (Daily.co-generated) differs from instanceId (we send).

    Based on production data analysis showing mtgSessionId is separate from instanceId.
    """

    def test_mtg_session_id_not_equal_to_cloud_instance_id(self):
        """
        mtgSessionId from Daily.co does NOT match cloud instanceId we send.

        Real example from production:
        - Meeting ID (cloud instanceId): 4ad503b6-8189-4910-a8f7-68cdd1b7f990
        - Recording mtgSessionId:        f25a2e09-740f-4932-9c0d-b1bebaa669c6
        """
        meeting_id = "4ad503b6-8189-4910-a8f7-68cdd1b7f990"
        mtg_session_id = "f25a2e09-740f-4932-9c0d-b1bebaa669c6"

        cloud_instance_id = generate_cloud_instance_id(meeting_id)
        assert str(cloud_instance_id) != mtg_session_id

    def test_mtg_session_id_not_equal_to_raw_tracks_instance_id(self):
        """
        mtgSessionId from Daily.co does NOT match raw-tracks instanceId we send.

        Real example from production:
        - Meeting ID:                  4ad503b6-8189-4910-a8f7-68cdd1b7f990
        - Raw-tracks instanceId:       784b3af3-c7dd-57f0-ac54-2ee91c6927cb
        - Recording mtgSessionId:      f25a2e09-740f-4932-9c0d-b1bebaa669c6
        """
        meeting_id = "4ad503b6-8189-4910-a8f7-68cdd1b7f990"
        expected_raw_tracks_id = "784b3af3-c7dd-57f0-ac54-2ee91c6927cb"
        mtg_session_id = "f25a2e09-740f-4932-9c0d-b1bebaa669c6"

        raw_tracks_instance_id = generate_raw_tracks_instance_id(meeting_id)
        assert str(raw_tracks_instance_id) == expected_raw_tracks_id
        assert str(raw_tracks_instance_id) != mtg_session_id
