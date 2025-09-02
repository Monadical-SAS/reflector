import hmac
import time
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Optional

import jwt

from reflector.db.rooms import Room
from reflector.settings import settings
from reflector.utils import generate_uuid4

from ..base import MeetingData, VideoPlatformClient


class JitsiClient(VideoPlatformClient):
    """Jitsi Meet video platform implementation."""

    PLATFORM_NAME = "jitsi"

    def _generate_jwt(self, room: str, moderator: bool, exp: datetime) -> str:
        """Generate JWT token for Jitsi Meet room access."""
        if not settings.JITSI_JWT_SECRET:
            raise ValueError("JITSI_JWT_SECRET is required for JWT generation")

        payload = {
            "aud": settings.JITSI_JWT_AUDIENCE,
            "iss": settings.JITSI_JWT_ISSUER,
            "sub": settings.JITSI_DOMAIN,
            "room": room,
            "exp": int(exp.timestamp()),
            "context": {
                "user": {
                    "name": "Reflector User",
                    "moderator": moderator,
                },
                "features": {
                    "recording": True,
                    "livestreaming": False,
                    "transcription": True,
                },
            },
        }

        return jwt.encode(payload, settings.JITSI_JWT_SECRET, algorithm="HS256")

    async def create_meeting(
        self, room_name_prefix: str, end_date: datetime, room: Room
    ) -> MeetingData:
        """Create a Jitsi Meet room with JWT authentication."""
        # Generate unique room name
        jitsi_room = f"reflector-{room.name}-{int(time.time())}"

        # Generate JWT tokens
        user_jwt = self._generate_jwt(room=jitsi_room, moderator=False, exp=end_date)
        host_jwt = self._generate_jwt(room=jitsi_room, moderator=True, exp=end_date)

        # Build room URLs with JWT tokens
        room_url = f"https://{settings.JITSI_DOMAIN}/{jitsi_room}?jwt={user_jwt}"
        host_room_url = f"https://{settings.JITSI_DOMAIN}/{jitsi_room}?jwt={host_jwt}"

        return MeetingData(
            meeting_id=generate_uuid4(),
            room_name=jitsi_room,
            room_url=room_url,
            host_room_url=host_room_url,
            platform=self.PLATFORM_NAME,
            extra_data={
                "user_jwt": user_jwt,
                "host_jwt": host_jwt,
                "domain": settings.JITSI_DOMAIN,
            },
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """Get room sessions (mock implementation - Jitsi doesn't provide sessions API)."""
        return {
            "roomName": room_name,
            "sessions": [
                {
                    "sessionId": generate_uuid4(),
                    "startTime": datetime.utcnow().isoformat(),
                    "participants": [],
                    "isActive": True,
                }
            ],
        }

    async def delete_room(self, room_name: str) -> bool:
        """Delete room (no-op - Jitsi rooms auto-expire with JWT expiration)."""
        return True

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """Upload logo (no-op - custom branding handled via Jitsi server config)."""
        return True

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        """Verify webhook signature for Prosody event-sync webhooks."""
        if not signature or not self.config.webhook_secret:
            return False

        try:
            expected = hmac.new(
                self.config.webhook_secret.encode(), body, sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False
