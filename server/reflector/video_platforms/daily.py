import base64
import hmac
from datetime import datetime
from hashlib import sha256
from http import HTTPStatus
from typing import Any, Dict, Optional

import httpx

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
    TIMEOUT = 10
    BASE_URL = "https://api.daily.co/v1"
    TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
    RECORDING_NONE: RecordingType = "none"
    RECORDING_CLOUD: RecordingType = "cloud"

    def __init__(self, config: VideoPlatformConfig):
        super().__init__(config)
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

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

        data = {
            "name": room_name,
            "privacy": "private" if room.is_locked else "public",
            "properties": {
                "enable_recording": "raw-tracks"
                if room.recording_type != self.RECORDING_NONE
                else False,
                "enable_chat": True,
                "enable_screenshare": True,
                "start_video_off": False,
                "start_audio_off": False,
                "exp": int(end_date.timestamp()),
            },
        }

        # Only configure recordings_bucket if recording is enabled
        if room.recording_type != self.RECORDING_NONE:
            daily_storage = get_dailyco_storage()
            assert daily_storage.bucket_name, "S3 bucket must be configured"
            data["properties"]["recordings_bucket"] = {
                "bucket_name": daily_storage.bucket_name,
                "bucket_region": daily_storage.region,
                "assume_role_arn": daily_storage.role_credential,
                "allow_api_access": True,
            }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/rooms",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            if response.status_code >= 400:
                logger.error(
                    "Daily.co API error",
                    status_code=response.status_code,
                    response_body=response.text,
                    request_data=data,
                )
            response.raise_for_status()
            result = response.json()

        room_url = result["url"]

        return MeetingData(
            meeting_id=result["id"],
            room_name=result["name"],
            room_url=room_url,
            host_room_url=room_url,
            platform=self.PLATFORM_NAME,
            extra_data=result,
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
        """Get room presence/session data for a Daily.co room.

        Example response:
        {
          "total_count": 1,
          "data": [
            {
              "room": "w2pp2cf4kltgFACPKXmX",
              "id": "d61cd7b2-a273-42b4-89bd-be763fd562c1",
              "userId": "pbZ+ismP7dk=",
              "userName": "Moishe",
              "joinTime": "2023-01-01T20:53:19.000Z",
              "duration": 2312
            }
          ]
        }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/rooms/{room_name}/presence",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def get_meeting_participants(self, meeting_id: str) -> Dict[str, Any]:
        """Get participant data for a specific Daily.co meeting.

        Example response:
        {
          "data": [
            {
              "user_id": "4q47OTmqa/w=",
              "participant_id": "d61cd7b2-a273-42b4-89bd-be763fd562c1",
              "user_name": "Lindsey",
              "join_time": 1672786813,
              "duration": 150
            },
            {
              "user_id": "pbZ+ismP7dk=",
              "participant_id": "b3d56359-14d7-46af-ac8b-18f8c991f5f6",
              "user_name": "Moishe",
              "join_time": 1672786797,
              "duration": 165
            }
          ]
        }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/meetings/{meeting_id}/participants",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def get_recording(self, recording_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/recordings/{recording_id}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def delete_room(self, room_name: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/rooms/{room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            return response.status_code in (HTTPStatus.OK, HTTPStatus.NOT_FOUND)

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        return True

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        """Verify Daily.co webhook signature.

        Daily.co uses:
        - X-Webhook-Signature header
        - X-Webhook-Timestamp header
        - Signature format: HMAC-SHA256(base64_decode(secret), timestamp + '.' + body)
        - Result is base64 encoded
        """
        if not signature or not timestamp:
            return False

        try:
            secret_bytes = base64.b64decode(self.config.webhook_secret)

            signed_content = timestamp.encode() + b"." + body

            expected = hmac.new(secret_bytes, signed_content, sha256).digest()
            expected_b64 = base64.b64encode(expected).decode()

            return hmac.compare_digest(expected_b64, signature)
        except Exception as e:
            logger.error("Daily.co webhook signature verification failed", exc_info=e)
            return False

    async def create_meeting_token(
        self,
        room_name: DailyRoomName,
        user_id: Optional[str] = None,
    ) -> str:
        data = {"properties": {"room_name": room_name}}

        if user_id:
            data["properties"]["user_id"] = user_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/meeting-tokens",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()["token"]
