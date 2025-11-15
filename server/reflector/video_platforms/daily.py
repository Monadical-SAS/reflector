from datetime import datetime
from typing import Any, Dict, Optional

from reflector.dailyco_api import (
    CreateMeetingTokenRequest,
    CreateRoomRequest,
    DailyApiClient,
    MeetingTokenProperties,
    RecordingsBucketConfig,
    RoomProperties,
    verify_webhook_signature,
)
from reflector.db.daily_participant_sessions import (
    daily_participant_sessions_controller,
)
from reflector.db.rooms import Room
from reflector.logger import logger
from reflector.storage import get_dailyco_storage

from ..schemas.platform import Platform
from ..utils.daily import DailyRoomName
from ..utils.string import NonEmptyString
from .base import ROOM_PREFIX_SEPARATOR, VideoPlatformClient
from .models import MeetingData, RecordingType, SessionData, VideoPlatformConfig


class DailyClient(VideoPlatformClient):
    PLATFORM_NAME: Platform = "daily"
    TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
    RECORDING_NONE: RecordingType = "none"
    RECORDING_CLOUD: RecordingType = "cloud"

    def __init__(self, config: VideoPlatformConfig):
        super().__init__(config)
        # Initialize dailyco_api client
        self._api_client = DailyApiClient(
            api_key=config.api_key,
            webhook_secret=config.webhook_secret,
            timeout=10.0,
        )

    async def create_meeting(
        self, room_name_prefix: NonEmptyString, end_date: datetime, room: Room
    ) -> MeetingData:
        """
        Daily.co rooms vs meetings:
        - We create a NEW Daily.co room for each Reflector meeting
        - Daily.co meeting/session starts automatically when first participant joins
        - Room auto-deletes after exp time
        - Meeting.room_name stores the timestamped Daily.co room name
        """
        timestamp = datetime.now().strftime(self.TIMESTAMP_FORMAT)
        room_name = f"{room_name_prefix}{ROOM_PREFIX_SEPARATOR}{timestamp}"

        # Build room properties
        properties = RoomProperties(
            enable_recording="raw-tracks"
            if room.recording_type != self.RECORDING_NONE
            else False,
            enable_chat=True,
            enable_screenshare=True,
            start_video_off=False,
            start_audio_off=False,
            exp=int(end_date.timestamp()),
        )

        # Only configure recordings_bucket if recording is enabled
        if room.recording_type != self.RECORDING_NONE:
            daily_storage = get_dailyco_storage()
            assert daily_storage.bucket_name, "S3 bucket must be configured"
            properties.recordings_bucket = RecordingsBucketConfig(
                bucket_name=daily_storage.bucket_name,
                bucket_region=daily_storage.region,
                assume_role_arn=daily_storage.role_credential,
                allow_api_access=True,
            )

        # Create room request
        request = CreateRoomRequest(
            name=room_name,
            privacy="private" if room.is_locked else "public",
            properties=properties,
        )

        # Call API
        result = await self._api_client.create_room(request)

        return MeetingData(
            meeting_id=result.id,
            room_name=result.name,
            room_url=result.url,
            host_room_url=result.url,
            platform=self.PLATFORM_NAME,
            extra_data=result.model_dump(),
        )

    async def get_room_sessions(self, room_name: str) -> list[SessionData]:
        """Get room session history from database (webhook-stored sessions).

        Daily.co doesn't provide historical session API, so we query our database
        where participant.joined/left webhooks are stored.
        """
        from reflector.db.meetings import meetings_controller

        meeting = await meetings_controller.get_by_room_name(room_name)
        if not meeting:
            return []

        sessions = await daily_participant_sessions_controller.get_by_meeting(
            meeting.id
        )

        return [
            SessionData(
                session_id=s.id,
                started_at=s.joined_at,
                ended_at=s.left_at,
            )
            for s in sessions
        ]

    async def get_room_presence(self, room_name: str) -> Dict[str, Any]:
        """Get room presence/session data for a Daily.co room."""
        result = await self._api_client.get_room_presence(room_name)
        return result.model_dump()

    async def get_meeting_participants(self, meeting_id: str) -> Dict[str, Any]:
        """Get participant data for a specific Daily.co meeting."""
        result = await self._api_client.get_meeting_participants(meeting_id)
        return result.model_dump()

    async def get_recording(self, recording_id: str) -> Dict[str, Any]:
        result = await self._api_client.get_recording(recording_id)
        return result.model_dump()

    async def delete_room(self, room_name: str) -> bool:
        """Delete a room (idempotent - succeeds even if room doesn't exist)."""
        await self._api_client.delete_room(room_name)
        return True

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        return True

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        """Verify Daily.co webhook signature using dailyco_api module."""
        if not self.config.webhook_secret:
            logger.warning("Webhook secret not configured")
            return False

        return verify_webhook_signature(
            body=body,
            signature=signature,
            timestamp=timestamp or "",
            webhook_secret=self.config.webhook_secret,
        )

    async def create_meeting_token(
        self,
        room_name: DailyRoomName,
        enable_recording: bool,
        user_id: Optional[str] = None,
    ) -> str:
        properties = MeetingTokenProperties(
            room_name=room_name,
            user_id=user_id,
            start_cloud_recording=enable_recording,
            enable_recording_ui=not enable_recording if enable_recording else True,
        )

        request = CreateMeetingTokenRequest(properties=properties)
        result = await self._api_client.create_meeting_token(request)
        return result.token

    async def close(self):
        """Clean up API client resources."""
        await self._api_client.close()
