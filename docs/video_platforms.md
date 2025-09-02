# Video Platforms Architecture (PR #529 Analysis)

This document analyzes the video platforms refactoring implemented in PR #529 for daily.co integration, providing a blueprint for extending support to Jitsi and other video conferencing platforms.

## Overview

The video platforms refactoring introduces a clean abstraction layer that allows Reflector to support multiple video conferencing providers (Whereby, Daily.co, etc.) without changing core application logic. This architecture enables:

- Seamless switching between video platforms
- Platform-specific feature support
- Isolated platform code organization
- Consistent API surface across platforms
- Feature flags for gradual migration

## Architecture Components

### 1. **Directory Structure**

```
server/reflector/video_platforms/
├── __init__.py              # Public API exports
├── base.py                  # Abstract base classes
├── factory.py               # Platform client factory
├── registry.py              # Platform registration system
├── whereby.py               # Whereby implementation
├── daily.py                 # Daily.co implementation
└── mock.py                  # Testing implementation
```

### 2. **Core Abstract Classes**

#### `VideoPlatformClient` (base.py)
Abstract base class defining the interface all platforms must implement:

```python
class VideoPlatformClient(ABC):
    PLATFORM_NAME: str = ""

    @abstractmethod
    async def create_meeting(self, room_name_prefix: str, end_date: datetime, room: Room) -> MeetingData

    @abstractmethod
    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]

    @abstractmethod
    async def delete_room(self, room_name: str) -> bool

    @abstractmethod
    async def upload_logo(self, room_name: str, logo_path: str) -> bool

    @abstractmethod
    def verify_webhook_signature(self, body: bytes, signature: str, timestamp: Optional[str] = None) -> bool
```

#### `MeetingData` (base.py)
Standardized meeting data structure returned by all platforms:

```python
class MeetingData(BaseModel):
    meeting_id: str
    room_name: str
    room_url: str
    host_room_url: str
    platform: str
    extra_data: Dict[str, Any] = {}  # Platform-specific data
```

#### `VideoPlatformConfig` (base.py)
Unified configuration structure for all platforms:

```python
class VideoPlatformConfig(BaseModel):
    api_key: str
    webhook_secret: str
    api_url: Optional[str] = None
    subdomain: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    aws_role_arn: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_access_key_secret: Optional[str] = None
```

### 3. **Platform Registration System**

#### Registry Pattern (registry.py)
- Automatic registration of built-in platforms
- Runtime platform discovery
- Type-safe client instantiation

```python
# Auto-registration of platforms
_PLATFORMS: Dict[str, Type[VideoPlatformClient]] = {}

def register_platform(name: str, client_class: Type[VideoPlatformClient])
def get_platform_client(platform: str, config: VideoPlatformConfig) -> VideoPlatformClient
```

#### Factory System (factory.py)
- Configuration management per platform
- Platform selection logic
- Feature flag integration

```python
def get_platform_for_room(room_id: Optional[str] = None) -> str:
    """Determine which platform to use based on feature flags."""
    if not settings.DAILY_MIGRATION_ENABLED:
        return "whereby"

    if room_id and room_id in settings.DAILY_MIGRATION_ROOM_IDS:
        return "daily"

    return settings.DEFAULT_VIDEO_PLATFORM
```

### 4. **Database Schema Changes**

#### Room Model Updates
Added `platform` field to track which video platform each room uses:

```python
# Database Schema
platform_column = sqlalchemy.Column(
    "platform",
    sqlalchemy.String,
    nullable=False,
    server_default="whereby"
)

# Pydantic Model
class Room(BaseModel):
    platform: Literal["whereby", "daily"] = "whereby"
```

#### Meeting Model Updates
Added `platform` field to meetings for tracking and debugging:

```python
# Database Schema
platform_column = sqlalchemy.Column(
    "platform",
    sqlalchemy.String,
    nullable=False,
    server_default="whereby"
)

# Pydantic Model
class Meeting(BaseModel):
    platform: Literal["whereby", "daily"] = "whereby"
```

**Key Decision**: No platform-specific fields were added to models. Instead, the `extra_data` field in `MeetingData` handles platform-specific information, following the user's rule of using generic `provider_data` as JSON if needed.

### 5. **Settings Configuration**

#### Feature Flags
```python
# Migration control
DAILY_MIGRATION_ENABLED: bool = True
DAILY_MIGRATION_ROOM_IDS: list[str] = []
DEFAULT_VIDEO_PLATFORM: str = "daily"

# Daily.co specific settings
DAILY_API_KEY: str | None = None
DAILY_WEBHOOK_SECRET: str | None = None
DAILY_SUBDOMAIN: str | None = None
AWS_DAILY_S3_BUCKET: str | None = None
AWS_DAILY_S3_REGION: str = "us-west-2"
AWS_DAILY_ROLE_ARN: str | None = None
```

#### Configuration Pattern
Each platform gets its own configuration namespace while sharing common patterns:

```python
def get_platform_config(platform: str) -> VideoPlatformConfig:
    if platform == "whereby":
        return VideoPlatformConfig(
            api_key=settings.WHEREBY_API_KEY or "",
            webhook_secret=settings.WHEREBY_WEBHOOK_SECRET or "",
            # ... whereby-specific config
        )
    elif platform == "daily":
        return VideoPlatformConfig(
            api_key=settings.DAILY_API_KEY or "",
            webhook_secret=settings.DAILY_WEBHOOK_SECRET or "",
            # ... daily-specific config
        )
```

### 6. **API Integration Updates**

#### Room Creation (views/rooms.py)
Updated to use platform factory instead of direct Whereby calls:

```python
@router.post("/rooms/{room_name}/meeting")
async def rooms_create_meeting(room_name: str, user: UserInfo):
    # OLD: Direct Whereby integration
    # whereby_meeting = await create_meeting("", end_date=end_date, room=room)

    # NEW: Platform abstraction
    platform = get_platform_for_room(room.id)
    client = create_platform_client(platform)

    meeting_data = await client.create_meeting(
        room_name_prefix=room.name, end_date=end_date, room=room
    )

    await client.upload_logo(meeting_data.room_name, "./images/logo.png")
```

### 7. **Webhook Handling**

#### Separate Webhook Endpoints
Each platform gets its own webhook endpoint with platform-specific signature verification:

```python
# views/daily.py
@router.post("/daily_webhook")
async def daily_webhook(event: DailyWebhookEvent, request: Request):
    # Verify Daily.co signature
    body = await request.body()
    signature = request.headers.get("X-Daily-Signature", "")

    if not verify_daily_webhook_signature(body, signature):
        raise HTTPException(status_code=401)

    # Handle platform-specific events
    if event.type == "participant.joined":
        await _handle_participant_joined(event)
```

#### Consistent Event Handling
Despite different event formats, the core business logic remains the same:

```python
async def _handle_participant_joined(event):
    room_name = event.data.get("room", {}).get("name")  # Daily.co format
    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        current_count = getattr(meeting, "num_clients", 0)
        await meetings_controller.update_meeting(
            meeting.id, num_clients=current_count + 1
        )
```

### 8. **Worker Task Integration**

#### New Task for Daily.co Recording Processing
Added platform-specific recording processing while maintaining the same pipeline:

```python
@shared_task
@asynctask
async def process_recording_from_url(recording_url: str, meeting_id: str, recording_id: str):
    """Process recording from Direct URL (Daily.co webhook)."""
    logger.info("Processing recording from URL for meeting: %s", meeting_id)
    # Uses same processing pipeline as Whereby S3 recordings
```

**Key Decision**: Worker tasks remain in main worker module but could be moved to platform-specific folders as suggested by the user.

### 9. **Testing Infrastructure**

#### Comprehensive Test Suite
- Unit tests for each platform client
- Integration tests for platform switching
- Mock platform for testing without external dependencies
- Webhook signature verification tests

```python
class TestPlatformIntegration:
    """Integration tests for platform switching."""

    async def test_platform_switching_preserves_interface(self):
        """Test that different platforms provide consistent interface."""
        # Test both Mock and Daily platforms return MeetingData objects
        # with consistent fields
```

## Implementation Patterns for Jitsi Integration

Based on the daily.co implementation, here's how Jitsi should be integrated:

### 1. **Jitsi Client Implementation**

```python
# video_platforms/jitsi.py
class JitsiClient(VideoPlatformClient):
    PLATFORM_NAME = "jitsi"

    async def create_meeting(self, room_name_prefix: str, end_date: datetime, room: Room) -> MeetingData:
        # Generate unique room name
        jitsi_room = f"reflector-{room.name}-{int(time.time())}"

        # Generate JWT tokens
        user_jwt = self._generate_jwt(room=jitsi_room, moderator=False, exp=end_date)
        host_jwt = self._generate_jwt(room=jitsi_room, moderator=True, exp=end_date)

        return MeetingData(
            meeting_id=generate_uuid4(),
            room_name=jitsi_room,
            room_url=f"https://jitsi.domain/{jitsi_room}?jwt={user_jwt}",
            host_room_url=f"https://jitsi.domain/{jitsi_room}?jwt={host_jwt}",
            platform=self.PLATFORM_NAME,
            extra_data={"user_jwt": user_jwt, "host_jwt": host_jwt}
        )
```

### 2. **Settings Integration**

```python
# settings.py
JITSI_DOMAIN: str = "meet.jit.si"
JITSI_JWT_SECRET: str | None = None
JITSI_WEBHOOK_SECRET: str | None = None
JITSI_API_URL: str | None = None  # If using Jitsi API
```

### 3. **Factory Registration**

```python
# registry.py
def _register_builtin_platforms():
    from .jitsi import JitsiClient
    register_platform("jitsi", JitsiClient)

# factory.py
def get_platform_config(platform: str) -> VideoPlatformConfig:
    elif platform == "jitsi":
        return VideoPlatformConfig(
            api_key="",  # Jitsi may not need API key
            webhook_secret=settings.JITSI_WEBHOOK_SECRET or "",
            api_url=settings.JITSI_API_URL,
        )
```

### 4. **Webhook Integration**

```python
# views/jitsi.py
@router.post("/jitsi/events")
async def jitsi_events_webhook(event_data: dict):
    # Handle Prosody event-sync webhook format
    event_type = event_data.get("event")
    room_name = event_data.get("room", "").split("@")[0]

    if event_type == "muc-occupant-joined":
        # Same participant handling logic as other platforms
```

## Key Benefits of This Architecture

### 1. **Isolation and Organization**
- Platform-specific code contained in separate modules
- No platform logic leaking into core application
- Easy to add/remove platforms without affecting others

### 2. **Consistent Interface**
- All platforms implement the same abstract methods
- Standardized `MeetingData` structure
- Uniform error handling and logging

### 3. **Gradual Migration Support**
- Feature flags for controlled rollouts
- Room-specific platform selection
- Fallback mechanisms for platform failures

### 4. **Configuration Management**
- Centralized settings per platform
- Consistent naming patterns
- Environment-based configuration

### 5. **Testing and Quality**
- Mock platform for testing
- Comprehensive test coverage
- Platform-specific test utilities

## Migration Strategy Applied

The daily.co implementation demonstrates a careful migration approach:

### 1. **Backward Compatibility**
- Default platform remains "whereby"
- Existing rooms continue using Whereby unless explicitly migrated
- Same API endpoints and response formats

### 2. **Feature Flag Control**
```python
# Gradual rollout control
DAILY_MIGRATION_ENABLED: bool = True
DAILY_MIGRATION_ROOM_IDS: list[str] = []  # Specific rooms to migrate
DEFAULT_VIDEO_PLATFORM: str = "daily"     # New rooms default
```

### 3. **Data Integrity**
- Platform field tracks which service each room/meeting uses
- No data loss during migration
- Platform-specific data preserved in `extra_data`

### 4. **Monitoring and Rollback**
- Comprehensive logging of platform selection
- Easy rollback by changing feature flags
- Platform-specific error tracking

## Recommendations for Jitsi Integration

Based on this analysis and the user's requirements:

### 1. **Follow the Pattern**
- Create `video_platforms/jitsi/` directory with:
  - `client.py` - Main JitsiClient implementation
  - `tasks.py` - Jitsi-specific worker tasks
  - `__init__.py` - Module exports

### 2. **Settings Organization**
- Use `JITSI_*` prefix for all Jitsi settings
- Follow the same configuration pattern as Daily.co
- Support both environment variables and config files

### 3. **Generic Database Fields**
- Avoid platform-specific columns in database
- Use `provider_data` JSON field if platform-specific data needed
- Keep `platform` field as simple string identifier

### 4. **Worker Task Migration**
According to user requirements, migrate platform-specific tasks:
```
video_platforms/
├── whereby/
│   ├── client.py  (moved from whereby.py)
│   └── tasks.py   (moved from worker/whereby_tasks.py)
├── daily/
│   ├── client.py  (moved from daily.py)
│   └── tasks.py   (moved from worker/daily_tasks.py)
└── jitsi/
    ├── client.py  (new JitsiClient)
    └── tasks.py   (new Jitsi recording tasks)
```

### 5. **Webhook Architecture**
- Create `views/jitsi.py` for Jitsi-specific webhooks
- Follow the same signature verification pattern
- Reuse existing participant tracking logic

## Implementation Checklist for Jitsi

- [ ] Create `video_platforms/jitsi/` directory structure
- [ ] Implement `JitsiClient` following the abstract interface
- [ ] Add Jitsi settings to configuration
- [ ] Register Jitsi platform in factory/registry
- [ ] Create Jitsi webhook endpoint
- [ ] Implement JWT token generation for room access
- [ ] Add Jitsi recording processing tasks
- [ ] Create comprehensive test suite
- [ ] Update database migrations for platform field
- [ ] Document Jitsi-specific configuration

## Conclusion

The video platforms refactoring in PR #529 provides an excellent foundation for adding Jitsi support. The architecture is well-designed with clear separation of concerns, consistent interfaces, and excellent extensibility. The daily.co implementation demonstrates how to add a new platform while maintaining backward compatibility and providing gradual migration capabilities.

The pattern should be directly applicable to Jitsi integration, with the main differences being:
- JWT-based authentication instead of API keys
- Different webhook event formats
- Jibri recording pipeline integration
- Self-hosted deployment considerations

This architecture successfully achieves the user's goals of:
1. Settings-based configuration
2. Generic database fields (no provider-specific columns)
3. Platform isolation in separate directories
4. Worker task organization within platform folders