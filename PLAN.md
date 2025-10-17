# Technical Specification: Multi-Provider Video Platform Integration

**Version:** 1.0
**Status:** Ready for Implementation
**Target:** Steps 1-3 of Video Platform Migration
**Estimated Effort:** 12-16 hours (senior engineer)
**Branch Base:** Current `main` branch

---

## Executive Summary

This document provides a comprehensive technical specification for implementing multi-provider video platform support in Reflector, focusing on abstracting the existing Whereby integration and adding Daily.co as a second provider. The implementation follows a phased approach ensuring zero downtime, backward compatibility, and feature parity between providers.

**Scope:**
- **Phase 1:** Extract existing Whereby implementation into reusable patterns
- **Phase 2:** Create provider abstraction layer maintaining current functionality
- **Phase 3:** Implement Daily.co provider with feature parity to Whereby

**Out of Scope:**
- Multi-track audio processing (Phase 4 - future work)
- Jitsi integration (Phase 5 - future work)
- Platform selection UI (controlled via environment variables)
- Advanced Daily.co features (presence API, raw-tracks recording)

---

## Business Context

### Problem Statement

Reflector currently has a hard dependency on Whereby for video conferencing. This creates:
1. **Vendor lock-in risk** - Single point of failure for core functionality
2. **Cost optimization limitations** - Cannot leverage competitive pricing
3. **Feature constraints** - Limited to Whereby's feature set
4. **Scalability concerns** - Dependent on Whereby's infrastructure reliability

### Business Goals

1. **Risk Mitigation:** Enable platform switching without code changes
2. **Cost Flexibility:** Allow deployment-specific provider selection
3. **Feature Expansion:** Prepare for future multi-track diarization (Daily.co raw-tracks)
4. **Architectural Cleanliness:** Establish patterns for future provider additions (Jitsi)

### Success Criteria

- ✅ Existing Whereby installations continue working unchanged
- ✅ New installations can choose Daily.co via environment variable
- ✅ Zero data migration required for existing deployments
- ✅ Recording processing pipeline unchanged
- ✅ Transcription quality identical between providers
- ✅ <2% performance overhead from abstraction layer
- ✅ Test coverage >90% for platform abstraction

---

## Architecture Overview

### Current Architecture (Whereby-only)

```
┌─────────────────────────────────────────────────────────┐
│ Frontend                                                 │
│  └─ RoomPage.tsx                                        │
│      └─ <whereby-embed> web component                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Backend                                                  │
│  └─ rooms.py (direct Whereby API calls)                │
│  └─ whereby.py (webhook handler)                       │
│  └─ process.py (S3-based recording ingestion)         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ External Services                                        │
│  ├─ Whereby API                                         │
│  ├─ Whereby Webhooks → SQS → recordings                │
│  └─ S3 (Whereby uploads directly)                      │
└─────────────────────────────────────────────────────────┘
```

### Target Architecture (Multi-provider)

```
┌─────────────────────────────────────────────────────────┐
│ Frontend                                                 │
│  └─ RoomContainer.tsx (platform router)                │
│      ├─ WherebyRoom.tsx                                │
│      └─ DailyRoom.tsx                                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ Backend - Platform Abstraction Layer                    │
│  ├─ VideoPlatformClient (ABC)                          │
│  ├─ PlatformFactory                                     │
│  ├─ PlatformRegistry                                    │
│  └─ Platform Implementations:                           │
│      ├─ WherebyClient                                   │
│      ├─ DailyClient                                     │
│      └─ MockClient (testing)                           │
└─────────────────────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
┌───────────────────────┐  ┌──────────────────────┐
│ Whereby Services      │  │ Daily.co Services    │
│  ├─ Whereby API       │  │  ├─ Daily.co API     │
│  ├─ Webhooks          │  │  ├─ Webhooks         │
│  └─ S3 Direct Upload  │  │  └─ Download URLs    │
└───────────────────────┘  └──────────────────────┘
```

### Key Architectural Principles

1. **Single Responsibility:** Each provider implements only platform-specific logic
2. **Open/Closed:** New providers can be added without modifying existing code
3. **Liskov Substitution:** All providers are interchangeable via base interface
4. **Dependency Inversion:** Business logic depends on abstraction, not implementations
5. **Interface Segregation:** Platform interface contains only universally needed methods

---

## Phase 1: Analysis & Extraction (2 hours)

### Objective
Understand current Whereby implementation patterns to inform abstraction design.

### Step 1.1: Audit Current Whereby Implementation

**Files to analyze:**

```bash
# Backend
server/reflector/views/rooms.py          # Room/meeting creation logic
server/reflector/views/whereby.py        # Webhook handler
server/reflector/worker/process.py       # Recording processing

# Frontend
www/app/[roomName]/page.tsx              # Room page component
www/app/(app)/rooms/page.tsx             # Room creation form

# Database
server/reflector/db/rooms.py             # Room model
server/reflector/db/meetings.py          # Meeting model
server/reflector/db/recordings.py        # Recording model
```

**Create analysis document:**

```markdown
# Whereby Integration Analysis

## API Calls Made
1. Create meeting: POST to whereby.dev/v1/meetings
2. Required fields: endDate, roomMode, fields
3. Response structure: { meetingId, roomUrl, hostRoomUrl }

## Webhook Events Received
1. room.client.joined - participant count++
2. room.client.left - participant count--

## Recording Flow
1. Whereby uploads MP4 to S3 bucket (direct)
2. S3 event → SQS queue
3. Worker polls SQS → downloads from S3
4. Processing pipeline: transcription → diarization → summarization

## Data Stored
- Room: whereby-specific fields (if any)
- Meeting: meetingId, roomUrl, hostRoomUrl
- Recording: S3 bucket, object_key

## Frontend Integration
- <whereby-embed> web component
- SDK loaded via dynamic import
- Custom focus management for consent dialog
- Events: leave, ready
```

### Step 1.2: Identify Abstraction Points

**Create abstraction requirements document:**

```markdown
# Platform Abstraction Requirements

## Must Abstract
1. Meeting creation (different APIs, different request/response formats)
2. Webhook signature verification (different algorithms/formats)
3. Recording ingestion (S3 direct vs download URL)
4. Frontend room component (web component vs iframe)

## Can Remain Concrete
1. Recording processing pipeline (same for all providers)
2. Transcription/diarization (provider-agnostic)
3. Database schema (add platform field, rest unchanged)
4. User consent flow (same UI/UX)

## Platform-Specific Differences
| Feature | Whereby | Daily.co |
|---------|---------|----------|
| Meeting creation | REST API | REST API |
| Authentication | API key header | Bearer token |
| Recording delivery | S3 upload | Download URL |
| Frontend SDK | Web component | iframe/React SDK |
| Webhook signature | HMAC + timestamp | HMAC only |
| Room expiration | Automatic | Manual or via exp field |
```

### Step 1.3: Define Standard Data Models

**Create `server/reflector/platform_types.py` (separate file to avoid circular imports):**

```python
"""Platform type definitions.

Separate file to prevent circular import issues when db models and
video platform code need to reference the Platform type.
"""

from typing import Literal

Platform = Literal["whereby", "daily"]
```

**Create `server/reflector/video_platforms/models.py`:**

```python
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from reflector.platform_types import Platform


class MeetingData(BaseModel):
    """Standardized meeting data returned by all providers."""

    platform: Platform
    meeting_id: str = Field(description="Platform-specific meeting identifier")
    room_url: str = Field(description="URL for participants to join")
    host_room_url: str = Field(description="URL for hosts (may be same as room_url)")
    room_name: str = Field(description="Human-readable room name")
    start_date: Optional[datetime] = None
    end_date: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "whereby",
                "meeting_id": "12345678",
                "room_url": "https://subdomain.whereby.com/room-20251008120000",
                "host_room_url": "https://subdomain.whereby.com/room-20251008120000?roomKey=abc123",
                "room_name": "room-20251008120000",
                "end_date": "2025-10-08T14:00:00Z"
            }
        }


class VideoPlatformConfig(BaseModel):
    """Platform-agnostic configuration model."""

    api_key: str
    webhook_secret: Optional[str] = None
    subdomain: Optional[str] = None  # Whereby/Daily subdomain
    s3_bucket: Optional[str] = None
    s3_region: str = "us-west-2"
    # Whereby uses access keys, Daily uses IAM role
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_role_arn: Optional[str] = None


class RecordingType:
    """Recording type constants."""
    NONE = "none"
    LOCAL = "local"
    CLOUD = "cloud"
```

### Deliverables
- [ ] Whereby integration analysis document
- [ ] Abstraction requirements document
- [ ] Standard data models in `models.py`
- [ ] List of files requiring modification

---

## Phase 2: Platform Abstraction Layer (4-5 hours)

### Objective
Create a clean abstraction layer without breaking existing Whereby functionality.

### Step 2.1: Create Base Abstraction

**File: `server/reflector/video_platforms/__init__.py`**

```python
"""Video platform abstraction layer."""

from .base import VideoPlatformClient
from .models import Platform, MeetingData, VideoPlatformConfig
from .factory import create_platform_client, get_platform_config
from .registry import register_platform, get_platform_client_class

__all__ = [
    "VideoPlatformClient",
    "Platform",
    "MeetingData",
    "VideoPlatformConfig",
    "create_platform_client",
    "get_platform_config",
    "register_platform",
    "get_platform_client_class",
]
```

**File: `server/reflector/video_platforms/base.py`**

```python
"""Abstract base class for video platform clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

from .models import MeetingData, Platform, VideoPlatformConfig

# Import Room with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from reflector.db.rooms import Room


class VideoPlatformClient(ABC):
    """
    Abstract base class for video platform integrations.

    All video platform providers (Whereby, Daily.co, etc.) must implement
    this interface to ensure consistent behavior across the application.

    Design Principles:
    - Methods should be platform-agnostic in their contracts
    - Return standardized data models (MeetingData)
    - Raise HTTPException for errors (FastAPI integration)
    - Use async/await for all I/O operations
    """

    PLATFORM_NAME: Platform  # Must be set by subclasses

    def __init__(self, config: VideoPlatformConfig):
        """
        Initialize the platform client with configuration.

        Args:
            config: Platform configuration with API keys, webhooks, etc.
        """
        self.config = config

    @abstractmethod
    async def create_meeting(
        self,
        room_name_prefix: str,
        end_date: datetime,
        room: "Room",
    ) -> MeetingData:
        """
        Create a new meeting room on the platform.

        Args:
            room_name_prefix: Prefix for generating unique room name
            end_date: When the meeting should expire
            room: Room database model with configuration

        Returns:
            MeetingData with platform-specific meeting details

        Raises:
            HTTPException: On API errors or validation failures

        Implementation Notes:
        - Generate room name as: {prefix}-YYYYMMDDHHMMSS
        - Configure recording based on room.recording_type
        - Set privacy based on room.is_locked
        - Use room.room_size if platform supports capacity limits
        """
        pass

    @abstractmethod
    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """
        Get current session information for a room.

        Args:
            room_name: The room identifier

        Returns:
            Platform-specific session data

        Raises:
            HTTPException: If room not found or API error
        """
        pass

    @abstractmethod
    async def delete_room(self, room_name: str) -> bool:
        """
        Delete a room from the platform.

        Args:
            room_name: The room identifier

        Returns:
            True if deleted successfully or already doesn't exist

        Raises:
            HTTPException: On API errors (except 404)

        Implementation Notes:
        - Some platforms (Whereby) auto-expire rooms and don't support deletion
        - Return True for 404 (idempotent operation)
        """
        pass

    @abstractmethod
    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """
        Upload a custom logo for a room (if supported).

        Args:
            room_name: The room identifier
            logo_path: Path to logo file

        Returns:
            True if uploaded successfully

        Implementation Notes:
        - Not all platforms support per-room logos
        - Return True immediately if not supported (graceful degradation)
        """
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify webhook request authenticity using HMAC signature.

        Args:
            body: Raw request body bytes
            signature: Signature from request header
            timestamp: Optional timestamp for replay attack prevention

        Returns:
            True if signature is valid

        Implementation Notes:
        - Use constant-time comparison (hmac.compare_digest)
        - Whereby: signature format is "t={timestamp},v1={sig}"
        - Daily.co: signature is simple HMAC hex digest
        - Implement timestamp freshness check if platform supports it
        """
        pass
```

### Step 2.2: Create Platform Registry

**File: `server/reflector/video_platforms/registry.py`**

```python
"""Platform registration and discovery system."""

from typing import Dict, Type
from .base import VideoPlatformClient
from .models import Platform


# Global registry of available platform clients
_PLATFORMS: Dict[Platform, Type[VideoPlatformClient]] = {}


def register_platform(
    platform_name: Platform,
    client_class: Type[VideoPlatformClient],
) -> None:
    """
    Register a video platform client implementation.

    Args:
        platform_name: Unique platform identifier ("whereby", "daily")
        client_class: Client class implementing VideoPlatformClient

    Example:
        register_platform("whereby", WherebyClient)
    """
    if platform_name in _PLATFORMS:
        raise ValueError(f"Platform '{platform_name}' already registered")

    # Validate that the class implements the interface
    if not issubclass(client_class, VideoPlatformClient):
        raise TypeError(
            f"Client class must inherit from VideoPlatformClient, "
            f"got {client_class}"
        )

    _PLATFORMS[platform_name] = client_class


def get_platform_client_class(platform: Platform) -> Type[VideoPlatformClient]:
    """
    Retrieve a registered platform client class.

    Args:
        platform: Platform identifier

    Returns:
        Client class for the specified platform

    Raises:
        ValueError: If platform not registered
    """
    if platform not in _PLATFORMS:
        available = ", ".join(_PLATFORMS.keys())
        raise ValueError(
            f"Unknown platform '{platform}'. "
            f"Available platforms: {available}"
        )

    return _PLATFORMS[platform]


def get_available_platforms() -> list[Platform]:
    """Get list of all registered platforms."""
    return list(_PLATFORMS.keys())
```

### Step 2.3: Create Platform Factory

**File: `server/reflector/video_platforms/factory.py`**

```python
"""Factory functions for creating platform clients."""

from typing import Optional
from reflector import settings
from .base import VideoPlatformClient
from .models import Platform, VideoPlatformConfig
from .registry import get_platform_client_class


def get_platform_config(platform: Platform) -> VideoPlatformConfig:
    """
    Build platform-specific configuration from settings.

    Args:
        platform: Platform identifier

    Returns:
        VideoPlatformConfig with platform-specific values

    Raises:
        ValueError: If required settings are missing
    """
    if platform == "whereby":
        if not settings.WHEREBY_API_KEY:
            raise ValueError("WHEREBY_API_KEY is required for Whereby platform")

        return VideoPlatformConfig(
            api_key=settings.WHEREBY_API_KEY,
            webhook_secret=settings.WHEREBY_WEBHOOK_SECRET,
            subdomain=None,  # Whereby doesn't use subdomains
            s3_bucket=settings.AWS_WHEREBY_S3_BUCKET,
            s3_region=settings.AWS_S3_REGION or "us-west-2",
            aws_access_key=settings.AWS_WHEREBY_ACCESS_KEY_ID,
            aws_secret_key=settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
        )

    elif platform == "daily":
        if not settings.DAILY_API_KEY:
            raise ValueError("DAILY_API_KEY is required for Daily.co platform")

        return VideoPlatformConfig(
            api_key=settings.DAILY_API_KEY,
            webhook_secret=settings.DAILY_WEBHOOK_SECRET,
            subdomain=settings.DAILY_SUBDOMAIN,
            s3_bucket=settings.AWS_DAILY_S3_BUCKET,
            s3_region=settings.AWS_DAILY_S3_REGION or "us-west-2",
            aws_role_arn=settings.AWS_DAILY_ROLE_ARN,
        )

    else:
        raise ValueError(f"Unknown platform: {platform}")


def create_platform_client(platform: Platform) -> VideoPlatformClient:
    """
    Create and configure a platform client instance.

    Args:
        platform: Platform identifier

    Returns:
        Configured client instance

    Example:
        client = create_platform_client("whereby")
        meeting = await client.create_meeting(...)
    """
    config = get_platform_config(platform)
    client_class = get_platform_client_class(platform)
    return client_class(config)


def get_platform_for_room(room_id: Optional[str] = None) -> Platform:
    """
    Determine which platform to use for a room.

    This implements the platform selection strategy using feature flags.

    Args:
        room_id: Optional room ID for room-specific overrides

    Returns:
        Platform to use

    Platform Selection Logic:
    1. If DAILY_MIGRATION_ENABLED=False → always use "whereby"
    2. If room_id in DAILY_MIGRATION_ROOM_IDS → use "daily"
    3. Otherwise → use DEFAULT_VIDEO_PLATFORM

    Example Environment Variables:
        DAILY_MIGRATION_ENABLED=true
        DAILY_MIGRATION_ROOM_IDS=["room-abc", "room-xyz"]
        DEFAULT_VIDEO_PLATFORM=whereby
    """
    # If Daily migration is disabled, always use Whereby
    if not settings.DAILY_MIGRATION_ENABLED:
        return "whereby"

    # If specific room is in migration list, use Daily
    if room_id and room_id in settings.DAILY_MIGRATION_ROOM_IDS:
        return "daily"

    # Otherwise use the configured default
    return settings.DEFAULT_VIDEO_PLATFORM
```

### Step 2.4: Create Mock Implementation for Testing

**File: `server/reflector/video_platforms/mock.py`**

```python
"""Mock video platform client for testing."""

import hmac
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from hashlib import sha256

from .base import VideoPlatformClient
from .models import MeetingData, Platform

# Import with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from reflector.db.rooms import Room


class MockClient(VideoPlatformClient):
    """
    Mock video platform client for unit testing.

    This client simulates a video platform without making real API calls.
    Useful for testing business logic without external dependencies.
    """

    PLATFORM_NAME: Platform = "whereby"  # Pretend to be Whereby for backward compat

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._participants: Dict[str, int] = {}

    async def create_meeting(
        self,
        room_name_prefix: str,
        end_date: datetime,
        room: "Room",
    ) -> MeetingData:
        """Create a mock meeting."""
        room_name = f"{room_name_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self._rooms[room_name] = {
            "name": room_name,
            "end_date": end_date,
            "room": room,
        }
        self._participants[room_name] = 0

        return MeetingData(
            platform=self.PLATFORM_NAME,
            meeting_id=f"mock-{room_name}",
            room_url=f"https://mock.example.com/{room_name}",
            host_room_url=f"https://mock.example.com/{room_name}?host=true",
            room_name=room_name,
            end_date=end_date,
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """Get mock room session data."""
        if room_name not in self._rooms:
            raise ValueError(f"Room {room_name} not found")

        return {
            "room_name": room_name,
            "participants": self._participants.get(room_name, 0),
            "created": self._rooms[room_name].get("created", datetime.now()),
        }

    async def delete_room(self, room_name: str) -> bool:
        """Delete mock room."""
        if room_name in self._rooms:
            del self._rooms[room_name]
            del self._participants[room_name]
        return True

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """Mock logo upload (always succeeds)."""
        return True

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Mock signature verification (accepts 'valid' as signature)."""
        return signature == "valid"

    # Test helper methods
    def add_participant(self, room_name: str) -> None:
        """Add a participant to a room (test helper)."""
        if room_name in self._participants:
            self._participants[room_name] += 1

    def remove_participant(self, room_name: str) -> None:
        """Remove a participant from a room (test helper)."""
        if room_name in self._participants and self._participants[room_name] > 0:
            self._participants[room_name] -= 1

    def clear_data(self) -> None:
        """Clear all mock data (test helper)."""
        self._rooms.clear()
        self._participants.clear()
```

### Step 2.5: Implement Whereby Client Wrapper

**File: `server/reflector/video_platforms/whereby.py`**

```python
"""Whereby platform client implementation."""

import re
import hmac
import json
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from .base import VideoPlatformClient
from .models import MeetingData, Platform

# Import with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from reflector.db.rooms import Room


class WherebyClient(VideoPlatformClient):
    """
    Whereby video platform client.

    Wraps the existing Whereby API integration into the platform abstraction.

    API Documentation: https://docs.whereby.com/
    """

    PLATFORM_NAME: Platform = "whereby"
    BASE_URL = "https://api.whereby.dev/v1"
    TIMEOUT = 10
    SIGNATURE_MAX_AGE = 60  # seconds

    def __init__(self, config):
        super().__init__(config)
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    async def create_meeting(
        self,
        room_name_prefix: str,
        end_date: datetime,
        room: "Room",
    ) -> MeetingData:
        """
        Create a Whereby meeting room.

        See: https://docs.whereby.com/reference/whereby-rest-api-reference#create-meeting
        """
        room_name = f"{room_name_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Build request payload
        data = {
            "endDate": end_date.isoformat(),
            "fields": ["hostRoomUrl"],
            "roomNamePrefix": f"/{room_name}",
        }

        # Configure room mode based on lock status
        if room.is_locked:
            data["roomMode"] = "normal"
        else:
            data["roomMode"] = "group"

        # Configure recording if enabled
        if room.recording_type == "cloud" and self.config.s3_bucket:
            data["recording"] = {
                "type": "cloud",
                "destination": {
                    "provider": "s3",
                    "config": {
                        "bucket": self.config.s3_bucket,
                        "region": self.config.s3_region,
                        "accessKeyId": self.config.aws_access_key,
                        "secretAccessKey": self.config.aws_secret_key,
                    }
                }
            }

        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/meetings",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

        # Transform to standard format
        return MeetingData(
            platform=self.PLATFORM_NAME,
            meeting_id=result["meetingId"],
            room_url=result["roomUrl"],
            host_room_url=result.get("hostRoomUrl", result["roomUrl"]),
            room_name=room_name,
            end_date=end_date,
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """Get Whereby room session data."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/meetings/{room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def delete_room(self, room_name: str) -> bool:
        """
        Whereby rooms auto-expire, so deletion is a no-op.

        Returns True to maintain interface compatibility.
        """
        return True

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """
        Upload custom logo to Whereby room.

        Note: This requires reading the logo file and making a multipart request.
        Implementation depends on logo storage strategy.
        """
        # TODO: Implement logo upload if needed
        # For now, return True (feature not critical)
        return True

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify Whereby webhook signature.

        Whereby signature format: "t={timestamp},v1={signature}"
        Algorithm: HMAC-SHA256(webhook_secret, timestamp + "." + body)

        See: https://docs.whereby.com/reference/whereby-rest-api-reference#webhook-signatures
        """
        if not self.config.webhook_secret:
            raise ValueError("webhook_secret is required for signature verification")

        # Parse signature format: t={timestamp},v1={signature}
        matches = re.match(r"t=(.*),v1=(.*)", signature)
        if not matches:
            return False

        sig_timestamp, sig_hash = matches.groups()

        # Check timestamp freshness (prevent replay attacks)
        try:
            ts = int(sig_timestamp)
            now = int(datetime.now().timestamp())
            if abs(now - ts) > self.SIGNATURE_MAX_AGE:
                return False
        except (ValueError, TypeError):
            return False

        # Compute expected signature
        message = f"{sig_timestamp}.{body.decode('utf-8')}"
        expected_sig = hmac.new(
            self.config.webhook_secret.encode(),
            message.encode(),
            sha256
        ).hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(expected_sig, sig_hash)
```

### Step 2.6: Register Whereby Client

**Add to `server/reflector/video_platforms/__init__.py`:**

```python
# Auto-register built-in platforms
from .whereby import WherebyClient
from .mock import MockClient

register_platform("whereby", WherebyClient)
```

### Step 2.7: Update Settings

**File: `server/reflector/settings.py`**

Add Daily.co settings and feature flags:

```python
# Existing Whereby settings (already present)
WHEREBY_API_URL: str = "https://api.whereby.dev/v1"
WHEREBY_API_KEY: str | None = None
WHEREBY_WEBHOOK_SECRET: str | None = None
AWS_WHEREBY_S3_BUCKET: str | None = None
AWS_WHEREBY_ACCESS_KEY_ID: str | None = None
AWS_WHEREBY_ACCESS_KEY_SECRET: str | None = None

# NEW: Daily.co API Integration
DAILY_API_KEY: str | None = None
DAILY_WEBHOOK_SECRET: str | None = None
DAILY_SUBDOMAIN: str | None = None
AWS_DAILY_S3_BUCKET: str | None = None
AWS_DAILY_S3_REGION: str = "us-west-2"
AWS_DAILY_ROLE_ARN: str | None = None

# NEW: Platform Migration Feature Flags
DAILY_MIGRATION_ENABLED: bool = False  # Conservative default
DAILY_MIGRATION_ROOM_IDS: list[str] = []  # Specific rooms for gradual rollout
DEFAULT_VIDEO_PLATFORM: Literal["whereby", "daily"] = "whereby"  # Default to Whereby
```

### Step 2.8: Update Database Schema

**Create migration: `server/migrations/versions/<alembic-id>_add_platform_support.py`**

Note: Alembic generates revision IDs automatically (e.g., `1e49625677e4_add_platform_support.py`)

```bash
cd server
uv run alembic revision -m "add_platform_support"
```

**Migration content:**

```python
"""add_platform_support

Adds platform field to room and meeting tables to support multi-provider architecture.

Revision ID: <auto-generated>
Revises: <latest-revision>
Create Date: <auto-generated>
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '<auto-generated>'
down_revision = '<latest-revision>'
branch_labels = None
depends_on = None


def upgrade():
    """Add platform field with default 'whereby' for backward compatibility."""

    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "platform",
                sa.String(),
                nullable=False,
                server_default="whereby",
            )
        )

    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "platform",
                sa.String(),
                nullable=False,
                server_default="whereby",
            )
        )


def downgrade():
    """Remove platform field."""

    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.drop_column("platform")

    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.drop_column("platform")
```

**Update models:**

**File: `server/reflector/db/rooms.py`**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reflector.video_platforms.models import Platform

class Room:
    # ... existing fields ...

    # NEW: Platform field
    platform: "Platform" = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=False,
        server_default="whereby",
    )
```

**File: `server/reflector/db/meetings.py`**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reflector.video_platforms.models import Platform

class Meeting:
    # ... existing fields ...

    # NEW: Platform field
    platform: "Platform" = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=False,
        server_default="whereby",
    )
```

### Step 2.9: Refactor Room/Meeting Creation

**File: `server/reflector/views/rooms.py`**

Replace direct Whereby API calls with platform abstraction:

```python
from reflector.video_platforms import (
    create_platform_client,
    get_platform_for_room,
)

# OLD CODE (remove):
# from reflector import whereby
# meeting_data = whereby.create_meeting(...)

# NEW CODE:
@router.post("/rooms", response_model=RoomResponse)
async def create_room(room_data: RoomCreate):
    """Create a new room."""

    # Determine platform for new room
    platform = get_platform_for_room()

    # Create room in database
    room = Room(
        name=room_data.name,
        is_locked=room_data.is_locked,
        recording_type=room_data.recording_type,
        platform=platform,  # NEW: Store platform
        # ... other fields ...
    )
    await room.save()

    return RoomResponse.from_orm(room)


@router.post("/rooms/{room_name}/meeting", response_model=MeetingResponse)
async def create_meeting(room_name: str, meeting_data: MeetingCreate):
    """Create a new meeting in a room."""

    # Get room
    room = await Room.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Use platform abstraction instead of direct Whereby calls
    platform = get_platform_for_room(room.id)  # Respects feature flags
    client = create_platform_client(platform)

    # Create meeting via platform client
    meeting_data = await client.create_meeting(
        room_name_prefix=room.name,
        end_date=meeting_data.end_date,
        room=room,
    )

    # Create database record
    meeting = Meeting(
        room_id=room.id,
        platform=meeting_data.platform,  # NEW: Store platform
        meeting_id=meeting_data.meeting_id,
        room_url=meeting_data.room_url,
        host_room_url=meeting_data.host_room_url,
        # ... other fields ...
    )
    await meeting.save()

    # Upload logo if configured (platform handles graceful degradation)
    if room.logo_path:
        await client.upload_logo(meeting_data.room_name, room.logo_path)

    return MeetingResponse.from_orm(meeting)
```

### Deliverables
- [ ] Platform abstraction layer (`base.py`, `registry.py`, `factory.py`, `models.py`)
- [ ] Whereby client wrapper (`whereby.py`)
- [ ] Mock client for testing (`mock.py`)
- [ ] Database migration for platform field
- [ ] Updated room/meeting models
- [ ] Refactored room creation logic
- [ ] Updated settings with feature flags

---

## Phase 3: Daily.co Implementation (4-5 hours)

### Objective
Implement Daily.co provider with feature parity to Whereby.

### Step 3.1: Implement Daily.co Client

**File: `server/reflector/video_platforms/daily.py`**

```python
"""Daily.co platform client implementation."""

import hmac
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from .base import VideoPlatformClient
from .models import MeetingData, Platform

# Import with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from reflector.db.rooms import Room


class DailyClient(VideoPlatformClient):
    """
    Daily.co video platform client.

    API Documentation: https://docs.daily.co/reference/rest-api
    """

    PLATFORM_NAME: Platform = "daily"
    BASE_URL = "https://api.daily.co/v1"
    TIMEOUT = 10

    def __init__(self, config):
        super().__init__(config)
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    async def create_meeting(
        self,
        room_name_prefix: str,
        end_date: datetime,
        room: "Room",
    ) -> MeetingData:
        """
        Create a Daily.co room.

        See: https://docs.daily.co/reference/rest-api/rooms/create-room
        """
        room_name = f"{room_name_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Build request payload
        data = {
            "name": room_name,
            "privacy": "private" if room.is_locked else "public",
            "properties": {
                "exp": int(end_date.timestamp()),
                "enable_chat": True,
                "enable_screenshare": True,
                "start_video_off": False,
                "start_audio_off": False,
            }
        }

        # Configure recording if enabled
        # NOTE: Daily.co always uses "raw-tracks" for better transcription quality
        # (multiple WebM files instead of single MP4)
        if room.recording_type != "none":
            data["properties"]["enable_recording"] = "raw-tracks"
        else:
            data["properties"]["enable_recording"] = False

        # Configure S3 bucket for recordings
        # NOTE: Not checking room.recording_type - figure out later if conditional needed
        assert self.config.s3_bucket, "S3 bucket must be configured"
        data["properties"]["recordings_bucket"] = {
            "bucket_name": self.config.s3_bucket,
            "bucket_region": self.config.s3_region,
            "assume_role_arn": self.config.aws_role_arn,
            "allow_api_access": True,
        }

        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/rooms",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

        # Build room URL
        room_url = result["url"]

        # Daily.co doesn't have separate host URLs
        host_room_url = room_url

        # Transform to standard format
        return MeetingData(
            platform=self.PLATFORM_NAME,
            meeting_id=result["id"],  # Daily.co room ID
            room_url=room_url,
            host_room_url=host_room_url,
            room_name=result["name"],
            end_date=end_date,
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """
        Get Daily.co room information.

        See: https://docs.daily.co/reference/rest-api/rooms/get-room-info
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/rooms/{room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def get_room_presence(self, room_name: str) -> Dict[str, Any]:
        """
        Get real-time participant presence (Daily.co-specific feature).

        See: https://docs.daily.co/reference/rest-api/rooms/get-room-presence

        Note: This method is NOT in the base interface since it's platform-specific.
        Only call this if you know you're using Daily.co.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/rooms/{room_name}/presence",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def delete_room(self, room_name: str) -> bool:
        """
        Delete a Daily.co room.

        See: https://docs.daily.co/reference/rest-api/rooms/delete-room
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/rooms/{room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )

            # Accept both 200 (deleted) and 404 (already gone) as success
            if response.status_code in (200, 404):
                return True

            response.raise_for_status()
            return False

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """
        Daily.co doesn't support per-room logos.

        Return True for interface compatibility (graceful degradation).
        """
        return True

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify Daily.co webhook signature.

        Daily.co signature format: Simple HMAC-SHA256 hex digest
        Header: X-Daily-Signature
        Algorithm: HMAC-SHA256(webhook_secret, body)

        See: https://docs.daily.co/reference/rest-api/webhooks#webhook-signatures
        """
        if not self.config.webhook_secret:
            raise ValueError("webhook_secret is required for signature verification")

        # Compute expected signature
        expected_sig = hmac.new(
            self.config.webhook_secret.encode(),
            body,
            sha256
        ).hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(expected_sig, signature)

    async def create_meeting_token(self, room_name: str, enable_recording: bool) -> str:
        """Create JWT meeting token with optional auto-recording.

        Daily.co supports token-based meeting configuration, which allows
        per-participant settings like auto-starting cloud recording.

        This is used instead of room-level recording config for more control.
        """
        data = {"properties": {"room_name": room_name}}

        if enable_recording:
            data["properties"]["start_cloud_recording"] = True

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/meeting-tokens",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()["token"]
```

**Token-Based Auto-Recording (Critical Addition)**

After creating a Daily.co meeting, append JWT token to URLs for auto-recording:

```python
# In rooms.py after create_meeting
if meeting.platform == "daily" and room.recording_trigger != "none":
    client = create_platform_client(meeting.platform)
    token = await client.create_meeting_token(
        meeting.room_name, enable_recording=True
    )
    meeting.room_url += f"?t={token}"
    meeting.host_room_url += f"?t={token}"
```

**Why tokens instead of room config:**
- Room-level `enable_recording` only enables the capability
- Token with `start_cloud_recording: true` actually starts it
- Provides per-participant control (future: host-only recording)

### Step 3.2: Register Daily.co Client

**Update `server/reflector/video_platforms/__init__.py`:**

```python
# Auto-register built-in platforms
from .whereby import WherebyClient
from .daily import DailyClient
from .mock import MockClient

register_platform("whereby", WherebyClient)
register_platform("daily", DailyClient)
```

### Step 3.3: Create Daily.co Webhook Handler

**File: `server/reflector/views/daily.py`**

```python
"""Daily.co webhook endpoint."""

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

from reflector import settings
from reflector.logger import logger
from reflector.db.meetings import Meeting
from reflector.video_platforms import create_platform_client


router = APIRouter()


# Webhook event models
class DailyWebhookEvent(BaseModel):
    """Base Daily.co webhook event."""
    type: str
    payload: dict
    id: str
    timestamp: datetime


class ParticipantPayload(BaseModel):
    """Participant event payload."""
    room: str
    participant_id: str
    user_name: Optional[str] = None


class RecordingPayload(BaseModel):
    """Recording event payload."""
    room: str
    recording_id: str
    download_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/webhook")
async def daily_webhook(
    request: Request,
    x_daily_signature: str = Header(None),
):
    """
    Handle Daily.co webhook events.

    Supported events:
    - participant.joined - Update participant count
    - participant.left - Update participant count
    - recording.started - Log recording start
    - recording.ready-to-download - Trigger processing
    - recording.error - Log recording errors

    See: https://docs.daily.co/reference/rest-api/webhooks
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not x_daily_signature:
        raise HTTPException(status_code=400, detail="Missing X-Daily-Signature header")

    client = create_platform_client("daily")
    if not client.verify_webhook_signature(body, x_daily_signature):
        logger.warning("Daily.co webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event
    try:
        event = DailyWebhookEvent.parse_raw(body)
    except Exception as e:
        logger.error(f"Failed to parse Daily.co webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid event format")

    logger.info(f"Daily.co webhook event: {event.type} (room: {event.payload.get('room')})")

    # Handle event by type
    if event.type == "participant.joined":
        await handle_participant_joined(event)

    elif event.type == "participant.left":
        await handle_participant_left(event)

    elif event.type == "recording.started":
        await handle_recording_started(event)

    elif event.type == "recording.ready-to-download":
        await handle_recording_ready(event)

    elif event.type == "recording.error":
        await handle_recording_error(event)

    else:
        logger.warning(f"Unhandled Daily.co event type: {event.type}")

    return {"status": "ok"}


async def handle_participant_joined(event: DailyWebhookEvent):
    """Handle participant joining a room."""
    room_name = event.payload.get("room")
    if not room_name:
        return

    # Find active meeting for this room
    meeting = await Meeting.get_active_by_room_name(room_name)
    if not meeting:
        logger.warning(f"No active meeting found for room: {room_name}")
        return

    # Increment participant count
    meeting.num_clients = (meeting.num_clients or 0) + 1
    await meeting.save()

    logger.info(f"Participant joined {room_name}, count: {meeting.num_clients}")


async def handle_participant_left(event: DailyWebhookEvent):
    """Handle participant leaving a room."""
    room_name = event.payload.get("room")
    if not room_name:
        return

    # Find active meeting for this room
    meeting = await Meeting.get_active_by_room_name(room_name)
    if not meeting:
        return

    # Decrement participant count (don't go below 0)
    meeting.num_clients = max(0, (meeting.num_clients or 1) - 1)
    await meeting.save()

    logger.info(f"Participant left {room_name}, count: {meeting.num_clients}")


async def handle_recording_started(event: DailyWebhookEvent):
    """Handle recording start."""
    room_name = event.payload.get("room")
    recording_id = event.payload.get("recording_id")

    logger.info(f"Recording started for room {room_name}: {recording_id}")


async def handle_recording_ready(event: DailyWebhookEvent):
    """Handle recording ready for download."""
    room_name = event.payload.get("room")
    recording_id = event.payload.get("recording_id")
    download_url = event.payload.get("download_url")

    if not download_url:
        logger.error(f"Recording ready but no download URL: {recording_id}")
        return

    # Find meeting for this room
    meeting = await Meeting.get_by_room_name(room_name)
    if not meeting:
        logger.error(f"No meeting found for room: {room_name}")
        return

    logger.info(f"Recording ready: {recording_id}, triggering processing")

    # Trigger background processing
    from reflector.worker.process import process_recording_from_url
    process_recording_from_url.delay(
        recording_url=download_url,
        meeting_id=str(meeting.id),
        recording_id=recording_id,
    )


async def handle_recording_error(event: DailyWebhookEvent):
    """Handle recording errors."""
    room_name = event.payload.get("room")
    recording_id = event.payload.get("recording_id")
    error = event.payload.get("error")

    logger.error(
        f"Recording error for room {room_name}: {error}",
        extra={"recording_id": recording_id}
    )
```

**Register router in `server/reflector/app.py`:**

```python
from reflector.views import daily

app.include_router(daily.router, prefix="/v1/daily", tags=["daily"])
```

### Step 3.4: Create Recording Processing Task

**⚠️ NEXT STEP - NOT YET IMPLEMENTED**

The `process_recording_from_url` task described below is the next implementation step.
It handles downloading Daily.co recordings from webhook URLs into the existing transcription pipeline.

**Update `server/reflector/worker/process.py`:**

```python
from celery import shared_task
import httpx
from pathlib import Path
import tempfile

from reflector.db.recordings import Recording
from reflector.db.meetings import Meeting
from reflector.logger import logger


@shared_task
@asynctask
async def process_recording_from_url(
    recording_url: str,
    meeting_id: str,
    recording_id: str,
):
    """
    Download and process a recording from a URL (Daily.co).

    This task is triggered by Daily.co webhooks when a recording is ready.

    Args:
        recording_url: HTTPS URL to download recording from
        meeting_id: Database ID of the meeting
        recording_id: Platform-specific recording identifier
    """
    logger.info(f"Processing recording from URL: {recording_id}")

    # Get meeting
    meeting = await Meeting.get(meeting_id)
    if not meeting:
        logger.error(f"Meeting not found: {meeting_id}")
        return

    # Download recording to temporary file
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                recording_url,
                timeout=300,  # 5 minutes for large files
            )
            response.raise_for_status()

            # Save to temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".mp4",
                delete=False,
            ) as tmp_file:
                tmp_file.write(response.content)
                local_path = tmp_file.name

        logger.info(f"Downloaded recording to: {local_path}")

    except Exception as e:
        logger.error(f"Failed to download recording: {e}")
        return

    try:
        # Validate audio stream exists
        import ffmpeg
        probe = ffmpeg.probe(local_path)
        audio_streams = [
            s for s in probe["streams"]
            if s["codec_type"] == "audio"
        ]

        if not audio_streams:
            logger.error(f"No audio stream in recording: {recording_id}")
            return

        # Create recording record
        recording = Recording(
            meeting_id=meeting_id,
            bucket="daily-recordings",  # Logical bucket name
            object_key=recording_id,  # Store Daily.co recording ID
            local_path=local_path,
            status="downloaded",
        )
        await recording.save()

        logger.info(f"Created recording record: {recording.id}")

        # Trigger main processing pipeline
        from reflector.worker.pipeline import task_pipeline_process
        task_pipeline_process.delay(transcript_id=str(recording.transcript_id))

    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        # Clean up temporary file on error
        Path(local_path).unlink(missing_ok=True)
        raise
```

### Step 3.5: Create Frontend Components

**File: `www/app/[roomName]/components/RoomContainer.tsx`**

```typescript
'use client'

import { useEffect, useState } from 'react'
import WherebyRoom from './WherebyRoom'
import DailyRoom from './DailyRoom'
import { Meeting } from '@/app/api/types.gen'

interface RoomContainerProps {
  meeting: Meeting
}

export default function RoomContainer({ meeting }: RoomContainerProps) {
  // Determine platform from meeting response
  const platform = meeting.platform || 'whereby' // Default for backward compat

  // Route to appropriate platform component
  if (platform === 'daily') {
    return <DailyRoom meeting={meeting} />
  }

  // Default to Whereby
  return <WherebyRoom meeting={meeting} />
}
```

**File: `www/app/[roomName]/components/DailyRoom.tsx`**

```typescript
'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import DailyIframe, { DailyCall } from '@daily-co/daily-js'
import { Meeting } from '@/app/api/types.gen'
import { Box, Button, Text, useToast } from '@chakra-ui/react'
import { useSessionStatus } from '@/hooks/useSessionStatus'
import { api } from '@/app/api/client'

interface DailyRoomProps {
  meeting: Meeting
}

export default function DailyRoom({ meeting }: DailyRoomProps) {
  const router = useRouter()
  const toast = useToast()
  const containerRef = useRef<HTMLDivElement>(null)
  const callFrameRef = useRef<DailyCall | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showConsent, setShowConsent] = useState(false)

  const { sessionId } = useSessionStatus(meeting.id)

  useEffect(() => {
    if (!containerRef.current) return

    // Check if recording requires consent
    if (meeting.recording_type === 'cloud' && !sessionId) {
      setShowConsent(true)
      setIsLoading(false)
      return
    }

    // Create Daily.co iframe
    const frame = DailyIframe.createFrame(containerRef.current, {
      showLeaveButton: true,
      showFullscreenButton: true,
      iframeStyle: {
        position: 'absolute',
        width: '100%',
        height: '100%',
        border: 'none',
      },
    })

    callFrameRef.current = frame

    // Join meeting
    frame.join({ url: meeting.room_url })
      .then(() => {
        setIsLoading(false)
      })
      .catch((error) => {
        console.error('Failed to join Daily.co meeting:', error)
        toast({
          title: 'Failed to join meeting',
          description: error.message,
          status: 'error',
          duration: 5000,
        })
        setIsLoading(false)
      })

    // Handle leave event
    frame.on('left-meeting', () => {
      router.push('/browse')
    })

    // Cleanup
    return () => {
      if (callFrameRef.current) {
        callFrameRef.current.destroy()
        callFrameRef.current = null
      }
    }
  }, [meeting, sessionId, router, toast])

  const handleConsent = async () => {
    try {
      await api.v1MeetingAudioConsent({
        path: { meeting_id: meeting.id },
        body: { consent: true },
      })
      setShowConsent(false)
      // Trigger re-render to join meeting
      window.location.reload()
    } catch (error) {
      toast({
        title: 'Failed to record consent',
        description: 'Please try again',
        status: 'error',
        duration: 3000,
      })
    }
  }

  if (showConsent) {
    return (
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        textAlign="center"
        maxW="500px"
        p={8}
        bg="white"
        borderRadius="md"
        boxShadow="lg"
      >
        <Text fontSize="xl" fontWeight="bold" mb={4}>
          Recording Consent Required
        </Text>
        <Text mb={6}>
          This meeting will be recorded and transcribed. Do you consent to
          participate?
        </Text>
        <Button colorScheme="blue" onClick={handleConsent} mr={4}>
          I Consent
        </Button>
        <Button onClick={() => router.push('/browse')}>
          Decline
        </Button>
      </Box>
    )
  }

  if (isLoading) {
    return (
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
      >
        <Text>Loading meeting...</Text>
      </Box>
    )
  }

  return (
    <Box
      ref={containerRef}
      position="absolute"
      top={0}
      left={0}
      right={0}
      bottom={0}
    />
  )
}
```

**File: `www/app/[roomName]/components/WherebyRoom.tsx`**

Extract existing room page logic into this component (no changes to functionality).

**Update `www/app/[roomName]/page.tsx`:**

```typescript
import RoomContainer from './components/RoomContainer'
import { api } from '@/app/api/client'

export default async function RoomPage({ params }: { params: { roomName: string } }) {
  const meeting = await api.v1GetActiveMeeting({
    path: { room_name: params.roomName }
  })

  return <RoomContainer meeting={meeting} />
}
```

### Step 3.6: Update Frontend Dependencies

**Update `www/package.json`:**

```bash
cd www
yarn add @daily-co/daily-js@^0.81.0
```

### Step 3.7: Update Environment Configuration

**Update `server/env.example`:**

```bash
# Video Platform Configuration
# Whereby (existing provider)
WHEREBY_API_KEY=your-whereby-api-key
WHEREBY_WEBHOOK_SECRET=your-whereby-webhook-secret
AWS_WHEREBY_S3_BUCKET=your-whereby-bucket
AWS_WHEREBY_ACCESS_KEY_ID=your-aws-key
AWS_WHEREBY_ACCESS_KEY_SECRET=your-aws-secret

# Daily.co (new provider)
DAILY_API_KEY=your-daily-api-key
DAILY_WEBHOOK_SECRET=your-daily-webhook-secret
DAILY_SUBDOMAIN=your-subdomain
AWS_DAILY_S3_BUCKET=your-daily-bucket
AWS_DAILY_S3_REGION=us-west-2
AWS_DAILY_ROLE_ARN=arn:aws:iam::ACCOUNT:role/DailyRecording

# Platform Selection
DAILY_MIGRATION_ENABLED=false           # Enable Daily.co support
DAILY_MIGRATION_ROOM_IDS=[]            # Specific rooms to use Daily
DEFAULT_VIDEO_PLATFORM=whereby          # Default platform for new rooms
```

### Deliverables
- [ ] Daily.co client implementation
- [ ] Daily.co webhook handler
- [ ] Recording download task
- [ ] Frontend platform routing
- [ ] DailyRoom component
- [ ] WherebyRoom component extraction
- [ ] Updated environment configuration
- [ ] Frontend dependencies installed

---

## Testing Strategy (3-4 hours)

### Unit Tests

**File: `server/tests/test_video_platforms.py`**

```python
"""Unit tests for video platform abstraction."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from reflector.video_platforms import (
    create_platform_client,
    get_platform_config,
    register_platform,
    get_available_platforms,
)
from reflector.video_platforms.whereby import WherebyClient
from reflector.video_platforms.daily import DailyClient
from reflector.video_platforms.mock import MockClient


@pytest.fixture
def mock_room():
    """Create a mock room object."""
    room = Mock()
    room.id = "room-123"
    room.name = "test-room"
    room.is_locked = False
    room.recording_type = "cloud"
    room.room_size = 10
    return room


def test_platform_registry():
    """Test platform registration and discovery."""
    platforms = get_available_platforms()
    assert "whereby" in platforms
    assert "daily" in platforms


def test_create_whereby_client():
    """Test Whereby client creation."""
    with patch("reflector.settings") as mock_settings:
        mock_settings.WHEREBY_API_KEY = "test-key"
        mock_settings.WHEREBY_WEBHOOK_SECRET = "test-secret"

        client = create_platform_client("whereby")
        assert isinstance(client, WherebyClient)
        assert client.PLATFORM_NAME == "whereby"


def test_create_daily_client():
    """Test Daily.co client creation."""
    with patch("reflector.settings") as mock_settings:
        mock_settings.DAILY_API_KEY = "test-key"
        mock_settings.DAILY_WEBHOOK_SECRET = "test-secret"

        client = create_platform_client("daily")
        assert isinstance(client, DailyClient)
        assert client.PLATFORM_NAME == "daily"


@pytest.mark.asyncio
async def test_whereby_signature_verification():
    """Test Whereby webhook signature verification."""
    config = VideoPlatformConfig(
        api_key="test",
        webhook_secret="test-secret",
    )
    client = WherebyClient(config)

    # Generate valid signature
    timestamp = str(int(datetime.now().timestamp()))
    body = b'{"event": "test"}'
    message = f"{timestamp}.{body.decode()}"

    import hmac
    from hashlib import sha256
    signature = hmac.new(
        b"test-secret",
        message.encode(),
        sha256
    ).hexdigest()

    sig_header = f"t={timestamp},v1={signature}"

    assert client.verify_webhook_signature(body, sig_header)


@pytest.mark.asyncio
async def test_daily_signature_verification():
    """Test Daily.co webhook signature verification."""
    config = VideoPlatformConfig(
        api_key="test",
        webhook_secret="test-secret",
    )
    client = DailyClient(config)

    # Generate valid signature
    body = b'{"event": "test"}'

    import hmac
    from hashlib import sha256
    signature = hmac.new(
        b"test-secret",
        body,
        sha256
    ).hexdigest()

    assert client.verify_webhook_signature(body, signature)


@pytest.mark.asyncio
async def test_mock_client_lifecycle(mock_room):
    """Test mock client create/delete lifecycle."""
    config = VideoPlatformConfig(api_key="test")
    client = MockClient(config)

    # Create meeting
    end_date = datetime.now() + timedelta(hours=1)
    meeting = await client.create_meeting("test", end_date, mock_room)

    assert meeting.platform == "whereby"  # Mock pretends to be Whereby
    assert "test-" in meeting.room_name

    # Get sessions
    sessions = await client.get_room_sessions(meeting.room_name)
    assert sessions["room_name"] == meeting.room_name
    assert sessions["participants"] == 0

    # Add participant
    client.add_participant(meeting.room_name)
    sessions = await client.get_room_sessions(meeting.room_name)
    assert sessions["participants"] == 1

    # Delete room
    result = await client.delete_room(meeting.room_name)
    assert result is True

    # Room should be gone
    with pytest.raises(ValueError):
        await client.get_room_sessions(meeting.room_name)
```

**File: `server/tests/test_daily_webhook.py`**

```python
"""Integration tests for Daily.co webhook handler."""

import pytest
import hmac
from hashlib import sha256
from datetime import datetime
from fastapi.testclient import TestClient

from reflector.app import app
from reflector.db.meetings import Meeting


client = TestClient(app)


def create_webhook_signature(body: bytes, secret: str) -> str:
    """Create Daily.co webhook signature."""
    return hmac.new(secret.encode(), body, sha256).hexdigest()


@pytest.mark.asyncio
async def test_participant_joined(mock_meeting):
    """Test participant joined event."""
    webhook_secret = "test-secret"

    event_data = {
        "type": "participant.joined",
        "id": "evt_123",
        "timestamp": datetime.now().isoformat(),
        "payload": {
            "room": mock_meeting.room_name,
            "participant_id": "user_123",
        }
    }

    body = json.dumps(event_data).encode()
    signature = create_webhook_signature(body, webhook_secret)

    with patch("reflector.settings.DAILY_WEBHOOK_SECRET", webhook_secret):
        response = client.post(
            "/v1/daily/webhook",
            content=body,
            headers={"X-Daily-Signature": signature}
        )

    assert response.status_code == 200

    # Verify participant count increased
    meeting = await Meeting.get(mock_meeting.id)
    assert meeting.num_clients == 1


@pytest.mark.asyncio
async def test_recording_ready(mock_meeting):
    """Test recording ready event triggers processing."""
    webhook_secret = "test-secret"

    event_data = {
        "type": "recording.ready-to-download",
        "id": "evt_456",
        "timestamp": datetime.now().isoformat(),
        "payload": {
            "room": mock_meeting.room_name,
            "recording_id": "rec_789",
            "download_url": "https://daily.co/recordings/rec_789.mp4",
        }
    }

    body = json.dumps(event_data).encode()
    signature = create_webhook_signature(body, webhook_secret)

    with patch("reflector.settings.DAILY_WEBHOOK_SECRET", webhook_secret):
        with patch("reflector.worker.process.process_recording_from_url.delay") as mock_task:
            response = client.post(
                "/v1/daily/webhook",
                content=body,
                headers={"X-Daily-Signature": signature}
            )

    assert response.status_code == 200
    mock_task.assert_called_once()


def test_invalid_signature():
    """Test webhook rejects invalid signature."""
    event_data = {"type": "participant.joined"}
    body = json.dumps(event_data).encode()

    response = client.post(
        "/v1/daily/webhook",
        content=body,
        headers={"X-Daily-Signature": "invalid"}
    )

    assert response.status_code == 401
```

### Integration Tests

**Test Checklist:**
- [ ] Platform factory creates correct client types
- [ ] Whereby client wrapper calls work
- [ ] Daily.co client API calls work (mocked)
- [ ] Webhook signature verification (both platforms)
- [ ] Recording download task executes
- [ ] Frontend components render correctly
- [ ] Platform routing works in RoomContainer

### Manual Testing Procedure

**Prerequisites:**
1. Daily.co account with API credentials
2. Webhook endpoint configured in Daily.co dashboard
3. Database migration applied

**Test Scenario 1: Whereby Still Works**
```bash
# Set environment
export DEFAULT_VIDEO_PLATFORM=whereby
export DAILY_MIGRATION_ENABLED=false

# Create room and meeting
# Verify Whereby embed loads
# Verify recording works
# Verify transcription pipeline runs
```

**Test Scenario 2: Daily.co New Installation**
```bash
# Set environment
export DEFAULT_VIDEO_PLATFORM=daily
export DAILY_MIGRATION_ENABLED=true
export DAILY_API_KEY=your-key
export DAILY_WEBHOOK_SECRET=your-secret

# Create room and meeting
# Verify Daily.co iframe loads
# Verify participant events update count
# Start recording
# Verify webhook fires
# Verify recording downloads
# Verify transcription pipeline runs
```

**Test Scenario 3: Gradual Migration**
```bash
# Set environment
export DAILY_MIGRATION_ENABLED=true
export DAILY_MIGRATION_ROOM_IDS=["specific-room-id"]
export DEFAULT_VIDEO_PLATFORM=whereby

# Create two rooms
# Verify one uses Daily, one uses Whereby
# Verify both work independently
```

---

## Rollout Plan

### Phase 1: Development Testing (Week 1)
- [ ] Deploy to development environment
- [ ] Run full test suite
- [ ] Manual testing of both providers
- [ ] Performance benchmarking

### Phase 2: Staging Validation (Week 2)
- [ ] Deploy to staging with `DAILY_MIGRATION_ENABLED=false`
- [ ] Verify no regressions in Whereby functionality
- [ ] Enable Daily.co for internal test rooms
- [ ] Validate recording pipeline end-to-end

### Phase 3: Production Gradual Rollout (Weeks 3-6)
- [ ] Deploy to production with `DEFAULT_VIDEO_PLATFORM=whereby`
- [ ] Enable Daily.co for 1-2 beta customers
- [ ] Monitor error rates, recording success, transcription quality
- [ ] Gradually expand to more customers
- [ ] Collect feedback and iterate

### Phase 4: Full Migration (Week 7+)
- [ ] Set `DEFAULT_VIDEO_PLATFORM=daily` for new installations
- [ ] Maintain Whereby support for existing customers
- [ ] Document platform selection in admin guide

---

## Risk Analysis

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Database migration fails on production | HIGH | LOW | Test migration on production copy first |
| Recording format incompatibility | HIGH | LOW | Both use MP4, validate with test recordings |
| Webhook signature fails | MEDIUM | LOW | Comprehensive tests, staging validation |
| Performance degradation from abstraction | MEDIUM | LOW | Benchmark before/after, <2% overhead target |
| Frontend component bugs | MEDIUM | MEDIUM | Extract Whereby logic first, test independently |
| Circular import issues | LOW | MEDIUM | Use TYPE_CHECKING pattern consistently |

### Business Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Customer complaints about new UI | MEDIUM | LOW | UI should be identical, consent flow same |
| Recording processing failures | HIGH | LOW | Same pipeline, tested with mock recordings |
| Whereby customers affected | HIGH | LOW | Feature flag off by default, no changes to Whereby flow |
| Cost overruns from dual providers | LOW | LOW | Provider selection controlled, not running both |

---

## Success Metrics

### Implementation Metrics
- [ ] Test coverage >90% for platform abstraction
- [ ] Zero failing tests in CI
- [ ] Database migration applies cleanly on staging
- [ ] All linting passes
- [ ] Documentation complete

### Functional Metrics
- [ ] Whereby installations unaffected (0% regression)
- [ ] Daily.co meetings create successfully (>99%)
- [ ] Recording download success rate >98%
- [ ] Transcription quality equivalent between providers
- [ ] Webhook delivery rate >99.5%

### Performance Metrics
- [ ] Meeting creation latency <500ms (both providers)
- [ ] Abstraction overhead <2%
- [ ] Frontend bundle size increase <50KB
- [ ] No memory leaks in long-running meetings

---

## Documentation Requirements

### Code Documentation
- [ ] Docstrings on all public methods
- [ ] Architecture decision records (ADR) for abstraction pattern
- [ ] Inline comments for complex logic

### User Documentation
- [ ] Update README with provider configuration
- [ ] Admin guide for platform selection
- [ ] Troubleshooting guide for common issues

### Developer Documentation
- [ ] Architecture diagram updated
- [ ] Contributing guide updated with platform addition process
- [ ] API documentation regenerated

---

## Appendix A: File Checklist

### Backend Files (New)
- [ ] `server/reflector/platform_types.py` (Platform literal type - separate to avoid circular imports)
- [ ] `server/reflector/video_platforms/__init__.py`
- [ ] `server/reflector/video_platforms/base.py`
- [ ] `server/reflector/video_platforms/models.py`
- [ ] `server/reflector/video_platforms/registry.py`
- [ ] `server/reflector/video_platforms/factory.py`
- [ ] `server/reflector/video_platforms/whereby.py`
- [ ] `server/reflector/video_platforms/daily.py`
- [ ] `server/reflector/video_platforms/mock.py`
- [ ] `server/reflector/views/daily.py`
- [ ] `server/migrations/versions/<alembic-id>_add_platform_support.py` (e.g., `1e49625677e4_...`)

### Backend Files (Modified)
- [ ] `server/reflector/settings.py`
- [ ] `server/reflector/views/rooms.py`
- [ ] `server/reflector/db/rooms.py`
- [ ] `server/reflector/db/meetings.py`
- [ ] `server/reflector/worker/process.py`
- [ ] `server/reflector/app.py`
- [ ] `server/env.example`

### Frontend Files (New)
- [ ] `www/app/[roomName]/components/RoomContainer.tsx`
- [ ] `www/app/[roomName]/components/DailyRoom.tsx`
- [ ] `www/app/[roomName]/components/WherebyRoom.tsx`

### Frontend Files (Modified)
- [ ] `www/app/[roomName]/page.tsx`
- [ ] `www/package.json`

### Test Files (New)
- [ ] `server/tests/test_video_platforms.py`
- [ ] `server/tests/test_daily_webhook.py`
- [ ] `server/tests/utils/video_platform_test_utils.py`

---

## Appendix B: Environment Variables Reference

```bash
# Whereby Configuration (Existing)
WHEREBY_API_KEY=                    # API key from Whereby dashboard
WHEREBY_WEBHOOK_SECRET=             # Webhook secret for signature verification
AWS_WHEREBY_S3_BUCKET=              # S3 bucket for Whereby recordings
AWS_WHEREBY_ACCESS_KEY_ID=          # AWS access key for S3
AWS_WHEREBY_ACCESS_KEY_SECRET=      # AWS secret key for S3

# Daily.co Configuration (New)
DAILY_API_KEY=                      # API key from Daily.co dashboard
DAILY_WEBHOOK_SECRET=               # Webhook secret for signature verification
DAILY_SUBDOMAIN=                    # Your Daily.co subdomain (optional)
AWS_DAILY_S3_BUCKET=                # S3 bucket for Daily.co recordings
AWS_DAILY_S3_REGION=us-west-2       # AWS region (default: us-west-2)
AWS_DAILY_ROLE_ARN=                 # IAM role ARN for S3 access

# Platform Selection (New)
DAILY_MIGRATION_ENABLED=false       # Master switch for Daily.co support
DAILY_MIGRATION_ROOM_IDS=[]        # JSON array of specific room IDs for Daily
DEFAULT_VIDEO_PLATFORM=whereby      # Default platform ("whereby" or "daily")
```

---

## Appendix C: Webhook Configuration

### Daily.co Webhook Setup

```bash
# Configure webhook endpoint via API
curl -X POST https://api.daily.co/v1/webhook-endpoints \
  -H "Authorization: Bearer ${DAILY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/v1/daily/webhook",
    "events": [
      "participant.joined",
      "participant.left",
      "recording.started",
      "recording.ready-to-download",
      "recording.error"
    ]
  }'
```

### Whereby Webhook Setup

Configured via Whereby dashboard under Account Settings → Webhooks.

---

## Summary

This technical specification provides a complete, step-by-step guide for implementing multi-provider video platform support in Reflector. The implementation follows clean architecture principles, maintains backward compatibility, and enables zero-downtime migration between providers.

**Key Implementation Principles:**
1. Abstraction before extension (Phase 2 before Phase 3)
2. Feature flags for gradual rollout
3. Comprehensive testing at each phase
4. Documentation alongside code
5. Monitor metrics throughout rollout

**Estimated Timeline:**
- Phase 1: 2 hours (analysis)
- Phase 2: 4-5 hours (abstraction)
- Phase 3: 4-5 hours (Daily.co)
- Testing: 3-4 hours
- **Total: 13-16 hours**

This document should be sufficient for a senior engineer to implement the feature independently with high confidence in the final result.
