# Multi-Provider Video Platform Implementation - Coder Briefing

## Your Mission

Implement multi-provider video platform support in Reflector, allowing the system to work with both Whereby and Daily.co video conferencing providers. The goal is to abstract the current Whereby-only implementation and add Daily.co as a second provider, with the ability to switch between them via environment variables.

**Branch:** `igor/dailico-2` (you're already on it)

**Estimated Time:** 12-16 hours (senior engineer)

**Complexity:** Medium-High (requires careful integration with existing codebase)

---

## What You Have

### 1. **PLAN.md** - Your Technical Specification (2,452 lines)
   - Complete step-by-step implementation guide
   - All code examples you need
   - Architecture diagrams and design rationale
   - Testing strategy and success metrics
   - **Read this first** to understand the overall approach

### 2. **IMPLEMENTATION_GUIDE.md** - Your Practical Guide
   - What to copy vs. adapt vs. rewrite
   - Common pitfalls and how to avoid them
   - Verification checklists for each phase
   - Decision trees for implementation choices
   - **Use this as your day-to-day reference**

### 3. **Reference Implementation** - `./reflector-dailyco-reference/`
   - Working implementation from 2.5 months ago
   - Good architecture and patterns
   - **BUT:** 91 commits behind current main, DO NOT merge directly
   - Use for inspiration and code patterns only

---

## Critical Context: Why Not Just Merge?

The reference branch (`origin/igor/feat-dailyco`) was started on August 1, 2025 and is now severely diverged from main:

- **91 commits behind main**
- Main has 12x more changes (45,840 insertions vs 3,689)
- Main added: calendar integration, webhooks, full-text search, React Query migration, security fixes
- Reference removed: features that main still has and needs

**Merging would be a disaster.** We're implementing fresh on current main, using the reference for validated patterns.

---

## High-Level Approach

### Phase 1: Analysis (2 hours)
- Study current Whereby integration
- Define abstraction requirements
- Create standard data models

### Phase 2: Abstraction Layer (4-5 hours)
- Build platform abstraction (base class, registry, factory)
- Extract Whereby into the abstraction
- Update database schema (add `platform` field)
- Integrate into rooms.py **without breaking calendar/webhooks**

### Phase 3: Daily.co Implementation (4-5 hours)
- Implement Daily.co client
- Add webhook handler
- Create frontend components (rewrite API calls for React Query)
- Add recording processing

### Phase 4: Testing (2-3 hours)
- Unit tests for platform abstraction
- Integration tests for webhooks
- Manual testing with both providers

---

## Key Files You'll Touch

### Backend (New)
```
server/reflector/video_platforms/
├── __init__.py
├── base.py              ← Abstract base class
├── models.py            ← Platform, MeetingData, VideoPlatformConfig
├── registry.py          ← Platform registration system
├── factory.py           ← Client creation and config
├── whereby.py           ← Whereby client wrapper
├── daily.py             ← Daily.co client
└── mock.py              ← Mock client for testing

server/reflector/views/daily.py       ← Daily.co webhooks
server/tests/test_video_platforms.py  ← Platform tests
server/tests/test_daily_webhook.py    ← Webhook tests
```

### Backend (Modified - Careful!)
```
server/reflector/settings.py          ← Add Daily.co settings
server/reflector/db/rooms.py          ← Add platform field, PRESERVE calendar fields
server/reflector/db/meetings.py       ← Add platform field
server/reflector/views/rooms.py       ← Integrate abstraction, PRESERVE calendar/webhooks
server/reflector/worker/process.py    ← Add process_recording_from_url task
server/reflector/app.py               ← Register daily router
server/env.example                    ← Document new env vars
```

### Frontend (New)
```
www/app/[roomName]/components/
├── RoomContainer.tsx    ← Platform router
├── DailyRoom.tsx        ← Daily.co component (rewrite API calls!)
└── WherebyRoom.tsx      ← Extract existing logic
```

### Frontend (Modified)
```
www/app/[roomName]/page.tsx           ← Use RoomContainer
www/package.json                      ← Add @daily-co/daily-js
```

### Database
```
server/migrations/versions/XXXXXX_add_platform_support.py  ← Generate fresh migration
```

---

## Critical Warnings ⚠️

### 1. **DO NOT Copy Database Migrations**
The reference migration has the wrong `down_revision` and is based on old schema.
```bash
# Instead:
cd server
uv run alembic revision -m "add_platform_support"
# Then edit the generated file
```

### 2. **DO NOT Remove Main's Features**
Main has calendar integration, webhooks, ICS sync that reference doesn't have.
When modifying `rooms.py`, only change meeting creation logic, preserve everything else.

### 3. **DO NOT Copy Frontend API Calls**
Reference uses old OpenAPI client. Main uses React Query.
Check how main currently makes API calls and replicate that pattern.

### 4. **DO NOT Copy package.json/migrations**
These files are severely outdated in reference.

### 5. **Preserve Type Safety**
Use `TYPE_CHECKING` imports to avoid circular dependencies:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from reflector.db.rooms import Room
```

---

## How to Start

### Day 1 Morning: Setup & Understanding (2-3 hours)
```bash
# 1. Verify you're on the right branch
git branch
# Should show: igor/dailico-2

# 2. Read the docs (in order)
# - PLAN.md (skim to understand scope, read Phase 1 carefully)
# - IMPLEMENTATION_GUIDE.md (read fully, bookmark it)

# 3. Study current Whereby integration
cat server/reflector/views/rooms.py | grep -A 20 "whereby"
cat www/app/[roomName]/page.tsx

# 4. Check reference implementation structure
ls -la reflector-dailyco-reference/server/reflector/video_platforms/
```

### Day 1 Afternoon: Phase 1 Execution (2-3 hours)
```bash
# 5. Copy video_platforms directory from reference
cp -r reflector-dailyco-reference/server/reflector/video_platforms/ \
      server/reflector/

# 6. Review and fix imports
cd server
uv run ruff check reflector/video_platforms/

# 7. Add settings to settings.py (see PLAN.md Phase 2.7)

# 8. Test imports work
uv run python -c "from reflector.video_platforms import create_platform_client; print('OK')"
```

### Day 2: Phase 2 - Database & Integration (4-5 hours)
```bash
# 9. Generate migration
uv run alembic revision -m "add_platform_support"
# Edit the file following PLAN.md Phase 2.8

# 10. Update Room/Meeting models
# Add platform field, PRESERVE all existing fields

# 11. Integrate into rooms.py
# Carefully modify meeting creation, preserve calendar/webhooks

# 12. Add Daily.co webhook handler
cp reflector-dailyco-reference/server/reflector/views/daily.py \
   server/reflector/views/
# Register in app.py
```

### Day 3: Phase 3 - Frontend & Testing (4-5 hours)
```bash
# 13. Create frontend components
mkdir -p www/app/[roomName]/components

# 14. Add Daily.co dependency
cd www
pnpm add @daily-co/daily-js@^0.81.0

# 15. Create RoomContainer, DailyRoom, WherebyRoom
# IMPORTANT: Rewrite API calls using React Query patterns

# 16. Regenerate types
pnpm openapi

# 17. Copy and adapt tests
cp reflector-dailyco-reference/server/tests/test_*.py server/tests/

# 18. Run tests
cd server
REDIS_HOST=localhost \
CELERY_BROKER_URL=redis://localhost:6379/1 \
uv run pytest tests/test_video_platforms.py -v
```

---

## Verification Checklist

After implementation, all of these must pass:

**Backend:**
- [ ] `cd server && uv run ruff check .` passes
- [ ] `uv run alembic upgrade head` works cleanly
- [ ] `uv run pytest tests/test_video_platforms.py` passes
- [ ] Can import: `from reflector.video_platforms import create_platform_client`
- [ ] Settings has all Daily.co variables

**Frontend:**
- [ ] `cd www && pnpm lint` passes
- [ ] No TypeScript errors
- [ ] `pnpm openapi` generates platform field
- [ ] No `@ts-ignore` for platform field

**Integration:**
- [ ] Whereby meetings still work (existing flow unchanged)
- [ ] Calendar/webhook features still work in rooms.py
- [ ] env.example documents all new variables

---

## When You're Stuck

### Check These Resources:
1. **PLAN.md** - Detailed code examples for your exact scenario
2. **IMPLEMENTATION_GUIDE.md** - Common pitfalls section
3. **Reference code** - See how it was solved before
4. **Git diff** - Compare reference to your implementation

### Compare Files:
```bash
# See what reference did
diff reflector-dailyco-reference/server/reflector/views/rooms.py \
     server/reflector/views/rooms.py

# See what changed in main since reference branch
git log --oneline --since="2025-08-01" -- server/reflector/views/rooms.py
```

### Common Issues:
- **Circular imports:** Use `TYPE_CHECKING` pattern
- **Tests fail with postgres error:** Use `REDIS_HOST=localhost` env vars
- **Frontend API calls broken:** Check current React Query patterns in main
- **Migrations fail:** Ensure you generated fresh, not copied

---

## Success Looks Like

When you're done:
- ✅ All tests pass
- ✅ Linting passes
- ✅ Can create Whereby meetings (unchanged behavior)
- ✅ Can create Daily.co meetings (with env vars)
- ✅ Calendar/webhooks still work
- ✅ Frontend has no TypeScript errors
- ✅ Platform selection via environment variables works

---

## Communication

If you need clarification on requirements, have questions about architecture decisions, or find issues with the spec, document them clearly with:
- What you expected
- What you found
- Your proposed solution

The PLAN.md document is comprehensive but you may find edge cases. Use your engineering judgment and document decisions.

---

## Final Notes

**This is not a simple copy-paste job.** You're doing careful integration work where you need to:
- Understand the abstraction pattern (PLAN.md)
- Preserve all of main's features
- Adapt reference code to current patterns
- Think about edge cases and testing

Take your time with Phase 2 (rooms.py integration) - that's where most bugs will come from if you accidentally break calendar/webhook features.

**Good luck! You've got comprehensive specs, working reference code, and a clean starting point. You can do this.**

---

## Quick Reference

```bash
# Your workspace
├── PLAN.md                        ← Complete technical spec (read first)
├── IMPLEMENTATION_GUIDE.md        ← Practical guide (bookmark this)
├── CODER_BRIEFING.md             ← This file
└── reflector-dailyco-reference/   ← Reference implementation (inspiration only)

# Key commands
cd server && uv run ruff check .                    # Lint backend
cd www && pnpm lint                                  # Lint frontend
cd server && uv run alembic revision -m "..."       # Create migration
cd www && pnpm openapi                              # Regenerate types
cd server && uv run pytest -v                       # Run tests
```
