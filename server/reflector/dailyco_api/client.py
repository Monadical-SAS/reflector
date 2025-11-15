"""
Daily.co API Client

Complete async client for Daily.co REST API with Pydantic models.

Reference: https://docs.daily.co/reference/rest-api
"""

from http import HTTPStatus
from typing import Any, Dict, List, Optional

import httpx
import structlog

from .requests import (
    CreateMeetingTokenRequest,
    CreateRoomRequest,
    CreateWebhookRequest,
    UpdateWebhookRequest,
)
from .responses import (
    MeetingParticipantsResponse,
    MeetingResponse,
    MeetingTokenResponse,
    RecordingResponse,
    RoomPresenceResponse,
    RoomResponse,
    WebhookResponse,
)

logger = structlog.get_logger(__name__)


class DailyApiClient:
    """
    Complete async client for Daily.co REST API.

    Usage:
        # Direct usage
        client = DailyApiClient(api_key="your_api_key")
        room = await client.create_room(CreateRoomRequest(name="my-room"))
        await client.close()  # Clean up when done

        # Context manager (recommended)
        async with DailyApiClient(api_key="your_api_key") as client:
            room = await client.create_room(CreateRoomRequest(name="my-room"))
    """

    BASE_URL = "https://api.daily.co/v1"
    DEFAULT_TIMEOUT = 10.0

    def __init__(
        self,
        api_key: str,
        webhook_secret: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Daily.co API client.

        Args:
            api_key: Daily.co API key (Bearer token)
            webhook_secret: Base64-encoded HMAC secret for webhook verification.
                Must match the 'hmac' value provided when creating webhooks.
                Generate with: base64.b64encode(os.urandom(32)).decode()
            timeout: Default request timeout in seconds
            base_url: Override base URL (for testing)
        """
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.timeout = timeout
        self.base_url = base_url or self.BASE_URL

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _handle_response(
        self, response: httpx.Response, operation: str
    ) -> Dict[str, Any]:
        """
        Handle API response with error logging.

        Args:
            response: HTTP response
            operation: Operation name for logging (e.g., "create_room")

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If request failed
        """
        if response.status_code >= 400:
            logger.error(
                f"Daily.co API error: {operation}",
                status_code=response.status_code,
                response_body=response.text,
                url=str(response.url),
            )

        response.raise_for_status()
        return response.json()

    # ============================================================================
    # ROOMS
    # ============================================================================

    async def create_room(self, request: CreateRoomRequest) -> RoomResponse:
        """
        Create a new Daily.co room.

        Reference: https://docs.daily.co/reference/rest-api/rooms/create-room

        Args:
            request: Room creation request with name, privacy, and properties

        Returns:
            Created room data including URL and ID

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/rooms",
            headers=self.headers,
            json=request.model_dump(exclude_none=True),
        )

        data = await self._handle_response(response, "create_room")
        return RoomResponse(**data)

    async def get_room(self, room_name: str) -> RoomResponse:
        """
        Get room configuration.

        Reference: https://docs.daily.co/reference/rest-api/rooms/get-room-configuration

        Args:
            room_name: Daily.co room name

        Returns:
            Room configuration data

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/rooms/{room_name}",
            headers=self.headers,
        )

        data = await self._handle_response(response, "get_room")
        return RoomResponse(**data)

    async def get_room_presence(self, room_name: str) -> RoomPresenceResponse:
        """
        Get current participants in a room (real-time presence).

        Reference: https://docs.daily.co/reference/rest-api/rooms/get-room-presence

        Args:
            room_name: Daily.co room name

        Returns:
            List of currently present participants with join time and duration

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/rooms/{room_name}/presence",
            headers=self.headers,
        )

        data = await self._handle_response(response, "get_room_presence")
        return RoomPresenceResponse(**data)

    async def delete_room(self, room_name: str) -> None:
        """
        Delete a room (idempotent - succeeds even if room doesn't exist).

        Reference: https://docs.daily.co/reference/rest-api/rooms/delete-room

        Args:
            room_name: Daily.co room name

        Raises:
            httpx.HTTPStatusError: If API request fails (except 404)
        """
        client = await self._get_client()
        response = await client.delete(
            f"{self.base_url}/rooms/{room_name}",
            headers=self.headers,
        )

        # Idempotent delete - 404 means already deleted
        if response.status_code == HTTPStatus.NOT_FOUND:
            logger.debug("Room not found (already deleted)", room_name=room_name)
            return

        await self._handle_response(response, "delete_room")

    # ============================================================================
    # MEETINGS
    # ============================================================================

    async def get_meeting(self, meeting_id: str) -> MeetingResponse:
        """
        Get full meeting information including participants.

        Reference: https://docs.daily.co/reference/rest-api/meetings/get-meeting-information

        Args:
            meeting_id: Daily.co meeting/session ID

        Returns:
            Meeting metadata including room, duration, participants, and status

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/meetings/{meeting_id}",
            headers=self.headers,
        )

        data = await self._handle_response(response, "get_meeting")
        return MeetingResponse(**data)

    async def get_meeting_participants(
        self,
        meeting_id: str,
        limit: Optional[int] = None,
        joined_after: Optional[str] = None,
        joined_before: Optional[str] = None,
    ) -> MeetingParticipantsResponse:
        """
        Get historical participant data from a completed meeting (paginated).

        Reference: https://docs.daily.co/reference/rest-api/meetings/get-meeting-participants

        Args:
            meeting_id: Daily.co meeting/session ID
            limit: Maximum number of participant records to return
            joined_after: Return participants who joined after this participant_id
            joined_before: Return participants who joined before this participant_id

        Returns:
            List of participants with join times and duration

        Raises:
            httpx.HTTPStatusError: If API request fails (404 when no more participants)

        Note:
            For pagination, use joined_after with the last participant_id from previous response.
            Returns 404 when no more participants remain.
        """
        params = {}
        if limit is not None:
            params["limit"] = limit
        if joined_after is not None:
            params["joined_after"] = joined_after
        if joined_before is not None:
            params["joined_before"] = joined_before

        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/meetings/{meeting_id}/participants",
            headers=self.headers,
            params=params,
        )

        data = await self._handle_response(response, "get_meeting_participants")
        return MeetingParticipantsResponse(**data)

    # ============================================================================
    # RECORDINGS
    # ============================================================================

    async def get_recording(self, recording_id: str) -> RecordingResponse:
        """
        Get recording metadata and status.

        Reference: https://docs.daily.co/reference/rest-api/recordings/get-recording-info

        Args:
            recording_id: Daily.co recording ID

        Returns:
            Recording metadata including status, duration, and S3 info

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/recordings/{recording_id}",
            headers=self.headers,
        )

        data = await self._handle_response(response, "get_recording")
        return RecordingResponse(**data)

    # ============================================================================
    # MEETING TOKENS
    # ============================================================================

    async def create_meeting_token(
        self, request: CreateMeetingTokenRequest
    ) -> MeetingTokenResponse:
        """
        Create a meeting token for participant authentication.

        Reference: https://docs.daily.co/reference/rest-api/meeting-tokens/create-meeting-token

        Args:
            request: Token properties including room name, user_id, permissions

        Returns:
            JWT meeting token

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/meeting-tokens",
            headers=self.headers,
            json=request.model_dump(exclude_none=True),
        )

        data = await self._handle_response(response, "create_meeting_token")
        return MeetingTokenResponse(**data)

    # ============================================================================
    # WEBHOOKS
    # ============================================================================

    async def list_webhooks(self) -> List[WebhookResponse]:
        """
        List all configured webhooks for this account.

        Reference: https://docs.daily.co/reference/rest-api/webhooks/list-webhooks

        Returns:
            List of webhook configurations

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/webhooks",
            headers=self.headers,
        )

        data = await self._handle_response(response, "list_webhooks")

        # Daily.co returns array directly (not paginated)
        if isinstance(data, list):
            return [WebhookResponse(**wh) for wh in data]

        # Future-proof: handle potential pagination envelope
        if isinstance(data, dict) and "data" in data:
            return [WebhookResponse(**wh) for wh in data["data"]]

        logger.warning("Unexpected webhook list response format", data=data)
        return []

    async def create_webhook(self, request: CreateWebhookRequest) -> WebhookResponse:
        """
        Create a new webhook subscription.

        Reference: https://docs.daily.co/reference/rest-api/webhooks/create-webhook

        Args:
            request: Webhook configuration with URL, event types, and HMAC secret

        Returns:
            Created webhook with UUID and state

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/webhooks",
            headers=self.headers,
            json=request.model_dump(exclude_none=True),
        )

        data = await self._handle_response(response, "create_webhook")
        return WebhookResponse(**data)

    async def update_webhook(
        self, webhook_uuid: str, request: UpdateWebhookRequest
    ) -> WebhookResponse:
        """
        Update webhook configuration.

        Note: Daily.co may not support PATCH for all fields.
        Common pattern is delete + recreate.

        Reference: https://docs.daily.co/reference/rest-api/webhooks

        Args:
            webhook_uuid: Webhook UUID to update
            request: Updated webhook configuration

        Returns:
            Updated webhook configuration

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        client = await self._get_client()
        response = await client.patch(
            f"{self.base_url}/webhooks/{webhook_uuid}",
            headers=self.headers,
            json=request.model_dump(exclude_none=True),
        )

        data = await self._handle_response(response, "update_webhook")
        return WebhookResponse(**data)

    async def delete_webhook(self, webhook_uuid: str) -> None:
        """
        Delete a webhook.

        Reference: https://docs.daily.co/reference/rest-api/webhooks/delete-webhook

        Args:
            webhook_uuid: Webhook UUID to delete

        Raises:
            httpx.HTTPStatusError: If webhook not found or deletion fails
        """
        client = await self._get_client()
        response = await client.delete(
            f"{self.base_url}/webhooks/{webhook_uuid}",
            headers=self.headers,
        )

        await self._handle_response(response, "delete_webhook")

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    async def find_webhook_by_url(self, url: str) -> Optional[WebhookResponse]:
        """
        Find a webhook by its URL.

        Args:
            url: Webhook endpoint URL to search for

        Returns:
            Webhook if found, None otherwise
        """
        webhooks = await self.list_webhooks()
        for webhook in webhooks:
            if webhook.url == url:
                return webhook
        return None

    async def find_webhooks_by_pattern(self, pattern: str) -> List[WebhookResponse]:
        """
        Find webhooks matching a URL pattern (e.g., 'ngrok').

        Args:
            pattern: String to match in webhook URLs

        Returns:
            List of matching webhooks
        """
        webhooks = await self.list_webhooks()
        return [wh for wh in webhooks if pattern in wh.url]
