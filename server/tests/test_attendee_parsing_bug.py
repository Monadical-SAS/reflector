import os
from unittest.mock import AsyncMock, patch

import pytest

from reflector.db.rooms import rooms_controller
from reflector.services.ics_sync import ICSSyncService


@pytest.mark.asyncio
async def test_attendee_parsing_bug():
    """
    Test that reproduces the attendee parsing bug where a string with comma-separated
    emails gets parsed as individual characters instead of separate email addresses.

    The bug manifests as getting 29 attendees with emails like "M", "A", "I", etc.
    instead of properly parsed email addresses.
    """
    # Create a test room
    room = await rooms_controller.add(
        name="test-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="http://test.com/test.ics",
        ics_enabled=True,
    )

    # Read the test ICS file that reproduces the bug
    test_ics_path = os.path.join(
        os.path.dirname(__file__), "test_attendee_parsing_bug.ics"
    )
    with open(test_ics_path, "r") as f:
        ics_content = f.read()

    # Create sync service and mock the fetch
    sync_service = ICSSyncService()

    with patch.object(
        sync_service.fetch_service, "fetch_ics", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ics_content

        # Debug: Parse the ICS content directly to examine attendee parsing
        calendar = sync_service.fetch_service.parse_ics(ics_content)
        from reflector.settings import settings

        room_url = f"{settings.BASE_URL}/room/{room.name}"

        print(f"Room URL being used for matching: {room_url}")
        print(f"ICS content:\n{ics_content}")

        events, total_events = sync_service.fetch_service.extract_room_events(
            calendar, room.name, room_url
        )

        print(f"Total events in calendar: {total_events}")
        print(f"Events matching room: {len(events)}")

        # Perform the sync
        result = await sync_service.sync_room_calendar(room)

        # Check that the sync succeeded
        assert result.get("status") == "success"
        assert result.get("events_found", 0) >= 0  # Allow for debugging

        # We already have the matching events from the debug code above
        assert len(events) == 1
        event = events[0]

        # This is where the bug manifests - check the attendees
        attendees = event["attendees"]

        # Print attendee info for debugging
        print(f"Number of attendees found: {len(attendees)}")
        for i, attendee in enumerate(attendees):
            print(
                f"Attendee {i}: email='{attendee.get('email')}', name='{attendee.get('name')}'"
            )

        # The bug would cause individual characters to be parsed as attendees
        # Check if we have the problematic parsing (emails like "M", "A", "I", etc.)
        single_char_emails = [
            att for att in attendees if att.get("email") and len(att["email"]) == 1
        ]

        if single_char_emails:
            print(
                f"BUG DETECTED: Found {len(single_char_emails)} single-character emails:"
            )
            for att in single_char_emails:
                print(f"  - '{att['email']}'")

        # For now, just assert that we have attendees (the test will show the bug)
        # In a fix, we would expect proper email addresses, not single characters
        assert len(attendees) > 0

        if len(attendees) > 3:
            pytest.fail(
                f"ATTENDEE PARSING BUG DETECTED: "
                f"Found {len(attendees)} attendees with {len(single_char_emails)} single-character emails. "
                f"This suggests a comma-separated string was parsed as individual characters."
            )


@pytest.mark.asyncio
async def test_correct_attendee_parsing():
    """
    Test what correct attendee parsing should look like.
    """
    from datetime import datetime, timezone

    from icalendar import Event

    from reflector.services.ics_sync import ICSFetchService

    service = ICSFetchService()

    # Create a properly formatted event with multiple attendees
    event = Event()
    event.add("uid", "test-correct-attendees")
    event.add("summary", "Test Meeting")
    event.add("location", "http://test.com/test")
    event.add("dtstart", datetime.now(timezone.utc))
    event.add("dtend", datetime.now(timezone.utc))

    # Add attendees the correct way (separate ATTENDEE lines)
    event.add("attendee", "mailto:alice@example.com", parameters={"CN": "Alice"})
    event.add("attendee", "mailto:bob@example.com", parameters={"CN": "Bob"})
    event.add("attendee", "mailto:charlie@example.com", parameters={"CN": "Charlie"})
    event.add(
        "organizer", "mailto:organizer@example.com", parameters={"CN": "Organizer"}
    )

    # Parse the event
    result = service._parse_event(event)

    assert result is not None
    attendees = result["attendees"]

    # Should have 4 attendees (3 attendees + 1 organizer)
    assert len(attendees) == 4

    # Check that all emails are valid email addresses
    emails = [att["email"] for att in attendees if att.get("email")]
    expected_emails = [
        "alice@example.com",
        "bob@example.com",
        "charlie@example.com",
        "organizer@example.com",
    ]

    for email in emails:
        assert "@" in email, f"Invalid email format: {email}"
        assert len(email) > 5, f"Email too short: {email}"

    # Check that we have the expected emails
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails
    assert "charlie@example.com" in emails
    assert "organizer@example.com" in emails
