# Daily.co Event-Driven Polling Architecture

## Overview

This document details the **event-driven polling architecture** for Daily.co participant presence tracking.

**Core Principle:** Participant webhooks don't write to DB, they only signal "this meeting needs polling".

**Note on Scope:** This architecture currently applies to **participant events only** (join/left). Recording webhooks queue tasks directly.

**Architecture:**
- **Single Writer:** Only polling updates DB (eliminates race conditions)
- **Event Triggers:** Webhooks + reconciliation timer set "needs poll" flags
- **Event Coalescing:** Multiple webhooks → single poll covers all changes
- **Fast Response:** Participant webhooks just set Redis flag and return immediately
- **Resilience:** Lost webhooks caught by 30s reconciliation timer

**All scenarios are illustrated with Mermaid sequence diagrams showing:**
- Event flow (webhook → flag → poll → DB)
- Event coalescing (multiple triggers → single poll)
- Reconciliation fallback mechanism
- Lock patterns for concurrent workers

## Implicit State Machine

The architecture creates an **implicit state machine** with three states:

```
States:
1. IDLE         - No flag exists (default state)
2. NEEDS_POLL   - Flag exists (webhook/reconciliation set it)
3. POLLING      - Flag claimed, poll in progress (transient, not observable in Redis)

Transitions:
IDLE → NEEDS_POLL:       Webhook or timer sets flag
NEEDS_POLL → POLLING:    Worker atomically claims flag (GETDEL)
POLLING → IDLE:          Poll completes (no explicit action needed)
```

**Design Trade-off:** Reconciliation runs unconditionally every 30s, setting flags for ALL active Daily.co meetings regardless of recent polls. This causes redundant API calls but:
- Keeps implementation simple (no timestamp tracking)
- Guarantees eventual consistency within 30s
- Redundant polls are safe (idempotent operations)
- Acceptable overhead for active meetings

## Redis Keys Architecture

### 1. Poll Request Flag
- **Key Pattern:** `meeting_poll_requested:{meeting_id}`
- **Value:** `"1"` (presence indicates poll needed)
- **TTL:** None (flag cleared by atomic GETDEL, reconciliation re-sets every 30s)
- **Purpose:** Signal that meeting needs polling
- **Set by:** Participant webhooks OR reconciliation timer (idempotent)
- **Cleared by:** Poll worker (atomic GETDEL)

### 2. Poll Execution Lock
- **Key Pattern:** `meeting_presence_poll:{meeting_id}`
- **Timeout:** 120s
- **Auto-extend:** Every 30s
- **Purpose:** Prevent concurrent polls by different workers
- **Pattern:** Distributed lock with automatic TTL extension

### 3. Recording Processing Lock
- **Key Pattern:** `recording:{recording_id}`
- **Timeout:** 600s (10 minutes)
- **Auto-extend:** Every 60s
- **Purpose:** Prevent duplicate transcription work for recording webhooks

### 4. Meeting Process Lock
- **Key Pattern:** `meeting_process_lock:{meeting_id}`
- **Timeout:** 120s
- **Auto-extend:** Every 30s
- **Purpose:** Prevent overlapping meeting processing runs

---

## Recording Processing Scenarios

**Note:** Scenarios 1-3 show recording processing (different architecture - webhooks queue tasks directly). Scenarios 4+ show the main event-driven polling architecture for participant presence.

### Scenario 1: Webhook vs Polling Race

```mermaid
sequenceDiagram
    participant Daily as Daily.co
    participant Webhook as Webhook Handler
    participant Poll as Polling Task
    participant Redis as Redis Lock
    participant Worker as Worker Process
    participant DB as Database

    Daily->>Daily: Recording completes
    Daily->>Webhook: Send webhook
    Daily->>Poll: Available via API

    par Webhook Path
        Webhook->>Worker: Queue task (Worker A)
        Worker->>Redis: Acquire lock "recording:rec-123"
        Redis-->>Worker: Lock acquired ✓
        Worker->>Worker: Process transcription
    and Polling Path
        Poll->>Poll: List recordings
        Poll->>DB: Check existing
        Poll->>Worker: Queue task (Worker B)
        Worker->>Redis: Acquire lock "recording:rec-123"
        Redis-->>Worker: Lock denied ✗
        Worker->>Worker: Skip (duplicate)
    end

    Worker->>DB: Save transcript
    Worker->>Redis: Release lock

    Note over Worker,Redis: Result: ✅ Only one transcription runs
```

### Scenario 2: Lost Webhook, Poll Backup

```mermaid
sequenceDiagram
    participant Daily as Daily.co
    participant Webhook as Webhook Handler
    participant Poll as Polling Task
    participant DB as Database
    participant Worker as Worker Process
    participant Redis as Redis Lock

    Daily->>Daily: Recording completes
    Daily--xWebhook: Webhook lost ❌
    Note over Webhook: Network failure

    Note over Poll: --- Eventually polled... ---

    Poll->>Daily: List recent recordings
    Daily-->>Poll: Returns recording list
    Poll->>DB: Check existing recordings
    DB-->>Poll: Recording not found
    Poll->>Worker: Queue missing recording
    Worker->>Redis: Acquire lock "recording:rec-123"
    Redis-->>Worker: Lock acquired ✓
    Worker->>Worker: Process transcription
    Worker->>DB: Save transcript
    Worker->>Redis: Release lock

    Note over Worker,DB: Result: ✅ Recording processed despite webhook loss
```

### Scenario 3: Duplicate Webhook Delivery

```mermaid
sequenceDiagram
    participant Daily as Daily.co
    participant Webhook as Webhook Handler
    participant Worker1 as Worker A
    participant Worker2 as Worker B
    participant Redis as Redis Lock
    participant DB as Database

    Daily->>Webhook: Send webhook
    Webhook->>Worker1: Queue task

    Daily->>Webhook: Send duplicate webhook
    Note over Webhook: Duplicate delivery
    Webhook->>Worker2: Queue same task

    Worker1->>Redis: Acquire lock "recording:rec-123"
    Redis-->>Worker1: Lock acquired ✓
    Worker1->>Worker1: Start processing

    Worker2->>Redis: Acquire lock "recording:rec-123"
    Redis-->>Worker2: Lock denied ✗
    Worker2->>Worker2: Log warning & exit

    Worker1->>Worker1: Complete transcription
    Worker1->>DB: Save transcript
    Worker1->>Redis: Release lock

    Note over Worker1,Worker2: Result: ✅ No duplicate processing
```

**Note:** This diagram shows concurrent duplicate webhooks where the lock provides protection. If a duplicate arrives after the first worker releases the lock, DB state checks prevent reprocessing (idempotent operation).

---

## Event-Driven Polling Scenarios

**Note:** Scenarios 4+ demonstrate the flag-based polling architecture described in this document (participant presence tracking).

### Scenario 4: Webhook Triggers Poll (Happy Path)

```mermaid
sequenceDiagram
    participant Daily as Daily.co
    participant Webhook as Webhook Handler
    participant Redis as Redis Flags
    participant Worker as Poll Worker
    participant API as Daily.co API
    participant DB as Database

    Note over DB: Initial: Users 1,2,3 (num_clients=3)

    Daily->>Webhook: participant.joined (User4)
    Webhook->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Webhook-->>Daily: 200 OK (fast)
    Note over Webhook: NO DB write, just flag

    Note over Worker,Redis: --- Poll Worker Processes Flag ---

    Worker->>Redis: GETDEL meeting_poll_requested:mtg-123
    Redis-->>Worker: Returns "1" (cleared)

    Worker->>Redis: Acquire lock "meeting_presence_poll:mtg-123"
    Redis-->>Worker: Lock acquired ✓

    Worker->>API: Get room presence
    API-->>Worker: Returns Users 1,2,3,4

    Worker->>DB: Get active sessions
    DB-->>Worker: Returns Users 1,2,3

    Worker->>DB: Add User4 session
    Worker->>DB: UPDATE num_clients=4

    Worker->>Redis: Release lock

    Note over DB: Result: ✅ User4 added, num_clients=4
```

**Reconciliation Logic:** Poll worker compares API presence vs DB active sessions:
- `missing = API_ids - DB_ids` → Batch upsert new sessions (joins)
- `stale = DB_ids - API_ids` → Batch close sessions (leaves)
- Mixed cases (simultaneous joins+leaves) handled in single poll

### Scenario 5: Event Coalescing (Multiple Webhooks)

```mermaid
sequenceDiagram
    participant Daily as Daily.co
    participant Webhook as Webhook Handler
    participant Redis as Redis Flags
    participant Worker as Poll Worker
    participant API as Daily.co API
    participant DB as Database

    Note over DB: Initial: User1 (num_clients=1)

    Daily->>Webhook: participant.joined (User2)
    Webhook->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Webhook-->>Daily: 200 OK

    Note over Daily,Webhook: --- Multiple events arrive ---

    Note over Daily: 500ms later...
    Daily->>Webhook: participant.joined (User3)
    Webhook->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Note over Redis: Already set, no-op
    Webhook-->>Daily: 200 OK

    Note over Daily: 800ms later...
    Daily->>Webhook: participant.joined (User4)
    Webhook->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Note over Redis: Already set, no-op
    Webhook-->>Daily: 200 OK

    Note over Worker,DB: --- Single poll handles all ---

    Worker->>Redis: GETDEL meeting_poll_requested:mtg-123
    Redis-->>Worker: Returns "1" (cleared)

    Worker->>Redis: Acquire lock
    Worker->>API: Get room presence
    API-->>Worker: Returns Users 1,2,3,4

    Worker->>DB: Add Users 2,3,4
    Worker->>DB: UPDATE num_clients=4

    Worker->>Redis: Release lock

    Note over DB: Result: ✅ 3 webhooks → 1 poll → All users synced
```

### Scenario 6: Lost Webhook Recovery (Reconciliation Timer)

```mermaid
sequenceDiagram
    participant Daily as Daily.co
    participant Webhook as Webhook Handler
    participant RecTimer as Reconciliation Timer
    participant Redis as Redis Flags
    participant Worker as Poll Worker
    participant API as Daily.co API
    participant DB as Database

    Note over DB: Initial: Users 1,2 (num_clients=2)

    Daily--xWebhook: participant.joined (User3)
    Note over Webhook: Network failure, webhook lost ❌

    Note over RecTimer: --- Next 30s cycle... ---

    RecTimer->>RecTimer: For ALL active Daily.co meetings
    RecTimer->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Note over RecTimer: Unconditional backup trigger

    Note over Worker,DB: --- Poll Worker Processes Flag ---

    Worker->>Redis: GETDEL meeting_poll_requested:mtg-123
    Redis-->>Worker: Returns "1" (cleared)

    Worker->>Redis: Acquire lock
    Worker->>API: Get room presence
    API-->>Worker: Returns Users 1,2,3

    Worker->>DB: Get sessions
    DB-->>Worker: Returns Users 1,2

    Worker->>DB: Add User3 session
    Worker->>DB: UPDATE num_clients=3

    Worker->>Redis: Release lock

    Note over DB: Result: ✅ Lost webhook recovered within 30s
```

### Scenario 7: Reconciliation Causes Redundant Poll

```mermaid
sequenceDiagram
    participant Webhook as Webhook Handler
    participant RecTimer as Reconciliation Timer
    participant Redis as Redis Flags
    participant Worker as Poll Worker
    participant API as Daily.co API
    participant DB as Database

    Note over DB: Initial state

    Webhook->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Worker->>Redis: GETDEL meeting_poll_requested:mtg-123
    Worker->>API: Poll room presence
    Worker->>DB: Update sessions
    Note over Worker: Poll complete at T0

    Note over RecTimer: --- 30s later (T0+30s) ---

    RecTimer->>RecTimer: For ALL active meetings
    RecTimer->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Note over RecTimer: No timestamp check!<br/>Unconditionally sets flags

    Worker->>Redis: GETDEL meeting_poll_requested:mtg-123
    Worker->>API: Poll room presence (again)
    Worker->>DB: Update sessions (likely no changes)

    Note over RecTimer,Redis: Result: ✅ Simple but causes redundant polls<br/>⚠️ Trade-off: Simplicity over efficiency
```

---

## Concurrent Polling Prevention

### Scenario 8: Two Workers See Same Poll Flag

```mermaid
sequenceDiagram
    participant Redis as Redis Flags
    participant WorkerA as Poll Worker A
    participant WorkerB as Poll Worker B
    participant API as Daily.co API
    participant DB as Database

    Note over Redis: Flag set by webhook:<br/>meeting_poll_requested:mtg-123 = "1"

    par Worker A Loop
        WorkerA->>Redis: GETDEL meeting_poll_requested:mtg-123
        Redis-->>WorkerA: Returns "1" (cleared atomically)
        WorkerA->>Redis: Acquire lock "meeting_presence_poll:mtg-123"
        Redis-->>WorkerA: Lock acquired ✓
        WorkerA->>API: Get room presence
        API-->>WorkerA: Return participants
        WorkerA->>DB: Reconcile sessions
        WorkerA->>Redis: Release lock
    and Worker B Loop (concurrent)
        WorkerB->>Redis: GETDEL meeting_poll_requested:mtg-123
        Redis-->>WorkerB: Returns NULL (already cleared by A)
        WorkerB->>WorkerB: No flag, skip meeting
        Note over WorkerB: Continues to next meeting
    end

    Note over WorkerA,WorkerB: Result: ✅ GETDEL atomicity prevents duplicate work
```

### Scenario 9: Two Workers Polling Different Meetings

```mermaid
sequenceDiagram
    participant Redis as Redis Flags
    participant WorkerA as Poll Worker A
    participant WorkerB as Poll Worker B
    participant API as Daily.co API
    participant DB as Database

    Note over Redis: Flags set:<br/>mtg-123 = "1"<br/>mtg-456 = "1"

    par Worker A: mtg-123
        WorkerA->>Redis: GETDEL meeting_poll_requested:mtg-123
        Redis-->>WorkerA: "1"
        WorkerA->>Redis: Acquire lock "meeting_presence_poll:mtg-123"
        WorkerA->>API: Poll mtg-123
        WorkerA->>DB: Update mtg-123 sessions
        WorkerA->>Redis: Release lock
    and Worker B: mtg-456
        WorkerB->>Redis: GETDEL meeting_poll_requested:mtg-456
        Redis-->>WorkerB: "1"
        WorkerB->>Redis: Acquire lock "meeting_presence_poll:mtg-456"
        WorkerB->>API: Poll mtg-456
        WorkerB->>DB: Update mtg-456 sessions
        WorkerB->>Redis: Release lock
    end

    Note over WorkerA,WorkerB: Result: ✅ Parallel processing of different meetings
```

---

## Meeting Processing Lock

### Scenario 10: Process Meetings Overlap

```mermaid
sequenceDiagram
    participant Cron as Cron Scheduler
    participant Worker1 as Worker #1
    participant Worker2 as Worker #2
    participant Worker3 as Worker #3
    participant Redis as Redis Lock
    participant API as Platform API

    Note over Cron: Periodic execution

    Cron->>Worker1: Start meeting processing
    Worker1->>Redis: Acquire lock "meeting_process_lock:meeting-123"
    Redis-->>Worker1: Lock acquired (120s timeout) ✓
    Worker1->>API: Get room sessions
    Worker1->>Worker1: Processing in progress...

    Note over Cron: --- Next scheduled run... ---

    Cron->>Worker2: Start meeting processing
    Worker2->>Redis: Acquire lock "meeting_process_lock:meeting-123"
    Redis-->>Worker2: Lock denied ✗
    Worker2->>Worker2: Skip meeting-123
    Note over Worker2: Continues with other meetings

    Note over Worker1: Still processing...

    Worker1->>Redis: Release lock

    Note over Cron: --- Later scheduled run... ---

    Cron->>Worker3: Start meeting processing
    Worker3->>Redis: Acquire lock "meeting_process_lock:meeting-123"
    Redis-->>Worker3: Lock acquired ✓
    Note over Worker3: Normal processing

    Note over Worker1,Worker3: Result: ✅ No overlapping processing
```

---

## Master Diagram: Event-Driven Architecture Flow

```mermaid
sequenceDiagram
    participant Daily as Daily.co
    participant Webhook as Webhook Handler
    participant RecTimer as Reconciliation Timer
    participant Redis as Redis Flags
    participant Worker as Poll Worker
    participant API as Daily.co API
    participant DB as Database

    Note over Daily,DB: EVENT-DRIVEN ARCHITECTURE: Single Writer (Poll Only)

    Note over Webhook,Daily: --- Event Triggers (Participant Events Only) ---

    Daily->>Webhook: participant.joined
    Webhook->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Webhook-->>Daily: 200 OK (fast)
    Note over Webhook: NO DB write, just flag ✅

    Daily->>Webhook: participant.left
    Webhook->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Webhook-->>Daily: 200 OK (fast)

    Note over Worker,DB: --- Single Writer (Poll Worker Loop - every 1s) ---

    Worker->>Redis: GETDEL meeting_poll_requested:mtg-123
    Redis-->>Worker: Returns "1" (cleared atomically)

    Worker->>Redis: Acquire lock "meeting_presence_poll:mtg-123"
    Redis-->>Worker: Lock acquired ✓

    Worker->>API: Get room presence
    API-->>Worker: Current participants

    Worker->>DB: Get active sessions
    DB-->>Worker: Current DB state

    Worker->>Worker: Reconcile: add missing, close stale
    Worker->>DB: Batch upsert new sessions
    Worker->>DB: Batch close left sessions
    Worker->>DB: UPDATE num_clients = COUNT(active)

    Worker->>Redis: Release lock

    Note over RecTimer,Redis: --- Backup Trigger (Every 30s) ---

    RecTimer->>RecTimer: For each active Daily.co meeting...
    RecTimer->>Redis: SET meeting_poll_requested:mtg-123 = "1"
    Note over RecTimer: Unconditional - ensures eventual consistency<br/>No timestamp tracking (simple design)

    Note over Daily,DB: Result: ✅ No race conditions (single writer)<br/>✅ Fast webhook response (just flag)<br/>✅ Event coalescing (multiple → single poll)<br/>✅ Resilient (30s reconciliation backup)
```

## Key Principles

1. **Single Writer** - Only poll worker writes to DB (eliminates all race conditions)
2. **Event Triggers** - Participant webhooks + reconciliation timer set poll flags
3. **Fast Participant Webhooks** - Just SET flag in Redis, return immediately
4. **Atomic Flag Operations** - `GETDEL` ensures exactly-once processing
5. **Event Coalescing** - Multiple webhooks → single poll covers all changes
6. **Unconditional Reconciliation** - Timer sets flags for ALL active meetings every 30s (no timestamp tracking)
7. **DB as Source of Truth** - API state reconciled into DB, `num_clients` derived from final DB state
8. **Lock for Coordination** - Prevents concurrent polls, not webhook races

## Architecture Constraints

### Current Limitations

1. **Redundant Polls:** Reconciliation triggers polls every 30s regardless of recent webhook activity
2. **No Rate Limiting:** High-traffic meetings may generate frequent API calls
3. **Participant Events Only:** Recording webhooks still queue tasks directly (not using flag pattern)

### Operational Requirements

- **Poll worker must run continuously** - 1-5s loop interval
- **Reconciliation timer must run continuously** - 30s-5m interval
- **Redis must be available** - No fallback mechanism
- **Idempotent operations required** - Polls may execute redundantly
