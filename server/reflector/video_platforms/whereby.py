import hmac
import json
import re
import time
from datetime import datetime
from hashlib import sha256
from typing import Optional

import httpx

from reflector.db.rooms import Room
from reflector.storage import get_whereby_storage

from ..schemas.platform import WHEREBY_PLATFORM, Platform
from ..utils.string import NonEmptyString
from .base import VideoPlatformClient
from .models import MeetingData, SessionData, VideoPlatformConfig
from .whereby_utils import whereby_room_name_prefix


class WherebyClient(VideoPlatformClient):
    PLATFORM_NAME: Platform = WHEREBY_PLATFORM
    TIMEOUT = 10  # seconds
    MAX_ELAPSED_TIME = 60 * 1000  # 1 minute in milliseconds

    def __init__(self, config: VideoPlatformConfig):
        super().__init__(config)
        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {config.api_key}",
        }

    async def create_meeting(
        self, room_name_prefix: NonEmptyString, end_date: datetime, room: Room
    ) -> MeetingData:
        data = {
            "isLocked": room.is_locked,
            "roomNamePrefix": whereby_room_name_prefix(room_name_prefix),
            "roomNamePattern": "uuid",
            "roomMode": room.room_mode,
            "endDate": end_date.isoformat(),
            "fields": ["hostRoomUrl"],
        }

        if room.recording_type == "cloud":
            # Get storage config for passing credentials to Whereby API
            whereby_storage = get_whereby_storage()
            key_id, secret = whereby_storage.key_credentials
            data["recording"] = {
                "type": room.recording_type,
                "destination": {
                    "provider": "s3",
                    "bucket": whereby_storage.bucket_name,
                    "accessKeyId": key_id,
                    "accessKeySecret": secret,
                    "fileFormat": "mp4",
                },
                "startTrigger": room.recording_trigger,
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.api_url}/meetings",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

        return MeetingData(
            meeting_id=result["meetingId"],
            room_name=result["roomName"],
            room_url=result["roomUrl"],
            host_room_url=result["hostRoomUrl"],
            platform=self.PLATFORM_NAME,
            extra_data=result,
        )

    async def get_room_sessions(self, room_name: str) -> list[SessionData]:
        """Get room session history from Whereby API.

        Whereby API returns: [{"sessionId": "...", "startedAt": "...", "endedAt": "..." | null}, ...]
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.config.api_url}/insights/room-sessions?roomName={room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            results = response.json().get("results", [])

            return [
                SessionData(
                    session_id=s["sessionId"],
                    started_at=datetime.fromisoformat(
                        s["startedAt"].replace("Z", "+00:00")
                    ),
                    ended_at=datetime.fromisoformat(s["endedAt"].replace("Z", "+00:00"))
                    if s.get("endedAt")
                    else None,
                )
                for s in results
            ]

    async def delete_room(self, room_name: str) -> bool:
        return True

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        async with httpx.AsyncClient() as client:
            with open(logo_path, "rb") as f:
                response = await client.put(
                    f"{self.config.api_url}/rooms/{room_name}/theme/logo",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                    },
                    timeout=self.TIMEOUT,
                    files={"image": f},
                )
                response.raise_for_status()
        return True

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        if not signature:
            return False

        matches = re.match(r"t=(.*),v1=(.*)", signature)
        if not matches:
            return False

        ts, sig = matches.groups()

        current_time = int(time.time() * 1000)
        diff_time = current_time - int(ts) * 1000
        if diff_time >= self.MAX_ELAPSED_TIME:
            return False

        body_dict = json.loads(body)
        signed_payload = f"{ts}.{json.dumps(body_dict, separators=(',', ':'))}"
        hmac_obj = hmac.new(
            self.config.webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            sha256,
        )
        expected_signature = hmac_obj.hexdigest()

        try:
            return hmac.compare_digest(
                expected_signature.encode("utf-8"), sig.encode("utf-8")
            )
        except Exception:
            return False
