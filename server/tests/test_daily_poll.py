"""Tests for simplified Daily.co polling functions.

Includes both unit tests and state machine verification tests that run
an explicit state machine in parallel with our simple implementation
to ensure correct state transitions.
"""

import asyncio
from enum import Enum
from typing import Dict
from unittest.mock import AsyncMock, patch

import pytest

from reflector.utils.daily_poll import request_meeting_poll, try_claim_meeting_poll


@pytest.mark.asyncio
@patch("reflector.utils.daily_poll.get_redis_client", new_callable=AsyncMock)
async def test_request_meeting_poll_sets_flag(mock_get_redis):
    """Test that request_meeting_poll sets Redis flag."""
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    await request_meeting_poll("meeting-123")

    mock_redis.set.assert_called_once_with("meeting_poll_requested:meeting-123", "1")


@pytest.mark.asyncio
@patch("reflector.utils.daily_poll.get_redis_client", new_callable=AsyncMock)
async def test_try_claim_meeting_poll_success(mock_get_redis):
    """Test that try_claim_meeting_poll returns True when flag exists."""
    mock_redis = AsyncMock()
    mock_redis.getdel.return_value = "1"
    mock_get_redis.return_value = mock_redis

    result = await try_claim_meeting_poll("meeting-123")

    assert result is True
    mock_redis.getdel.assert_called_once_with("meeting_poll_requested:meeting-123")


@pytest.mark.asyncio
@patch("reflector.utils.daily_poll.get_redis_client", new_callable=AsyncMock)
async def test_try_claim_meeting_poll_no_flag(mock_get_redis):
    """Test that try_claim_meeting_poll returns False when no flag."""
    mock_redis = AsyncMock()
    mock_redis.getdel.return_value = None
    mock_get_redis.return_value = mock_redis

    result = await try_claim_meeting_poll("meeting-123")

    assert result is False
    mock_redis.getdel.assert_called_once_with("meeting_poll_requested:meeting-123")


@pytest.mark.asyncio
@patch("reflector.utils.daily_poll.get_redis_client", new_callable=AsyncMock)
async def test_request_poll_idempotent(mock_get_redis):
    """Test that request_meeting_poll can be called multiple times (idempotent)."""
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    await request_meeting_poll("meeting-123")
    await request_meeting_poll("meeting-123")
    await request_meeting_poll("meeting-123")

    assert mock_redis.set.call_count == 3
    # All calls set the same key-value
    for call in mock_redis.set.call_args_list:
        assert call.args == ("meeting_poll_requested:meeting-123", "1")


# ============================================================================
# State Machine Verification Tests
# ============================================================================


class ExplicitState(Enum):
    """Explicit states for verification."""

    IDLE = "idle"
    NEEDS_POLL = "needs_poll"
    POLLING = "polling"


class StateVerifier:
    """Tracks expected state transitions for verification."""

    def __init__(self):
        self.states: Dict[str, ExplicitState] = {}
        self.transitions: list[tuple[str, ExplicitState, ExplicitState]] = []

    def get_state(self, meeting_id: str) -> ExplicitState:
        return self.states.get(meeting_id, ExplicitState.IDLE)

    def transition(
        self, meeting_id: str, from_state: ExplicitState, to_state: ExplicitState
    ):
        """Record and verify state transition."""
        current = self.get_state(meeting_id)
        if current != from_state:
            raise AssertionError(
                f"Invalid transition for {meeting_id}: "
                f"expected from {from_state.value}, but was {current.value}"
            )
        self.states[meeting_id] = to_state
        self.transitions.append((meeting_id, from_state, to_state))


@pytest.mark.asyncio
@patch("reflector.utils.daily_poll.get_redis_client", new_callable=AsyncMock)
async def test_state_transitions_match_explicit_machine(mock_get_redis):
    """Verify our simple implementation follows state machine rules."""

    # Setup mock Redis
    flags = {}  # Simulate Redis storage

    async def mock_set(key, value):
        flags[key] = value
        return True

    async def mock_getdel(key):
        return flags.pop(key, None)

    mock_redis = AsyncMock()
    mock_redis.set = mock_set
    mock_redis.getdel = mock_getdel
    mock_get_redis.return_value = mock_redis

    verifier = StateVerifier()
    meeting_id = "meeting-123"

    # Initial state should be IDLE
    assert verifier.get_state(meeting_id) == ExplicitState.IDLE
    assert f"meeting_poll_requested:{meeting_id}" not in flags

    # Transition 1: IDLE → NEEDS_POLL (webhook sets flag)
    await request_meeting_poll(meeting_id)
    verifier.transition(meeting_id, ExplicitState.IDLE, ExplicitState.NEEDS_POLL)
    assert f"meeting_poll_requested:{meeting_id}" in flags

    # Verify idempotency: NEEDS_POLL → NEEDS_POLL (webhook fires again)
    await request_meeting_poll(meeting_id)
    # State doesn't change, no transition recorded
    assert verifier.get_state(meeting_id) == ExplicitState.NEEDS_POLL
    assert f"meeting_poll_requested:{meeting_id}" in flags

    # Transition 2: NEEDS_POLL → POLLING (worker claims flag)
    claimed = await try_claim_meeting_poll(meeting_id)
    assert claimed is True
    verifier.transition(meeting_id, ExplicitState.NEEDS_POLL, ExplicitState.POLLING)
    # Flag should be gone (atomic claim)
    assert f"meeting_poll_requested:{meeting_id}" not in flags

    # Concurrent claim should fail (already in POLLING state)
    claimed2 = await try_claim_meeting_poll(meeting_id)
    assert claimed2 is False
    assert verifier.get_state(meeting_id) == ExplicitState.POLLING

    # Transition 3: POLLING → IDLE (poll completes - implicit in our implementation)
    # In real implementation, this happens when poll_daily_room_presence() finishes
    verifier.transition(meeting_id, ExplicitState.POLLING, ExplicitState.IDLE)

    # Verify complete cycle
    assert verifier.transitions == [
        (meeting_id, ExplicitState.IDLE, ExplicitState.NEEDS_POLL),
        (meeting_id, ExplicitState.NEEDS_POLL, ExplicitState.POLLING),
        (meeting_id, ExplicitState.POLLING, ExplicitState.IDLE),
    ]


@pytest.mark.asyncio
@patch("reflector.utils.daily_poll.get_redis_client", new_callable=AsyncMock)
async def test_concurrent_workers_respect_state_machine(mock_get_redis):
    """Test that concurrent workers maintain state machine invariants."""

    flags = {}
    claims = []

    async def mock_set(key, value):
        flags[key] = value
        return True

    async def mock_getdel(key):
        # Simulate atomic GETDEL - only one worker can claim
        value = flags.pop(key, None)
        if value:
            claims.append(asyncio.current_task())
        return value

    mock_redis = AsyncMock()
    mock_redis.set = mock_set
    mock_redis.getdel = mock_getdel
    mock_get_redis.return_value = mock_redis

    meeting_id = "meeting-456"

    # Set flag (IDLE → NEEDS_POLL)
    await request_meeting_poll(meeting_id)

    # Simulate 10 concurrent workers trying to claim
    async def worker(worker_id: int):
        claimed = await try_claim_meeting_poll(meeting_id)
        return (worker_id, claimed)

    results = await asyncio.gather(*[worker(i) for i in range(10)])

    # Exactly one worker should succeed (NEEDS_POLL → POLLING)
    successful_workers = [w for w, claimed in results if claimed]
    assert len(successful_workers) == 1

    # All others should see IDLE state (flag already claimed)
    failed_workers = [w for w, claimed in results if not claimed]
    assert len(failed_workers) == 9

    # Only one atomic claim should have succeeded
    assert len(claims) == 1


@pytest.mark.asyncio
@patch("reflector.utils.daily_poll.get_redis_client", new_callable=AsyncMock)
async def test_reconciliation_resets_to_needs_poll(mock_get_redis):
    """Test that reconciliation can always set NEEDS_POLL regardless of current state."""

    flags = {}

    async def mock_set(key, value):
        flags[key] = value
        return True

    async def mock_getdel(key):
        return flags.pop(key, None)

    mock_redis = AsyncMock()
    mock_redis.set = mock_set
    mock_redis.getdel = mock_getdel
    mock_get_redis.return_value = mock_redis

    verifier = StateVerifier()
    meeting_id = "meeting-789"

    # Test from IDLE state
    assert verifier.get_state(meeting_id) == ExplicitState.IDLE
    await request_meeting_poll(meeting_id)  # Reconciliation sets flag
    verifier.transition(meeting_id, ExplicitState.IDLE, ExplicitState.NEEDS_POLL)
    assert f"meeting_poll_requested:{meeting_id}" in flags

    # Test idempotency from NEEDS_POLL state
    await request_meeting_poll(meeting_id)  # Reconciliation runs again
    # No state change, still NEEDS_POLL
    assert verifier.get_state(meeting_id) == ExplicitState.NEEDS_POLL
    assert f"meeting_poll_requested:{meeting_id}" in flags

    # Claim the flag (NEEDS_POLL → POLLING)
    claimed = await try_claim_meeting_poll(meeting_id)
    assert claimed is True
    verifier.transition(meeting_id, ExplicitState.NEEDS_POLL, ExplicitState.POLLING)

    # Even while POLLING, reconciliation can set flag again
    # (This is safe because GETDEL already removed the old flag)
    await request_meeting_poll(meeting_id)
    # In our model, this effectively queues another poll after current one finishes
    assert f"meeting_poll_requested:{meeting_id}" in flags

    # After current poll finishes (POLLING → IDLE), the new flag is ready
    verifier.transition(meeting_id, ExplicitState.POLLING, ExplicitState.IDLE)

    # Now the flag from reconciliation can be claimed
    verifier.transition(meeting_id, ExplicitState.IDLE, ExplicitState.NEEDS_POLL)
    claimed = await try_claim_meeting_poll(meeting_id)
    assert claimed is True


def test_state_machine_properties():
    """Test formal properties of our implicit state machine.

    Note: These are documentation tests showing what transitions are invalid.
    The actual enforcement happens via our implementation's design.
    """

    # Property 1: Can't skip NEEDS_POLL state
    # In our implementation, you can't go directly from nothing to polling
    # because try_claim_meeting_poll() only succeeds if flag exists
    verifier = StateVerifier()
    assert verifier.get_state("m1") == ExplicitState.IDLE

    # Property 2: Once in POLLING, flag is gone
    # In our implementation, once try_claim_meeting_poll() returns true,
    # the flag is atomically removed, so no other worker can claim it
    verifier.states["m2"] = ExplicitState.POLLING
    # This represents that the flag was claimed and removed

    # Property 3: NEEDS_POLL is idempotent
    # request_meeting_poll() can be called multiple times safely
    verifier.states["m3"] = ExplicitState.NEEDS_POLL
    # Multiple calls to request_meeting_poll() just set the same flag

    # Property 4: Atomic transitions prevent races
    # GETDEL ensures exactly one worker transitions from NEEDS_POLL to POLLING
    # (Tested in test_concurrent_workers_respect_state_machine)
