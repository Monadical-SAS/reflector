# Presence System Race Condition: Design Document

## Executive Summary

Users in the same Reflector room can end up in **different Daily.co rooms** due to race conditions in meeting lifecycle management. This document details the root cause, why current mitigations are insufficient, and proposes a solution that eliminates the race by design.

---

## Problem Statement

When a user quickly leaves and rejoins a meeting (e.g., closes tab and reopens within seconds), they may find themselves in a different Daily.co room than other participants in the same Reflector room. This breaks the core assumption that all users in a Reflector room share the same video call.

### Symptoms
- User A and User B are in the same Reflector room but different Daily.co rooms
- User reports "I can't see/hear the other participant"
- Meeting appears active but users are isolated

---

## Evidence: Hypothesis Simulation

A simulation was built to model the presence system and find race conditions through randomized action sequences.

**Location**: `server/tests/simulation/`

```bash
cd server

# Current system config - finds race conditions
uv run pytest tests/simulation/test_presence_race.py::test_presence_race_conditions_current_system
# Result: XFAIL (expected failure - race found)

# Fixed system config - no race conditions
uv run pytest tests/simulation/test_presence_race.py::test_presence_no_race_conditions_fixed_system
# Result: PASS
```

The simulation models:
- Discrete time clock for deterministic replay
- Daily.co rooms, participants, presence API with configurable lag
- Reflector meetings, sessions, webhooks
- User state machine: `idle → joining → handshaking → connected → leaving → idle`
- Background tasks: `poll_daily_room_presence`, `process_meetings`

### Key Finding

The simulation proves that **even with the Daily API call**, a race window exists during WebRTC handshake when users are invisible to the presence API.

---

## Current System Analysis

### Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  Daily.co   │
│  (Next.js)  │     │  (FastAPI)  │     │    API      │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Database   │
                    │  (Sessions) │
                    └─────────────┘
```

### Relevant Code Paths

#### 1. Meeting Join Flow
- **File**: `server/reflector/views/rooms.py`
- **Endpoint**: `POST /rooms/{room_name}/meeting`
- Returns existing active meeting or creates new one
- User then connects to Daily.co via WebRTC (frontend)

#### 2. Presence Polling
- **File**: `server/reflector/worker/process.py:642`
- **Function**: `poll_daily_room_presence()`
- Called by webhooks (`participant.joined`, `participant.left`) and `/joined`, `/leave` endpoints
- Queries Daily API for current participants
- Updates `daily_participant_sessions` table in database

#### 3. Meeting Deactivation
- **File**: `server/reflector/worker/process.py:754`
- **Function**: `process_meetings()`
- Runs periodically (every 60s via Celery beat)
- Checks if meetings should be deactivated

**Current implementation** (lines 806-833):
```python
if meeting.platform == "daily":
    try:
        presence = await client.get_room_presence(meeting.room_name)
        has_active_sessions = presence.total_count > 0
        # ...
    except Exception:
        logger_.warning("Daily.co presence API failed, falling back to DB sessions")
        room_sessions = await client.get_room_sessions(meeting.room_name)
        has_active_sessions = bool(
            room_sessions and any(s.ended_at is None for s in room_sessions)
        )
```

**Key observation**: The code already uses the Daily API (`get_room_presence`), not just the database. The race condition persists despite this.

### Endpoints from feature-leave-endpoint Branch

The `feature-leave-endpoint` branch added explicit leave/join notifications:

| Endpoint | Purpose | Trigger |
|----------|---------|---------|
| `POST /rooms/{room_name}/meetings/{meeting_id}/join` | Get meeting info | User navigates to room |
| `POST /rooms/{room_name}/meetings/{meeting_id}/joined` | Signal connection complete | After WebRTC connects |
| `POST /rooms/{room_name}/meetings/{meeting_id}/leave` | Signal user leaving | Tab close via sendBeacon |

These endpoints trigger `poll_daily_room_presence_task` to update session state faster than waiting for webhooks.

---

## Race Condition: Detailed Analysis

### The Fundamental Problem

**The backend has no knowledge of users who are in the process of joining (WebRTC handshake phase).**

Data sources available to backend:
| Source | What it knows | Limitation |
|--------|---------------|------------|
| Daily Presence API | Currently connected users | 0-500ms lag; doesn't see handshaking users |
| Database sessions | Historical join/leave events | Stale; updated by polls |
| Webhooks | Join/leave events | Delayed; can fail |

**Gap**: No source knows about users between "decided to join" and "WebRTC handshake complete".

### Race Scenario Timeline

```
T+0ms:    User A connected to Meeting M1, visible in Daily presence
T+1000ms: User A closes browser tab
T+1050ms: participant.left webhook fires → poll_daily_room_presence queued
T+1500ms: User A reopens tab (quick rejoin)
T+1600ms: POST /meeting returns M1 (still active)
T+1700ms: Frontend starts WebRTC handshake
T+2000ms: User A in handshake - NOT visible to Daily presence API
T+2100ms: poll runs → sees 0 participants → marks session as left_at
T+3000ms: process_meetings runs
T+3100ms: Daily API returns 0 participants (user still handshaking)
T+3200ms: has_active_sessions=False, has_had_sessions=True
T+3300ms: Meeting deactivated, Daily room deleted
T+4000ms: User A WebRTC completes → Daily room is gone!
T+5000ms: User B joins same Reflector room → new Meeting M2 created

RESULT: User A orphaned, User B in different Daily room
```

### Why Current Mitigations Are Insufficient

#### 1. Using Daily API (already implemented)
The code already calls `get_room_presence()` instead of relying solely on database sessions. **This doesn't help** because the Daily presence API itself doesn't see users during WebRTC handshake (0-500ms consistency lag + handshake duration of 500-3000ms).

#### 2. Fallback to Database
When Daily API fails, the code falls back to database sessions. This is **worse** because database is even more stale than the API.

#### 3. Leave/Join Endpoints
The `/joined` and `/leave` endpoints trigger immediate polls, reducing the window but **not eliminating it**. The poll still only sees what Daily presence API reports.

---

## Proposed Solutions

### Option A: Grace Period (Not Recommended)

Add a time-based buffer before deactivation.

```python
GRACE_PERIOD_SECONDS = 10

if not has_active_sessions and has_had_sessions:
    recent_activity = await get_recent_activity(meeting_id, within_seconds=GRACE_PERIOD_SECONDS)
    if recent_activity:
        continue  # Skip deactivation
```

**Pros:**
- Simple to implement
- Low risk

**Cons:**
- Arbitrary timeout value (why 10s? why not 5s or 30s?)
- Feels like a hack ("setTimeout solution")
- Delays legitimate deactivation
- Doesn't eliminate race, just makes it less likely

### Option B: Track "Intent to Join" (Recommended)

Add explicit state tracking for users who are in the process of joining.

**New endpoint**: `POST /rooms/{room_name}/meetings/{meeting_id}/joining`

**Flow change**:
```
Current:
1. POST /join → get meeting info
2. Render Daily iframe (start WebRTC)
3. POST /joined (after connected)

Proposed:
1. POST /join → get meeting info
2. POST /joining → "I'm about to connect" ← NEW (wait for 200 OK)
3. Render Daily iframe (start WebRTC)
4. POST /joined (after connected)
```

**Backend tracking**:
```python
# On /joining endpoint
await pending_joins.create(meeting_id=meeting_id, user_id=user_id, created_at=now())

# In process_meetings
pending = await pending_joins.get_recent(meeting_id, max_age_seconds=30)
if pending:
    logger.info("Meeting has pending joins, skipping deactivation")
    continue

# On /joined endpoint or timeout
await pending_joins.delete(meeting_id=meeting_id, user_id=user_id)
```

**Pros:**
- Eliminates race by design (backend knows before Daily does)
- Explicit state machine, not time-based guessing
- Clear semantics

**Cons:**
- Adds ~50-200ms latency (one round-trip before iframe renders)
- Requires frontend changes
- Needs cleanup mechanism for abandoned joins (user closes tab during handshake)

### Option C: Optimistic Locking with Version

Track meeting "version" that must match for deactivation.

**Concept**: Each join attempt increments a version. Deactivation only proceeds if version hasn't changed since presence check.

**Cons:**
- Complex to implement correctly
- Still has edge cases with concurrent joins

---

## Recommended Approach: Option B

**Track "Intent to Join"** is the cleanest solution because it:

1. **Eliminates the race by design** - no timing windows
2. **Makes state explicit** - joining/connected/leaving are tracked, not inferred
3. **Aligns with existing patterns** - similar to `/joined` and `/leave` endpoints
4. **No arbitrary timeouts** - unlike grace period

### Data Model Change

Add tracking for pending joins. Options:

| Storage | Pros | Cons |
|---------|------|------|
| Redis key | Fast, auto-expire | Lost on Redis restart |
| Database table | Persistent, queryable | Slightly slower |
| In-memory | Fastest | Lost on server restart |

**Recommendation**: Redis with TTL (30s expiry) for simplicity. Pending joins are ephemeral - if Redis restarts, worst case is a brief deactivation delay.

```python
# Redis key format
pending_join:{meeting_id}:{user_id} = {timestamp}
# TTL: 30 seconds
```

### Implementation Checklist

1. **Backend: Add `/joining` endpoint**
   - File: `server/reflector/views/rooms.py`
   - Creates Redis key with 30s TTL
   - Returns 200 OK

2. **Backend: Modify `process_meetings()`**
   - File: `server/reflector/worker/process.py`
   - Before deactivation, check for pending joins
   - If any exist, skip deactivation

3. **Backend: Modify `/joined` endpoint**
   - Clear pending join on successful connection

4. **Frontend: Call `/joining` before WebRTC**
   - File: `www/app/[roomName]/components/DailyRoom.tsx`
   - Await response before rendering Daily iframe

5. **Update simulation**
   - Add `joining` state tracking to match new design
   - Verify race condition is eliminated

6. **Integration tests**
   - Test quick rejoin scenario
   - Test abandoned join (user closes during handshake)
   - Test concurrent joins from multiple users

---

## Files Reference

### Core Files to Modify
| File | Purpose |
|------|---------|
| `server/reflector/views/rooms.py` | Add `/joining` endpoint |
| `server/reflector/worker/process.py` | Check pending joins before deactivation |
| `www/app/[roomName]/components/DailyRoom.tsx` | Call `/joining` before WebRTC |

### Reference Files
| File | Contains |
|------|----------|
| `server/reflector/video_platforms/daily.py:128` | `get_room_presence()` - Daily API call |
| `server/reflector/worker/process.py:642` | `poll_daily_room_presence()` - presence polling |
| `server/reflector/views/daily.py:125` | Webhook handlers |
| `server/tests/simulation/` | Hypothesis simulation proving the race |
| `server/tests/test_daily_presence_deactivation.py` | Unit tests for presence logic |

### Simulation Files
| File | Purpose |
|------|---------|
| `tests/simulation/system.py` | Main simulation engine |
| `tests/simulation/config.py` | Current vs fixed system configs |
| `tests/simulation/state.py` | State dataclasses |
| `tests/simulation/test_presence_race.py` | Hypothesis stateful tests |
| `tests/simulation/test_targeted_scenarios.py` | Specific race scenarios |
| `server/reflector/presence/model.py` | Shared state machine model |

---

## Alternative Considered: Remove DB Fallback

One simpler change discussed: remove the database fallback when Daily API fails, and "fail loudly" instead.

```python
# Current (with fallback)
try:
    presence = await client.get_room_presence(meeting.room_name)
    has_active_sessions = presence.total_count > 0
except Exception:
    # Fallback to stale DB
    room_sessions = await client.get_room_sessions(meeting.room_name)
    has_active_sessions = bool(room_sessions and any(s.ended_at is None for s in room_sessions))

# Proposed (fail loudly)
try:
    presence = await client.get_room_presence(meeting.room_name)
    has_active_sessions = presence.total_count > 0
except Exception:
    logger.error("Daily API failed, skipping deactivation check for this meeting")
    continue  # Don't deactivate if we can't verify
```

**This helps but doesn't eliminate the race** - it only removes one failure mode (stale DB). The core race (handshake invisibility) remains.

---

## Conclusion

The presence system race condition is a **data model gap**, not a timing issue that can be solved with grace periods. The backend needs explicit knowledge of users who intend to join, before they become visible to the Daily presence API.

The recommended fix is to add a `/joining` endpoint that the frontend calls before starting WebRTC. This creates a "reservation" that prevents premature meeting deactivation during the handshake window.

This approach:
- Eliminates the race by design
- Adds minimal latency (~50-200ms)
- Follows explicit state machine principles
- Avoids arbitrary timeout hacks

---

## Appendix: Simulation Test Results

```
$ uv run pytest tests/simulation/ -v

tests/simulation/test_model_conformance.py::TestModelConformance::test_simulation_uses_model_states PASSED
tests/simulation/test_model_conformance.py::TestModelConformance::test_simulation_respects_transitions PASSED
tests/simulation/test_model_conformance.py::TestModelConformance::test_simulation_invalid_transitions_checked PASSED
tests/simulation/test_model_conformance.py::TestModelConformance::test_simulation_implements_protocols PASSED
tests/simulation/test_model_conformance.py::TestModelConformance::test_simulation_uses_shared_invariants PASSED
tests/simulation/test_model_conformance.py::TestProductionStateMachine::test_state_machine_has_all_states PASSED
tests/simulation/test_model_conformance.py::TestProductionStateMachine::test_state_machine_valid_transitions PASSED
tests/simulation/test_model_conformance.py::TestProductionStateMachine::test_state_machine_invalid_transitions_raise PASSED
tests/simulation/test_model_conformance.py::TestProductionStateMachine::test_guarded_user_state_transitions PASSED
tests/simulation/test_model_conformance.py::TestProductionStateMachine::test_guarded_user_state_rejects_invalid PASSED
tests/simulation/test_model_conformance.py::TestProductionStateMachine::test_guarded_user_state_tracks_history PASSED
tests/simulation/test_model_conformance.py::TestInvariantConsistency::test_invariants_same_between_model_and_simulation PASSED
tests/simulation/test_model_conformance.py::test_quick_conformance_check PASSED
tests/simulation/test_presence_race.py::TestPresenceRaceFixed::runTest PASSED
tests/simulation/test_presence_race.py::test_presence_race_conditions_current_system XFAIL
tests/simulation/test_presence_race.py::test_presence_no_race_conditions_fixed_system PASSED
tests/simulation/test_presence_race.py::test_smoke_presence_simulation PASSED
tests/simulation/test_targeted_scenarios.py::TestQuickRejoinRace::test_quick_rejoin_causes_split PASSED
tests/simulation/test_targeted_scenarios.py::TestQuickRejoinRace::test_quick_rejoin_fixed_system PASSED
tests/simulation/test_targeted_scenarios.py::TestSimultaneousJoins::test_two_users_join_simultaneously PASSED
tests/simulation/test_targeted_scenarios.py::TestProcessMeetingsRace::test_process_meetings_during_handshake PASSED
tests/simulation/test_targeted_scenarios.py::TestPresenceLagRace::test_presence_lag_causes_incorrect_count PASSED
tests/simulation/test_targeted_scenarios.py::TestMeetingDeactivationEdgeCases::test_deactivation_with_no_sessions PASSED
tests/simulation/test_targeted_scenarios.py::TestMeetingDeactivationEdgeCases::test_deactivation_requires_had_sessions PASSED
tests/simulation/test_targeted_scenarios.py::TestEventLogTracing::test_event_log_captures_flow PASSED
tests/simulation/test_targeted_scenarios.py::test_config_presets PASSED

================== 25 passed, 1 xfailed ==================
```

The `xfail` test (`test_presence_race_conditions_current_system`) demonstrates that the current system configuration has race conditions that can be found through randomized testing.
