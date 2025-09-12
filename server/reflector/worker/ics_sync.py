from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task
from celery.utils.log import get_task_logger

from reflector.asynctask import asynctask
from reflector.db.calendar_events import calendar_events_controller
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller
from reflector.services.ics_sync import SyncStatus, ics_sync_service
from reflector.whereby import create_meeting, upload_logo

logger = structlog.wrap_logger(get_task_logger(__name__))


@shared_task
@asynctask
async def sync_room_ics(room_id: str):
    try:
        room = await rooms_controller.get_by_id(room_id)
        if not room:
            logger.warning("Room not found for ICS sync", room_id=room_id)
            return

        if not room.ics_enabled or not room.ics_url:
            logger.debug("ICS not enabled for room", room_id=room_id)
            return

        logger.info("Starting ICS sync for room", room_id=room_id, room_name=room.name)
        result = await ics_sync_service.sync_room_calendar(room)

        if result["status"] == SyncStatus.SUCCESS:
            logger.info(
                "ICS sync completed successfully",
                room_id=room_id,
                events_found=result.get("events_found", 0),
                events_created=result.get("events_created", 0),
                events_updated=result.get("events_updated", 0),
                events_deleted=result.get("events_deleted", 0),
            )
        elif result["status"] == SyncStatus.UNCHANGED:
            logger.debug("ICS content unchanged", room_id=room_id)
        elif result["status"] == SyncStatus.ERROR:
            logger.error("ICS sync failed", room_id=room_id, error=result.get("error"))
        else:
            logger.debug(
                "ICS sync skipped", room_id=room_id, reason=result.get("reason")
            )

    except Exception as e:
        logger.error("Unexpected error during ICS sync", room_id=room_id, error=str(e))


@shared_task
@asynctask
async def sync_all_ics_calendars():
    try:
        logger.info("Starting sync for all ICS-enabled rooms")

        ics_enabled_rooms = await rooms_controller.get_ics_enabled()
        logger.info(f"Found {len(ics_enabled_rooms)} rooms with ICS enabled")

        for room in ics_enabled_rooms:
            if not _should_sync(room):
                logger.debug("Skipping room, not time to sync yet", room_id=room.id)
                continue

            sync_room_ics.delay(room.id)

        logger.info("Queued sync tasks for all eligible rooms")

    except Exception as e:
        logger.error("Error in sync_all_ics_calendars", error=str(e))


def _should_sync(room) -> bool:
    if not room.ics_last_sync:
        return True

    time_since_sync = datetime.now(timezone.utc) - room.ics_last_sync
    return time_since_sync.total_seconds() >= room.ics_fetch_interval


MEETING_DEFAULT_DURATION = timedelta(hours=1)


async def create_upcoming_meetings_for_event(event, create_window, room_id, room):
    if event.start_time <= create_window:
        return
    existing_meeting = await meetings_controller.get_by_calendar_event(event.id)

    if existing_meeting:
        return

    logger.info(
        "Pre-creating meeting for calendar event",
        room_id=room_id,
        event_id=event.id,
        event_title=event.title,
    )

    try:
        end_date = event.end_time or (event.start_time + MEETING_DEFAULT_DURATION)

        whereby_meeting = await create_meeting(
            event.title or "Scheduled Meeting",
            end_date=end_date,
            room=room,
        )
        await upload_logo(whereby_meeting["roomName"], "./images/logo.png")

        meeting = await meetings_controller.create(
            id=whereby_meeting["meetingId"],
            room_name=whereby_meeting["roomName"],
            room_url=whereby_meeting["roomUrl"],
            host_room_url=whereby_meeting["hostRoomUrl"],
            start_date=datetime.fromisoformat(whereby_meeting["startDate"]),
            end_date=datetime.fromisoformat(whereby_meeting["endDate"]),
            user_id=room.user_id,
            room=room,
            calendar_event_id=event.id,
            calendar_metadata={
                "title": event.title,
                "description": event.description,
                "attendees": event.attendees,
            },
        )

        logger.info(
            "Meeting pre-created successfully",
            meeting_id=meeting.id,
            event_id=event.id,
        )

    except Exception as e:
        logger.error(
            "Failed to pre-create meeting",
            room_id=room_id,
            event_id=event.id,
            error=str(e),
        )


@shared_task
@asynctask
async def create_upcoming_meetings():
    try:
        logger.info("Starting creation of upcoming meetings")

        ics_enabled_rooms = await rooms_controller.get_ics_enabled()
        now = datetime.now(timezone.utc)
        create_window = now - timedelta(minutes=6)

        for room in ics_enabled_rooms:
            events = await calendar_events_controller.get_upcoming(
                room.id,
                minutes_ahead=7,
            )

            for event in events:
                await create_upcoming_meetings_for_event(
                    event, create_window, room.id, room
                )
        logger.info("Completed pre-creation check for upcoming meetings")

    except Exception as e:
        logger.error("Error in create_upcoming_meetings", error=str(e))
