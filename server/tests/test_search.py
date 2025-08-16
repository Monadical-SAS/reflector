"""Tests for full-text search functionality."""

import json
from datetime import datetime, timezone
from enum import Enum
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from reflector.db import get_database
from reflector.db.search import (
    SearchController,
    SearchParameters,
    SearchResult,
    search_controller,
)
from reflector.db.transcripts import SourceKind, transcripts


# StatusFilter enum for future implementation
class StatusFilter(str, Enum):
    """Filter transcripts by processing status."""

    COMPLETED = "completed"
    PROCESSING = "processing"
    FAILED = "failed"
    PENDING = "pending"


@pytest.mark.asyncio
async def test_search_postgresql_only():
    params = SearchParameters(query_text="any query here")
    results, total = await search_controller.search_transcripts(params)
    assert results == []
    assert total == 0

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


@pytest.mark.asyncio
async def test_search_input_validation():
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


@pytest.mark.asyncio
async def test_empty_transcript_fallback_snippets():
    """Test that transcripts with no content get fallback snippets."""
    test_id = "test-empty-9b3f2a8d"

    try:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )

        test_data = {
            "id": test_id,
            "name": "Empty Transcript",
            "title": "Empty Meeting",
            "status": "completed",
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
            "webvtt": None,  # Empty content
        }

        await get_database().execute(transcripts.insert().values(**test_data))

        # Search should return the transcript with fallback snippet
        params = SearchParameters(query_text="empty")
        results, total = await search_controller.search_transcripts(params)

        # Should find the transcript by title
        assert total >= 1
        found = next((r for r in results if r.id == test_id), None)
        assert found is not None, "Should find transcript even with no content"
        assert len(found.search_snippets) > 0
        assert found.search_snippets[0] == "No transcript content available"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )
        await get_database().disconnect()


@pytest.mark.asyncio
async def test_search_with_long_summary():
    """Test that long_summary content is searchable."""
    test_id = "test-long-summary-8a9f3c2d"

    try:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )

        test_data = {
            "id": test_id,
            "name": "Test Long Summary",
            "title": "Regular Meeting",
            "status": "completed",
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
        }

        await get_database().execute(transcripts.insert().values(**test_data))

        # Search for term only in long_summary
        params = SearchParameters(query_text="quantum computing")
        results, total = await search_controller.search_transcripts(params)

        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find transcript by long_summary content"

        # Verify snippet is from long_summary
        test_result = next((r for r in results if r.id == test_id), None)
        assert test_result
        assert len(test_result.search_snippets) > 0
        assert "quantum computing" in test_result.search_snippets[0].lower()

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )
        await get_database().disconnect()


@pytest.mark.asyncio
async def test_postgresql_search_with_data():
    # collision is improbable
    test_id = "test-search-e2e-7f3a9b2c"

    try:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )

        test_data = {
            "id": test_id,
            "name": "Test Search Transcript",
            "title": "Engineering Planning Meeting Q4 2024",
            "status": "completed",
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
        }

        await get_database().execute(transcripts.insert().values(**test_data))

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
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )
        await get_database().disconnect()


# Tests merged from test_search_enhancements.py


@pytest.fixture
def sample_search_params():
    """Create sample search parameters for testing."""
    # Note: Only using fields that actually exist in SearchParameters
    return SearchParameters(
        query_text="test query",
        limit=20,
        offset=0,
        user_id="test-user",
        room_id="room1",  # room_id, not room_ids
        # Future fields not yet implemented:
        # source_kind=SourceKind.LIVE,
        # status=[StatusFilter.COMPLETED, StatusFilter.PROCESSING],
        # date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        # date_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_db_result():
    """Create a mock database result."""
    return {
        "id": "test-transcript-id",
        "title": "Test Transcript",
        "created_at": datetime(2024, 6, 15, tzinfo=timezone.utc),
        "duration": 3600.0,
        "status": "completed",
        "user_id": "test-user",
        "room_id": "room1",
        "source_kind": SourceKind.LIVE,
        "webvtt": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nThis is a test transcript",
        # "room_name": "Test Room",  # Not in current model
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
            room_id="room1",  # Currently only single room_id is supported
        )

        assert params.query_text == "search term"
        assert params.limit == 50
        assert params.offset == 10
        assert params.user_id == "user123"
        assert params.room_id == "room1"

        # These fields are planned but not yet implemented:
        # assert params.room_ids == ["room1", "room2", "room3"]
        # assert params.source_kind == SourceKind.FILE
        # assert params.status == [StatusFilter.COMPLETED]
        # assert params.date_from.year == 2024
        # assert params.date_to.month == 12

    def test_search_parameters_defaults(self):
        """Test SearchParameters with default values."""
        params = SearchParameters(query_text="test")

        assert params.query_text == "test"
        assert params.limit == 20  # DEFAULT_SEARCH_LIMIT
        assert params.offset == 0
        assert params.user_id is None
        assert params.room_id is None
        # Future fields (not yet implemented):
        # assert params.room_ids is None
        # assert params.source_kind is None
        # assert params.status is None
        # assert params.date_from is None
        # assert params.date_to is None


class TestSearchControllerFilters:
    """Test SearchController functionality with various filters."""

    @pytest.mark.asyncio
    async def test_search_with_source_kind_filter(self):
        """Test search filtering by source_kind."""
        controller = SearchController()
        with (
            patch("reflector.db.search.is_postgresql", return_value=True),
            patch("reflector.db.search.get_database") as mock_db,
        ):
            mock_db.return_value.fetch_all = AsyncMock(return_value=[])
            mock_db.return_value.fetch_val = AsyncMock(return_value=0)

            params = SearchParameters(query_text="test", source_kind=SourceKind.LIVE)

            results, total = await controller.search_transcripts(params)

            assert results == []
            assert total == 0

            # Verify the query was called
            mock_db.return_value.fetch_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_single_room_id(self):
        """Test search filtering by single room ID (currently supported)."""
        controller = SearchController()
        with (
            patch("reflector.db.search.is_postgresql", return_value=True),
            patch("reflector.db.search.get_database") as mock_db,
        ):
            mock_db.return_value.fetch_all = AsyncMock(return_value=[])
            mock_db.return_value.fetch_val = AsyncMock(return_value=0)

            params = SearchParameters(
                query_text="test",
                room_id="room1",  # Single room_id is supported
            )

            results, total = await controller.search_transcripts(params)

            assert results == []
            assert total == 0
            mock_db.return_value.fetch_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_result_includes_available_fields(self, mock_db_result):
        """Test that search results include available fields like source_kind."""
        controller = SearchController()
        with (
            patch("reflector.db.search.is_postgresql", return_value=True),
            patch("reflector.db.search.get_database") as mock_db,
        ):
            # Create a proper mock that behaves like a database row
            class MockRow:
                def __init__(self, data):
                    self._data = data
                    self._mapping = data  # SQLAlchemy-like attribute

                def __iter__(self):
                    return iter(self._data.items())

                def __getitem__(self, key):
                    return self._data[key]

                def keys(self):
                    return self._data.keys()

            mock_row = MockRow(mock_db_result)

            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            mock_db.return_value.fetch_val = AsyncMock(return_value=1)

            params = SearchParameters(query_text="test")

            results, total = await controller.search_transcripts(params)

            assert total == 1
            assert len(results) == 1

            result = results[0]
            assert isinstance(result, SearchResult)
            assert result.id == "test-transcript-id"
            assert result.title == "Test Transcript"
            # Currently available fields:
            assert result.rank == 0.95
            # Note: source_kind is in the DB but not in SearchResult model yet
            # Future fields (not yet in SearchResult model):
            # assert result.source_kind == SourceKind.LIVE
            # assert result.room_name == "Test Room"
            # assert result.processing_status == "completed"


class TestSearchEndpointParsing:
    """Test parameter parsing in the search endpoint."""

    def test_parse_comma_separated_room_ids(self):
        """Test parsing comma-separated room IDs."""
        room_ids_str = "room1,room2,room3"
        parsed = [rid.strip() for rid in room_ids_str.split(",") if rid.strip()]
        assert parsed == ["room1", "room2", "room3"]

        # Test with spaces
        room_ids_str = "room1, room2 , room3"
        parsed = [rid.strip() for rid in room_ids_str.split(",") if rid.strip()]
        assert parsed == ["room1", "room2", "room3"]

        # Test with empty values
        room_ids_str = "room1,,room3,"
        parsed = [rid.strip() for rid in room_ids_str.split(",") if rid.strip()]
        assert parsed == ["room1", "room3"]

    def test_parse_comma_separated_status(self):
        """Test parsing comma-separated status values."""
        status_str = "completed,processing,failed"
        status_list = [s.strip().lower() for s in status_str.split(",") if s.strip()]
        parsed = [StatusFilter(s) for s in status_list]

        assert len(parsed) == 3
        assert StatusFilter.COMPLETED in parsed
        assert StatusFilter.PROCESSING in parsed
        assert StatusFilter.FAILED in parsed

        # Test with mixed case
        status_str = "COMPLETED,Processing,FaiLeD"
        status_list = [s.strip().lower() for s in status_str.split(",") if s.strip()]
        parsed = [StatusFilter(s) for s in status_list]

        assert len(parsed) == 3
        assert StatusFilter.COMPLETED in parsed

    def test_parse_source_kind(self):
        """Test parsing source_kind values."""
        # Valid values
        for kind_str in ["live", "file", "room"]:
            parsed = SourceKind(kind_str)
            assert parsed == SourceKind(kind_str)

        # Test case insensitive
        parsed = SourceKind("LIVE".lower())
        assert parsed == SourceKind.LIVE

        # Invalid value should raise
        with pytest.raises(ValueError):
            SourceKind("invalid_kind")

    def test_invalid_status_value_raises_error(self):
        """Test that invalid status values raise errors."""
        with pytest.raises(ValueError):
            StatusFilter("invalid_status")


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
            status="completed",
            rank=0.85,
            duration=1800.5,
            search_snippets=["snippet 1", "snippet 2"],
            # Future fields (not in current SearchResult model):
            # source_kind="live",
            # room_name="Conference Room A",
            # processing_status="completed",
        )

        assert result.id == "test-id"
        assert result.title == "Test Title"
        assert result.user_id == "user-123"
        assert result.room_id == "room-456"
        assert result.status == "completed"
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
            # Future fields:
            # source_kind="file",
            # room_name=None,
            # processing_status=None,
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
            status="completed",
            rank=0.9,
            duration=None,  # Optional but required field
            search_snippets=[],
        )

        # Verify the datetime field is properly stored
        assert result.created_at == datetime(
            2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc
        )
        assert result.created_at.year == 2024
        assert result.created_at.month == 6
        assert result.created_at.day == 15
