"""Tests for full-text search functionality."""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, insert

from reflector.db.base import TranscriptModel
from reflector.db.search import (
    SearchController,
    SearchParameters,
    SearchResult,
    search_controller,
)
from reflector.db.transcripts import SourceKind


@pytest.mark.asyncio
async def test_search_postgresql_only(session):
    params = SearchParameters(query_text="any query here")
    results, total = await search_controller.search_transcripts(session, params)
    assert results == []
    assert total == 0

    params_empty = SearchParameters(query_text=None)
    results_empty, total_empty = await search_controller.search_transcripts(
        session, params_empty
    )
    assert isinstance(results_empty, list)
    assert isinstance(total_empty, int)


@pytest.mark.asyncio
async def test_search_with_empty_query(session):
    """Test that empty query returns all transcripts."""
    params = SearchParameters(query_text=None)
    results, total = await search_controller.search_transcripts(session, params)

    assert isinstance(results, list)
    assert isinstance(total, int)
    if len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at


@pytest.mark.asyncio
async def test_empty_transcript_title_only_match(session):
    """Test that transcripts with title-only matches return empty snippets."""
    test_id = "test-empty-9b3f2a8d"

    try:
        await session.execute(
            delete(TranscriptModel).where(TranscriptModel.id == test_id)
        )

        test_data = {
            "id": test_id,
            "name": "Empty Transcript",
            "title": "Empty Meeting",
            "status": "ended",
            "locked": False,
            "duration": 0.0,
            "created_at": datetime.now(timezone.utc),
            "short_summary": None,
            "long_summary": None,
            "topics": json.dumps([]),
            "events": json.dumps([]),
            "participants": json.dumps([]),
            "source_language": "en",
            "target_language": "en",
            "reviewed": False,
            "audio_location": "local",
            "share_mode": "private",
            "source_kind": "room",
            "webvtt": None,
            "user_id": "test-user-1",
        }

        await session.execute(insert(TranscriptModel).values(**test_data))
        await session.commit()

        params = SearchParameters(query_text="empty", user_id="test-user-1")
        results, total = await search_controller.search_transcripts(session, params)

        assert total >= 1
        found = next((r for r in results if r.id == test_id), None)
        assert found is not None, "Should find transcript by title match"
        assert found.search_snippets == []
        assert found.total_match_count == 0

    finally:
        await session.execute(
            delete(TranscriptModel).where(TranscriptModel.id == test_id)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_search_with_long_summary(session):
    """Test that long_summary content is searchable."""
    test_id = "test-long-summary-8a9f3c2d"

    try:
        await session.execute(
            delete(TranscriptModel).where(TranscriptModel.id == test_id)
        )

        test_data = {
            "id": test_id,
            "name": "Test Long Summary",
            "title": "Regular Meeting",
            "status": "ended",
            "locked": False,
            "duration": 1800.0,
            "created_at": datetime.now(timezone.utc),
            "short_summary": "Brief overview",
            "long_summary": "Detailed discussion about quantum computing applications and blockchain technology integration",
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
Basic meeting content without special keywords.""",
            "user_id": "test-user-2",
        }

        await session.execute(insert(TranscriptModel).values(**test_data))
        await session.commit()

        params = SearchParameters(query_text="quantum computing", user_id="test-user-2")
        results, total = await search_controller.search_transcripts(session, params)

        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find transcript by long_summary content"

        test_result = next((r for r in results if r.id == test_id), None)
        assert test_result
        assert len(test_result.search_snippets) > 0
        assert "quantum computing" in test_result.search_snippets[0].lower()

    finally:
        await session.execute(
            delete(TranscriptModel).where(TranscriptModel.id == test_id)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_postgresql_search_with_data(session):
    test_id = "test-search-e2e-7f3a9b2c"

    try:
        await session.execute(
            delete(TranscriptModel).where(TranscriptModel.id == test_id)
        )

        test_data = {
            "id": test_id,
            "name": "Test Search Transcript",
            "title": "Engineering Planning Meeting Q4 2024",
            "status": "ended",
            "locked": False,
            "duration": 1800.0,
            "created_at": datetime.now(timezone.utc),
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
            "user_id": "test-user-3",
        }

        await session.execute(insert(TranscriptModel).values(**test_data))
        await session.commit()

        params = SearchParameters(query_text="planning", user_id="test-user-3")
        results, total = await search_controller.search_transcripts(session, params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by title word"

        params = SearchParameters(query_text="tsvector", user_id="test-user-3")
        results, total = await search_controller.search_transcripts(session, params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by webvtt content"

        params = SearchParameters(
            query_text="engineering planning", user_id="test-user-3"
        )
        results, total = await search_controller.search_transcripts(session, params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by multiple words"

        test_result = next((r for r in results if r.id == test_id), None)
        if test_result:
            assert test_result.title == "Engineering Planning Meeting Q4 2024"
            assert test_result.status == "ended"
            assert test_result.duration == 1800.0
            assert 0 <= test_result.rank <= 1, "Rank should be normalized to 0-1"

        params = SearchParameters(
            query_text="tsvector OR nosuchword", user_id="test-user-3"
        )
        results, total = await search_controller.search_transcripts(session, params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript with OR query"

        params = SearchParameters(
            query_text='"full-text search"', user_id="test-user-3"
        )
        results, total = await search_controller.search_transcripts(session, params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by exact phrase"

    finally:
        await session.execute(
            delete(TranscriptModel).where(TranscriptModel.id == test_id)
        )
        await session.commit()


@pytest.fixture
def sample_search_params():
    """Create sample search parameters for testing."""
    return SearchParameters(
        query_text="test query",
        limit=20,
        offset=0,
        user_id="test-user",
        room_id="room1",
    )


@pytest.fixture
def mock_db_result():
    """Create a mock database result."""
    return {
        "id": "test-transcript-id",
        "title": "Test Transcript",
        "created_at": datetime(2024, 6, 15, tzinfo=timezone.utc),
        "duration": 3600.0,
        "status": "ended",
        "user_id": "test-user",
        "room_id": "room1",
        "source_kind": SourceKind.LIVE,
        "webvtt": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nThis is a test transcript",
        "rank": 0.95,
    }


class TestSearchParameters:
    """Test SearchParameters model validation and functionality."""

    def test_search_parameters_with_available_filters(self):
        """Test creating SearchParameters with currently available filter options."""
        params = SearchParameters(
            query_text="search term",
            limit=50,
            offset=10,
            user_id="user123",
            room_id="room1",
        )

        assert params.query_text == "search term"
        assert params.limit == 50
        assert params.offset == 10
        assert params.user_id == "user123"
        assert params.room_id == "room1"

    def test_search_parameters_defaults(self):
        """Test SearchParameters with default values."""
        params = SearchParameters(query_text="test")

        assert params.query_text == "test"
        assert params.limit == 20
        assert params.offset == 0
        assert params.user_id is None
        assert params.room_id is None


class TestSearchControllerFilters:
    """Test SearchController functionality with various filters."""

    @pytest.mark.asyncio
    async def test_search_with_source_kind_filter(self, session):
        """Test search filtering by source_kind."""
        controller = SearchController()
        params = SearchParameters(query_text="test", source_kind=SourceKind.LIVE)

        # This should not fail, even if no results are found
        results, total = await controller.search_transcripts(session, params)

        assert isinstance(results, list)
        assert isinstance(total, int)
        assert total >= 0

    @pytest.mark.asyncio
    async def test_search_with_single_room_id(self, session):
        """Test search filtering by single room ID (currently supported)."""
        controller = SearchController()
        params = SearchParameters(
            query_text="test",
            room_id="room1",
        )

        # This should not fail, even if no results are found
        results, total = await controller.search_transcripts(session, params)

        assert isinstance(results, list)
        assert isinstance(total, int)
        assert total >= 0

    @pytest.mark.asyncio
    async def test_search_result_includes_available_fields(
        self, session, mock_db_result
    ):
        """Test that search results include available fields like source_kind."""
        # Test that the search method works and returns SearchResult objects
        controller = SearchController()
        params = SearchParameters(query_text="test")

        results, total = await controller.search_transcripts(session, params)

        assert isinstance(results, list)
        assert isinstance(total, int)
        assert total >= 0

        # If any results exist, verify they are SearchResult objects
        for result in results:
            assert isinstance(result, SearchResult)
            assert hasattr(result, "id")
            assert hasattr(result, "title")
            assert hasattr(result, "rank")
            assert hasattr(result, "source_kind")


class TestSearchEndpointParsing:
    """Test parameter parsing in the search endpoint."""

    def test_parse_comma_separated_room_ids(self):
        """Test parsing comma-separated room IDs."""
        room_ids_str = "room1,room2,room3"
        parsed = [rid.strip() for rid in room_ids_str.split(",") if rid.strip()]
        assert parsed == ["room1", "room2", "room3"]

        room_ids_str = "room1, room2 , room3"
        parsed = [rid.strip() for rid in room_ids_str.split(",") if rid.strip()]
        assert parsed == ["room1", "room2", "room3"]

        room_ids_str = "room1,,room3,"
        parsed = [rid.strip() for rid in room_ids_str.split(",") if rid.strip()]
        assert parsed == ["room1", "room3"]

    def test_parse_source_kind(self):
        """Test parsing source_kind values."""
        for kind_str in ["live", "file", "room"]:
            parsed = SourceKind(kind_str)
            assert parsed == SourceKind(kind_str)

        with pytest.raises(ValueError):
            SourceKind("invalid_kind")


class TestSearchResultModel:
    """Test SearchResult model and serialization."""

    def test_search_result_with_available_fields(self):
        """Test SearchResult model with currently available fields populated."""
        result = SearchResult(
            id="test-id",
            title="Test Title",
            user_id="user-123",
            room_id="room-456",
            source_kind=SourceKind.ROOM,
            created_at=datetime(2024, 6, 15, tzinfo=timezone.utc),
            status="ended",
            rank=0.85,
            duration=1800.5,
            search_snippets=["snippet 1", "snippet 2"],
        )

        assert result.id == "test-id"
        assert result.title == "Test Title"
        assert result.user_id == "user-123"
        assert result.room_id == "room-456"
        assert result.status == "ended"
        assert result.rank == 0.85
        assert result.duration == 1800.5
        assert len(result.search_snippets) == 2

    def test_search_result_with_optional_fields_none(self):
        """Test SearchResult model with optional fields as None."""
        result = SearchResult(
            id="test-id",
            source_kind=SourceKind.FILE,
            created_at=datetime.now(timezone.utc),
            status="processing",
            rank=0.5,
            search_snippets=[],
            title=None,
            user_id=None,
            room_id=None,
            duration=None,
        )

        assert result.title is None
        assert result.user_id is None
        assert result.room_id is None
        assert result.duration is None

    def test_search_result_datetime_field(self):
        """Test that SearchResult accepts datetime field."""
        result = SearchResult(
            id="test-id",
            source_kind=SourceKind.LIVE,
            created_at=datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc),
            status="ended",
            rank=0.9,
            duration=None,
            search_snippets=[],
        )

        assert result.created_at == datetime(
            2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc
        )
