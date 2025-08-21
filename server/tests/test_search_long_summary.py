"""Tests for long_summary in search functionality."""

import json
import uuid
from datetime import datetime, timezone

import pytest

from reflector.db import get_database
from reflector.db.search import SearchParameters, search_controller
from reflector.db.transcripts import transcripts


@pytest.mark.asyncio
async def test_long_summary_snippet_prioritization():
    """Test that snippets from long_summary are prioritized over webvtt content."""
    test_id = f"test-snippet-priority-{uuid.uuid4()}"
    test_user = f"test-user-priority-{uuid.uuid4()}"

    try:
        test_data = {
            "id": test_id,
            "name": "Test Snippet Priority",
            "title": "Meeting About Projects",
            "status": "completed",
            "locked": False,
            "duration": 1800.0,
            "created_at": datetime.now(timezone.utc),
            "short_summary": "Project discussion",
            "long_summary": (
                "The team discussed advanced robotics applications including "
                "autonomous navigation systems and sensor fusion techniques. "
                "Robotics development will focus on real-time processing."
            ),
            "topics": json.dumps([]),
            "events": json.dumps([]),
            "participants": json.dumps([]),
            "source_language": "en",
            "target_language": "en",
            "reviewed": False,
            "audio_location": "local",
            "share_mode": "private",
            "source_kind": "room",
            "webvtt": """WEBVTT

00:00:00.000 --> 00:00:10.000
We talked about many different topics today.

00:00:10.000 --> 00:00:20.000
The robotics project is making good progress.

00:00:20.000 --> 00:00:30.000
We need to consider various implementation approaches.""",
            "user_id": test_user,
        }

        await get_database().execute(transcripts.insert().values(**test_data))

        params = SearchParameters(query_text="robotics", user_id=test_user)
        results, total = await search_controller.search_transcripts(params)

        assert total >= 1
        test_result = next((r for r in results if r.id == test_id), None)
        assert test_result, "Should find the test transcript"

        snippets = test_result.search_snippets
        assert len(snippets) > 0, "Should have at least one snippet"

        first_snippet = snippets[0].lower()
        assert (
            "advanced robotics" in first_snippet or "autonomous" in first_snippet
        ), f"First snippet should be from long_summary with detailed content. Got: {snippets[0]}"

        assert len(snippets) <= 3, "Should respect max snippets limit"

        for snippet in snippets:
            assert (
                "robotics" in snippet.lower()
            ), f"Snippet should contain search term: {snippet}"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )


@pytest.mark.asyncio
async def test_long_summary_only_search():
    """Test searching for content that only exists in long_summary."""
    test_id = f"test-long-only-{uuid.uuid4()}"
    test_user = f"test-user-longonly-{uuid.uuid4()}"

    try:
        test_data = {
            "id": test_id,
            "name": "Test Long Only",
            "title": "Standard Meeting",
            "status": "completed",
            "locked": False,
            "duration": 1800.0,
            "created_at": datetime.now(timezone.utc),
            "short_summary": "Team sync",
            "long_summary": (
                "Detailed analysis of cryptocurrency market trends and "
                "decentralized finance protocols. Discussion included "
                "yield farming strategies and liquidity pool mechanics."
            ),
            "topics": json.dumps([]),
            "events": json.dumps([]),
            "participants": json.dumps([]),
            "source_language": "en",
            "target_language": "en",
            "reviewed": False,
            "audio_location": "local",
            "share_mode": "private",
            "source_kind": "room",
            "webvtt": """WEBVTT

00:00:00.000 --> 00:00:10.000
Team meeting about general project updates.

00:00:10.000 --> 00:00:20.000
Discussion of timeline and deliverables.""",
            "user_id": test_user,
        }

        await get_database().execute(transcripts.insert().values(**test_data))

        params = SearchParameters(query_text="cryptocurrency", user_id=test_user)
        results, total = await search_controller.search_transcripts(params)

        found = any(r.id == test_id for r in results)
        assert found, "Should find transcript by long_summary-only content"

        test_result = next((r for r in results if r.id == test_id), None)
        assert test_result
        assert len(test_result.search_snippets) > 0

        snippet = test_result.search_snippets[0].lower()
        assert "cryptocurrency" in snippet, "Snippet should contain the search term"

        params2 = SearchParameters(query_text="yield farming", user_id=test_user)
        results2, total2 = await search_controller.search_transcripts(params2)

        found2 = any(r.id == test_id for r in results2)
        assert found2, "Should find transcript by specific long_summary phrase"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )
