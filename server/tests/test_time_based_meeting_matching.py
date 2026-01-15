"""
Integration tests for time-based meeting-to-recording matching.

Tests the critical path for matching Daily.co recordings to meetings when
API doesn't return instanceId.
"""

from datetime import datetime, timedelta, timezone

import pytest

from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller


@pytest.fixture
async def test_room():
    """Create a test room for meetings."""
    room = await rooms_controller.add(
        name="test-room-time",
        user_id="test-user-id",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic",
        is_shared=False,
        platform="daily",
    )
    return room


@pytest.fixture
def base_time():
    """Fixed timestamp for deterministic tests."""
    return datetime(2026, 1, 14, 9, 0, 0, tzinfo=timezone.utc)


class TestTimeBasedMatching:
    """Test get_by_room_name_and_time() matching logic."""

    async def test_exact_time_match(self, test_room, base_time):
        """Recording timestamp exactly matches meeting start_date."""
        meeting = await meetings_controller.create(
            id="meeting-exact",
            room_name="daily-test-20260114090000",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-20260114090000",
            recording_start=base_time,
            time_window_hours=168,
        )

        assert result is not None
        assert result.id == meeting.id

    async def test_recording_slightly_after_meeting_start(self, test_room, base_time):
        """Recording started 1 minute after meeting (participants joined late)."""
        meeting = await meetings_controller.create(
            id="meeting-late",
            room_name="daily-test-20260114090100",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        recording_start = base_time + timedelta(minutes=1)

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-20260114090100",
            recording_start=recording_start,
            time_window_hours=168,
        )

        assert result is not None
        assert result.id == meeting.id

    async def test_duplicate_room_names_picks_closest(self, test_room, base_time):
        """
        Two meetings with same room_name (duplicate/race condition).
        Should pick closest by timestamp.
        """
        meeting1 = await meetings_controller.create(
            id="meeting-1-first",
            room_name="daily-duplicate-room",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        meeting2 = await meetings_controller.create(
            id="meeting-2-second",
            room_name="daily-duplicate-room",  # Same room_name!
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time + timedelta(seconds=0.99),  # 0.99s later
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        # Recording started 0.5s after meeting1
        # Distance: meeting1 = 0.5s, meeting2 = 0.49s → meeting2 is closer
        recording_start = base_time + timedelta(seconds=0.5)

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-duplicate-room",
            recording_start=recording_start,
            time_window_hours=168,
        )

        assert result is not None
        assert result.id == meeting2.id  # meeting2 is closer (0.49s vs 0.5s)

    async def test_outside_time_window_returns_none(self, test_room, base_time):
        """Recording outside 1-week window returns None."""
        await meetings_controller.create(
            id="meeting-old",
            room_name="daily-test-old",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        # Recording 8 days later (outside 7-day window)
        recording_start = base_time + timedelta(days=8)

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-old",
            recording_start=recording_start,
            time_window_hours=168,
        )

        assert result is None

    async def test_tie_breaker_deterministic(self, test_room, base_time):
        """When time delta identical, tie-breaker by meeting.id is deterministic."""
        meeting_z = await meetings_controller.create(
            id="zzz-last-uuid",
            room_name="daily-test-tie",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        meeting_a = await meetings_controller.create(
            id="aaa-first-uuid",
            room_name="daily-test-tie",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,  # Exact same start_date
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-tie",
            recording_start=base_time,
            time_window_hours=168,
        )

        assert result is not None
        # Tie-breaker: lexicographically first UUID
        assert result.id == "aaa-first-uuid"

    async def test_timezone_naive_datetime_raises(self, test_room, base_time):
        """Timezone-naive datetime raises ValueError."""
        await meetings_controller.create(
            id="meeting-tz",
            room_name="daily-test-tz",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        # Naive datetime (no timezone)
        naive_dt = datetime(2026, 1, 14, 9, 0, 0)

        with pytest.raises(ValueError, match="timezone-aware"):
            await meetings_controller.get_by_room_name_and_time(
                room_name="daily-test-tz",
                recording_start=naive_dt,
                time_window_hours=168,
            )

    async def test_one_week_boundary_after_included(self, test_room, base_time):
        """Meeting 1-week AFTER recording is included (window_end boundary)."""
        meeting_time = base_time + timedelta(hours=168)

        await meetings_controller.create(
            id="meeting-boundary-after",
            room_name="daily-test-boundary-after",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=meeting_time,
            end_date=meeting_time + timedelta(hours=1),
            room=test_room,
        )

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-boundary-after",
            recording_start=base_time,
            time_window_hours=168,
        )

        assert result is not None
        assert result.id == "meeting-boundary-after"

    async def test_one_week_boundary_before_included(self, test_room, base_time):
        """Meeting 1-week BEFORE recording is included (window_start boundary)."""
        meeting_time = base_time - timedelta(hours=168)

        await meetings_controller.create(
            id="meeting-boundary-before",
            room_name="daily-test-boundary-before",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=meeting_time,
            end_date=meeting_time + timedelta(hours=1),
            room=test_room,
        )

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-boundary-before",
            recording_start=base_time,
            time_window_hours=168,
        )

        assert result is not None
        assert result.id == "meeting-boundary-before"

    async def test_recording_before_meeting_start(self, test_room, base_time):
        """Recording started before meeting (clock skew or early join)."""
        await meetings_controller.create(
            id="meeting-early",
            room_name="daily-test-early",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        recording_start = base_time - timedelta(minutes=2)

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-early",
            recording_start=recording_start,
            time_window_hours=168,
        )

        assert result is not None
        assert result.id == "meeting-early"

    async def test_mixed_inside_outside_window(self, test_room, base_time):
        """Multiple meetings, only one inside window - returns the inside one."""
        await meetings_controller.create(
            id="meeting-old",
            room_name="daily-test-mixed",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time - timedelta(days=10),
            end_date=base_time - timedelta(days=10, hours=-1),
            room=test_room,
        )

        await meetings_controller.create(
            id="meeting-inside",
            room_name="daily-test-mixed",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time - timedelta(days=2),
            end_date=base_time - timedelta(days=2, hours=-1),
            room=test_room,
        )

        await meetings_controller.create(
            id="meeting-future",
            room_name="daily-test-mixed",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time + timedelta(days=10),
            end_date=base_time + timedelta(days=10, hours=1),
            room=test_room,
        )

        result = await meetings_controller.get_by_room_name_and_time(
            room_name="daily-test-mixed",
            recording_start=base_time,
            time_window_hours=168,
        )

        assert result is not None
        assert result.id == "meeting-inside"


class TestAtomicCloudRecordingUpdate:
    """Test atomic update prevents race conditions."""

    async def test_first_update_succeeds(self, test_room, base_time):
        """First call to set_cloud_recording_if_missing succeeds."""
        meeting = await meetings_controller.create(
            id="meeting-atomic-1",
            room_name="daily-test-atomic",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        success = await meetings_controller.set_cloud_recording_if_missing(
            meeting_id=meeting.id,
            s3_key="first-s3-key",
            duration=100,
        )

        assert success is True

        updated = await meetings_controller.get_by_id(meeting.id)
        assert updated.daily_composed_video_s3_key == "first-s3-key"
        assert updated.daily_composed_video_duration == 100

    async def test_second_update_fails_atomically(self, test_room, base_time):
        """Second call to update same meeting doesn't overwrite (atomic check)."""
        meeting = await meetings_controller.create(
            id="meeting-atomic-2",
            room_name="daily-test-atomic2",
            room_url="https://example.daily.co/test",
            host_room_url="https://example.daily.co/test?t=host",
            start_date=base_time,
            end_date=base_time + timedelta(hours=1),
            room=test_room,
        )

        success1 = await meetings_controller.set_cloud_recording_if_missing(
            meeting_id=meeting.id,
            s3_key="first-s3-key",
            duration=100,
        )

        assert success1 is True

        after_first = await meetings_controller.get_by_id(meeting.id)
        assert after_first.daily_composed_video_s3_key == "first-s3-key"

        success2 = await meetings_controller.set_cloud_recording_if_missing(
            meeting_id=meeting.id,
            s3_key="bucket/path/should-not-overwrite",
            duration=200,
        )

        assert success2 is False

        final = await meetings_controller.get_by_id(meeting.id)
        assert final.daily_composed_video_s3_key == "first-s3-key"
        assert final.daily_composed_video_duration == 100
