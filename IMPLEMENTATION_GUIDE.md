# Daily.co Implementation Guide

## Overview
Implement multi-provider video platform support (Whereby + Daily.co) following PLAN.md.

## Reference Code Location
- **Reference branch:** `origin/igor/feat-dailyco` (on remote)
- **Worktree location:** `./reflector-dailyco-reference/`
- **Status:** Reference only - DO NOT merge or copy directly

## What Exists in Reference Branch (For Inspiration)

### ✅ Can Use As Reference (Well-Implemented)
```
server/reflector/video_platforms/
├── base.py              ← Platform abstraction (good design, copy-safe)
├── models.py            ← Data models (copy-safe)
├── registry.py          ← Registry pattern (copy-safe)
├── factory.py           ← Factory pattern (needs settings updates)
├── whereby.py           ← Whereby client (needs adaptation)
├── daily.py             ← Daily.co client (needs adaptation)
└── mock.py              ← Mock client (copy-safe for tests)

server/reflector/views/daily.py       ← Webhook handler (needs adaptation)
server/tests/test_video_platforms.py  ← Tests (good reference)
server/tests/test_daily_webhook.py    ← Tests (good reference)

www/app/[roomName]/components/
├── RoomContainer.tsx    ← Platform router (needs React Query)
├── DailyRoom.tsx        ← Daily component (needs React Query)
└── WherebyRoom.tsx      ← Whereby extraction (needs React Query)
```

### ⚠️ Needs Significant Changes (Use Logic Only)
- `server/reflector/db/rooms.py` - Reference removed calendar/webhook fields that main has
- `server/reflector/db/meetings.py` - Same issue (missing user_id handling differences)
- `server/reflector/views/rooms.py` - Main has calendar integration, webhooks, ICS sync
- `server/reflector/worker/process.py` - Main has different recording flow
- Migration files - Must regenerate against current main schema

### ❌ Do NOT Use (Outdated/Incompatible)
- `package.json`/`pnpm-lock.yaml` - Main uses different dependency versions
- Frontend API client calls - Main uses React Query (reference uses old OpenAPI client)
- Database migrations - Must create new ones from scratch
- Any files that delete features present in main (search, calendar, webhooks)

## Key Differences: Reference vs Current Main

| Aspect | Reference Branch | Current Main | Action Required |
|--------|------------------|--------------|-----------------|
| **API client** | Old OpenAPI generated | React Query hooks | Rewrite all API calls |
| **Database schema** | Simplified (removed features) | Has calendar, webhooks, full-text search | Merge carefully, preserve main features |
| **Settings** | Aug 2025 structure | Current structure | Adapt carefully |
| **Migrations** | Branched from Aug 1 | Current main (91+ commits ahead) | Regenerate from scratch |
| **Frontend deps** | `@daily-co/daily-js@0.81.0` | Check current versions | Update to compatible versions |
| **Package manager** | yarn | pnpm (maybe both?) | Use what main uses |

## Branch Divergence Analysis

**The reference branch is 91 commits behind main and severely diverged:**
- Reference: 8 commits, 3,689 insertions, 425 deletions
- Main since divergence: 320 files changed, 45,840 insertions, 16,827 deletions
- **Main has 12x more changes**

**Major features in main that reference lacks:**
1. Calendar integration (ICS sync with rooms)
2. Self-hosted GPU API infrastructure
3. Frontend OpenAPI React Query migration
4. Full-text search (backend + frontend)
5. Webhook system for room events
6. Environment variable migration
7. Security fixes and auth improvements
8. Docker production frontend
9. Meeting user ID removal (schema change)
10. NextJS version upgrades

**High conflict risk files:**
- `server/reflector/views/rooms.py` - 12x more changes in main
- `server/reflector/db/rooms.py` - Main added 7+ fields
- `www/package.json` - NextJS major version bump
- Database migrations - 20+ new migrations in main

## Implementation Approach

### Phase 1: Copy Clean Abstractions (1-2 hours)

**Files to copy directly from reference:**
```bash
# Core abstraction (review but mostly safe to copy)
cp -r reflector-dailyco-reference/server/reflector/video_platforms/ \
      server/reflector/

# BUT review each file for:
# - Import paths (make sure they match current main)
# - Settings references (adapt to current settings.py)
# - Type imports (ensure no circular dependencies)
```

**After copying, immediately:**
```bash
cd server
# Check for issues
uv run ruff check reflector/video_platforms/
# Fix any import errors or type issues
```

### Phase 2: Adapt to Current Main (2-3 hours)

**2.1 Settings Integration**

File: `server/reflector/settings.py`

Add at the appropriate location (near existing Whereby settings):

```python
# Daily.co API Integration (NEW)
DAILY_API_KEY: str | None = None
DAILY_WEBHOOK_SECRET: str | None = None
DAILY_SUBDOMAIN: str | None = None
AWS_DAILY_S3_BUCKET: str | None = None
AWS_DAILY_S3_REGION: str = "us-west-2"
AWS_DAILY_ROLE_ARN: str | None = None

# Platform Migration Feature Flags (NEW)
DAILY_MIGRATION_ENABLED: bool = False  # Conservative default
DAILY_MIGRATION_ROOM_IDS: list[str] = []
DEFAULT_VIDEO_PLATFORM: Literal["whereby", "daily"] = "whereby"
```

**2.2 Database Migration**

⚠️ **CRITICAL: Do NOT copy migration from reference**

Generate new migration:
```bash
cd server
uv run alembic revision -m "add_platform_support"
```

Edit the generated migration file to add `platform` column:
```python
def upgrade():
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("platform", sa.String(), nullable=False, server_default="whereby")
        )

    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("platform", sa.String(), nullable=False, server_default="whereby")
        )
```

**2.3 Update Database Models**

File: `server/reflector/db/rooms.py`

Add platform field (preserve all existing fields from main):
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reflector.video_platforms.models import Platform

class Room:
    # ... ALL existing fields from main (calendar, webhooks, etc.) ...

    # NEW: Platform field
    platform: "Platform" = sqlalchemy.Column(
        sqlalchemy.String,
        nullable=False,
        server_default="whereby",
    )
```

File: `server/reflector/db/meetings.py`

Same approach - add platform field, preserve everything from main.

**2.4 Integrate Platform Abstraction into rooms.py**

⚠️ **This is the most delicate part - main has calendar/webhook features**

File: `server/reflector/views/rooms.py`

Strategy:
1. Add imports at top
2. Modify meeting creation logic only
3. Preserve all calendar/webhook/ICS logic from main

```python
# Add imports
from reflector.video_platforms import (
    create_platform_client,
    get_platform_for_room,
)

# In create_meeting endpoint:
# OLD: Direct Whereby API calls
# NEW: Platform abstraction

# Find the meeting creation section and replace:
platform = get_platform_for_room(room.id)
client = create_platform_client(platform)

meeting_data = await client.create_meeting(
    room_name_prefix=room.name,
    end_date=meeting_data.end_date,
    room=room,
)

# Then create Meeting record with meeting_data.platform, meeting_data.meeting_id, etc.
```

**2.5 Add Daily.co Webhook Handler**

Copy from reference, minimal changes needed:
```bash
cp reflector-dailyco-reference/server/reflector/views/daily.py \
   server/reflector/views/
```

Register in `server/reflector/app.py`:
```python
from reflector.views import daily

app.include_router(daily.router, prefix="/v1/daily", tags=["daily"])
```

**2.6 Add Recording Processing Task**

File: `server/reflector/worker/process.py`

Add the `process_recording_from_url` task from reference (copy the function).

### Phase 3: Frontend Adaptation (3-4 hours)

**3.1 Determine Current API Client Pattern**

First, check how main currently makes API calls:
```bash
cd www
grep -r "api\." app/ | head -20
# Look for patterns like: api.v1Something()
```

**3.2 Create Components**

Copy component structure from reference but **rewrite all API calls**:

```bash
mkdir -p www/app/[roomName]/components
```

Files to create:
- `RoomContainer.tsx` - Platform router (mostly copy-safe, just fix imports)
- `DailyRoom.tsx` - Needs React Query API calls
- `WherebyRoom.tsx` - Extract current room page logic

**Example React Query pattern** (adapt to your actual API):
```typescript
import { api } from '@/app/api/client'

// In DailyRoom.tsx
const handleConsent = async () => {
  try {
    await api.v1MeetingAudioConsent({
      path: { meeting_id: meeting.id },
      body: { consent: true },
    })
    // ...
  } catch (error) {
    // ...
  }
}
```

**3.3 Add Daily.co Dependency**

Check current package manager:
```bash
cd www
ls package-lock.json yarn.lock pnpm-lock.yaml
```

Then install:
```bash
# If using pnpm
pnpm add @daily-co/daily-js@^0.81.0

# If using yarn
yarn add @daily-co/daily-js@^0.81.0
```

**3.4 Update TypeScript Types**

After backend changes, regenerate types:
```bash
cd www
pnpm openapi  # or yarn openapi
```

This should pick up the new `platform` field on Meeting type.

### Phase 4: Testing (2-3 hours)

**4.1 Copy Test Structure**

```bash
cp reflector-dailyco-reference/server/tests/test_video_platforms.py \
   server/tests/

cp reflector-dailyco-reference/server/tests/test_daily_webhook.py \
   server/tests/
```

**4.2 Fix Test Imports and Fixtures**

Update imports to match current test infrastructure:
- Check `server/tests/conftest.py` for fixture patterns
- Update database access patterns if changed
- Fix any import errors

**4.3 Run Tests**

```bash
cd server
# Run with environment variables for Mac
REDIS_HOST=localhost \
CELERY_BROKER_URL=redis://localhost:6379/1 \
CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
uv run pytest tests/test_video_platforms.py -v
```

### Phase 5: Environment Configuration

**Update `server/env.example`:**

Add at the end:
```bash
# Daily.co API Integration
DAILY_API_KEY=your-daily-api-key
DAILY_WEBHOOK_SECRET=your-daily-webhook-secret
DAILY_SUBDOMAIN=your-subdomain
AWS_DAILY_S3_BUCKET=your-daily-bucket
AWS_DAILY_S3_REGION=us-west-2
AWS_DAILY_ROLE_ARN=arn:aws:iam::ACCOUNT:role/DailyRecording

# Platform Selection
DAILY_MIGRATION_ENABLED=false           # Master switch
DAILY_MIGRATION_ROOM_IDS=[]            # Specific room IDs
DEFAULT_VIDEO_PLATFORM=whereby          # Default platform
```

## Decision Tree: Copy vs Adapt vs Rewrite

```
┌─ Is it pure abstraction logic? (base.py, registry.py, models.py)
│  YES → Copy directly, review imports
│  NO  → Continue ↓
│
├─ Does it touch database models?
│  YES → Adapt carefully, preserve main's fields
│  NO  → Continue ↓
│
├─ Does it make API calls on frontend?
│  YES → Rewrite using React Query
│  NO  → Continue ↓
│
├─ Is it a database migration?
│  YES → Generate fresh from current schema
│  NO  → Continue ↓
│
└─ Does it touch rooms.py or core business logic?
   YES → Merge carefully, preserve calendar/webhooks
   NO  → Safe to adapt from reference
```

## Verification Checklist

After each phase, verify:

**Phase 1 (Abstraction Layer):**
- [ ] `uv run ruff check server/reflector/video_platforms/` passes
- [ ] No circular import errors
- [ ] Can import `from reflector.video_platforms import create_platform_client`

**Phase 2 (Backend Integration):**
- [ ] `uv run ruff check server/` passes
- [ ] Migration file generated (not copied)
- [ ] Room and Meeting models have platform field
- [ ] rooms.py still has calendar/webhook features

**Phase 3 (Frontend):**
- [ ] `pnpm lint` passes
- [ ] No TypeScript errors
- [ ] No `@ts-ignore` for platform field
- [ ] API calls use React Query patterns

**Phase 4 (Testing):**
- [ ] Tests can be collected: `pytest tests/test_video_platforms.py --collect-only`
- [ ] Database fixtures work
- [ ] Mock platform works

**Phase 5 (Config):**
- [ ] env.example has Daily.co variables
- [ ] settings.py has all new variables
- [ ] No duplicate variable definitions

## Common Pitfalls

### 1. Database Schema Conflicts
**Problem:** Reference removed fields that main has (calendar, webhooks)
**Solution:** Always preserve main's fields, only add platform field

### 2. Migration Conflicts
**Problem:** Reference migration has wrong `down_revision`
**Solution:** Always generate fresh migration from current main

### 3. Frontend API Calls
**Problem:** Reference uses old API client patterns
**Solution:** Check current main's API usage, replicate that pattern

### 4. Import Errors
**Problem:** Circular imports with TYPE_CHECKING
**Solution:** Use `if TYPE_CHECKING:` for Room/Meeting imports in video_platforms

### 5. Test Database Issues
**Problem:** Tests fail with "could not translate host name 'postgres'"
**Solution:** Use environment variables: `REDIS_HOST=localhost DATABASE_URL=...`

### 6. Preserved Features Broken
**Problem:** Calendar/webhook features stop working
**Solution:** Carefully review rooms.py diff, only change meeting creation, not calendar logic

## File Modification Summary

**New files (can copy):**
- `server/reflector/video_platforms/*.py` (entire directory)
- `server/reflector/views/daily.py`
- `server/tests/test_video_platforms.py`
- `server/tests/test_daily_webhook.py`
- `www/app/[roomName]/components/RoomContainer.tsx`
- `www/app/[roomName]/components/DailyRoom.tsx`
- `www/app/[roomName]/components/WherebyRoom.tsx`

**Modified files (careful merging):**
- `server/reflector/settings.py` - Add Daily.co settings
- `server/reflector/db/rooms.py` - Add platform field
- `server/reflector/db/meetings.py` - Add platform field
- `server/reflector/views/rooms.py` - Integrate platform abstraction
- `server/reflector/worker/process.py` - Add process_recording_from_url
- `server/reflector/app.py` - Register daily router
- `server/env.example` - Add Daily.co variables
- `www/app/[roomName]/page.tsx` - Use RoomContainer
- `www/package.json` - Add @daily-co/daily-js

**Generated files (do not copy):**
- `server/migrations/versions/XXXXXX_add_platform_support.py` - Generate fresh

## Success Metrics

Implementation is complete when:
- [ ] All tests pass (including new platform tests)
- [ ] Linting passes (ruff, pnpm lint)
- [ ] Migration applies cleanly: `uv run alembic upgrade head`
- [ ] Can create Whereby meeting (existing flow unchanged)
- [ ] Can create Daily.co meeting (with env vars set)
- [ ] Frontend loads without TypeScript errors
- [ ] No features from main were accidentally removed

## Getting Help

**Reference documentation locations:**
- Implementation plan: `PLAN.md`
- Reference implementation: `./reflector-dailyco-reference/`
- Current main codebase: `./ ` (current directory)

**Compare implementations:**
```bash
# Compare specific files
diff reflector-dailyco-reference/server/reflector/video_platforms/base.py \
     server/reflector/video_platforms/base.py

# See what changed in rooms.py between reference branch point and now
git log --oneline --since="2025-08-01" -- server/reflector/views/rooms.py
```

**Key insight:** The reference branch validates the approach and provides working code patterns, but you're implementing fresh against current main to avoid merge conflicts and preserve all new features.
