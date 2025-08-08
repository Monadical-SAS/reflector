"""Tests for full-text search functionality."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from reflector.db import database
from reflector.db.search import SearchParameters, search_controller
from reflector.db.transcripts import transcripts
from reflector.db.utils import is_postgresql


@pytest.mark.asyncio
async def test_search_postgresql_only():
    await database.connect()

    try:
        params = SearchParameters(query_text="any query here")
        results, total = await search_controller.search_transcripts(params)
        assert results == []
        assert total == 0

        # Test that empty query raises validation error
        try:
            SearchParameters(query_text="")
            assert False, "Should have raised validation error"
        except ValidationError:
            pass  # Expected

        # Test that whitespace query raises validation error
        try:
            SearchParameters(query_text="   ")
            assert False, "Should have raised validation error"
        except ValidationError:
            pass  # Expected

    finally:
        await database.disconnect()


@pytest.mark.asyncio
async def test_search_input_validation():
    await database.connect()

    try:
        # Test that empty query raises validation error
        try:
            SearchParameters(query_text="")
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass  # Expected

        # Test that whitespace query raises validation error
        try:
            SearchParameters(query_text="   \t\n  ")
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass  # Expected
    finally:
        await database.disconnect()


@pytest.mark.asyncio
async def test_postgresql_search_with_data():
    """Test full-text search with actual data in PostgreSQL.

    Run with: DATABASE_URL=postgresql://reflector:reflector@localhost:5432/reflector_test uv run pytest tests/test_search.py::test_postgresql_search_with_data -v -p no:env
    """
    # Skip if not PostgreSQL
    if not is_postgresql():
        pytest.skip("Test requires PostgreSQL. Set DATABASE_URL=postgresql://...")

    await database.connect()

    # Use a unique test ID to avoid collisions
    test_id = "test-search-e2e-7f3a9b2c"

    try:
        # Clean up any existing test transcript
        await database.execute(transcripts.delete().where(transcripts.c.id == test_id))

        # Create test transcript with searchable content
        test_data = {
            "id": test_id,
            "name": "Test Search Transcript",
            "title": "Engineering Planning Meeting Q4 2024",
            "status": "completed",
            "locked": False,
            "duration": 1800.0,
            "created_at": datetime.now(),
            "short_summary": "Team discussed search implementation",
            "long_summary": "The engineering team met to plan the search feature",
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
Welcome to our engineering planning meeting for Q4 2024.

00:00:10.000 --> 00:00:20.000
Today we'll discuss the implementation of full-text search.

00:00:20.000 --> 00:00:30.000
The search feature should support complex queries with ranking.

00:00:30.000 --> 00:00:40.000
We need to implement PostgreSQL tsvector for better performance.""",
        }

        # Insert test transcript
        await database.execute(transcripts.insert().values(**test_data))

        # Test 1: Search for a word in title
        params = SearchParameters(query_text="planning")
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by title word"

        # Test 2: Search for a word in webvtt content
        params = SearchParameters(query_text="tsvector")
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by webvtt content"

        # Test 3: Search with multiple words
        params = SearchParameters(query_text="engineering planning")
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by multiple words"

        # Test 4: Verify SearchResult structure
        test_result = next((r for r in results if r.id == test_id), None)
        if test_result:
            assert test_result.title == "Engineering Planning Meeting Q4 2024"
            assert test_result.status == "completed"
            assert test_result.duration == 1800.0
            assert test_result.source_kind == "room"
            assert 0 <= test_result.rank <= 1, "Rank should be normalized to 0-1"

        # Test 5: Search with OR operator
        params = SearchParameters(query_text="tsvector OR nosuchword")
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript with OR query"

        # Test 6: Quoted phrase search
        params = SearchParameters(query_text='"full-text search"')
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by exact phrase"

    finally:
        # Clean up test data
        await database.execute(transcripts.delete().where(transcripts.c.id == test_id))
        await database.disconnect()
