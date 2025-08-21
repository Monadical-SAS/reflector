"""Tests for full-text search functionality."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.db import get_database
from reflector.db.rooms import rooms
from reflector.db.search import (
    SearchController,
    SearchParameters,
    SearchResult,
    search_controller,
)
from reflector.db.transcripts import SourceKind, transcripts


def create_test_room_data(room_id: str, name: str, user_id: str, is_shared: bool):
    """Helper to create consistent room test data."""
    return {
        "id": room_id,
        "name": name,
        "user_id": user_id,
        "is_shared": is_shared,
        "created_at": datetime.now(timezone.utc),
    }


def create_test_transcript_data(
    transcript_id: str,
    name: str,
    title: str,
    user_id: str = None,
    room_id: str = None,
    webvtt: str = "WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nTest content",
):
    """Helper to create consistent transcript test data."""
    return {
        "id": transcript_id,
        "name": name,
        "title": title,
        "status": "completed",
        "room_id": room_id,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "duration": 1800.0,
        "source_kind": "room" if room_id else "file",
        "topics": json.dumps([]),
        "events": json.dumps([]),
        "participants": json.dumps([]),
        "webvtt": webvtt,
    }


@pytest.mark.asyncio
async def test_search_postgresql_only():
    params = SearchParameters(query_text="any query here")
    results, total = await search_controller.search_transcripts(params)
    assert results == []
    assert total == 0

    params_empty = SearchParameters(query_text="")
    results_empty, total_empty = await search_controller.search_transcripts(
        params_empty
    )
    assert isinstance(results_empty, list)
    assert isinstance(total_empty, int)


@pytest.mark.asyncio
async def test_search_with_empty_query():
    """Test that empty query returns all transcripts."""
    params = SearchParameters(query_text="")
    results, total = await search_controller.search_transcripts(params)

    assert isinstance(results, list)
    assert isinstance(total, int)
    if len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at


@pytest.mark.asyncio
async def test_empty_transcript_title_only_match():
    """Test that transcripts with title-only matches return empty snippets."""
    test_id = f"test-empty-{uuid.uuid4()}"
    test_user = f"test-user-empty-{uuid.uuid4()}"

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
            "webvtt": None,
            "user_id": test_user,
        }

        await get_database().execute(transcripts.insert().values(**test_data))

        params = SearchParameters(query_text="empty", user_id=test_user)
        results, total = await search_controller.search_transcripts(params)

        assert total >= 1
        found = next((r for r in results if r.id == test_id), None)
        assert found is not None, "Should find transcript by title match"
        assert found.search_snippets == []
        assert found.total_match_count == 0

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )


@pytest.mark.asyncio
async def test_search_with_long_summary():
    """Test that long_summary content is searchable."""
    test_id = f"test-long-summary-{uuid.uuid4()}"
    test_user = f"test-user-summary-{uuid.uuid4()}"

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
            "user_id": test_user,
        }

        await get_database().execute(transcripts.insert().values(**test_data))

        params = SearchParameters(query_text="quantum computing", user_id=test_user)
        results, total = await search_controller.search_transcripts(params)

        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find transcript by long_summary content"

        test_result = next((r for r in results if r.id == test_id), None)
        assert test_result
        assert len(test_result.search_snippets) > 0
        assert "quantum computing" in test_result.search_snippets[0].lower()

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )


@pytest.mark.asyncio
async def test_postgresql_search_with_data():
    test_id = f"test-search-e2e-{uuid.uuid4()}"
    test_user = f"test-user-pg-{uuid.uuid4()}"

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
            "user_id": test_user,
        }

        await get_database().execute(transcripts.insert().values(**test_data))

        params = SearchParameters(query_text="planning", user_id=test_user)
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by title word"

        params = SearchParameters(query_text="tsvector", user_id=test_user)
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by webvtt content"

        params = SearchParameters(query_text="engineering planning", user_id=test_user)
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by multiple words"

        test_result = next((r for r in results if r.id == test_id), None)
        if test_result:
            assert test_result.title == "Engineering Planning Meeting Q4 2024"
            assert test_result.status == "completed"
            assert test_result.duration == 1800.0
            assert 0 <= test_result.rank <= 1, "Rank should be normalized to 0-1"

        params = SearchParameters(
            query_text="tsvector OR nosuchword", user_id=test_user
        )
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript with OR query"

        params = SearchParameters(query_text='"full-text search"', user_id=test_user)
        results, total = await search_controller.search_transcripts(params)
        assert total >= 1
        found = any(r.id == test_id for r in results)
        assert found, "Should find test transcript by exact phrase"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_id)
        )


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
        "status": "completed",
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
                room_id="room1",
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

            class MockRow:
                def __init__(self, data):
                    self._data = data
                    self._mapping = data

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
            assert result.rank == 0.95


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
            status="completed",
            rank=0.85,
            duration=1800.5,
            search_snippets=["snippet 1", "snippet 2"],
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
            duration=None,
            search_snippets=[],
        )

        assert result.created_at == datetime(
            2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc
        )


@pytest.mark.asyncio
async def test_search_shared_room_visible_to_anonymous():
    """Test that transcripts in shared rooms are searchable without user_id."""
    test_room_id = f"shared-room-test-{uuid.uuid4()}"
    test_transcript_id = f"shared-transcript-{uuid.uuid4()}"
    owner_user = "room-owner"

    try:
        room_data = create_test_room_data(
            test_room_id, "Shared Test Room", owner_user, is_shared=True
        )
        await get_database().execute(rooms.insert().values(**room_data))

        transcript_data = create_test_transcript_data(
            test_transcript_id,
            "Shared Room Transcript",
            "Public Meeting",
            user_id=owner_user,
            room_id=test_room_id,
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nShared content",
        )
        await get_database().execute(transcripts.insert().values(**transcript_data))

        params = SearchParameters(query_text="public")
        results, total = await search_controller.search_transcripts(params)

        matching_results = [r for r in results if r.id == test_transcript_id]
        assert (
            len(matching_results) == 1
        ), f"Expected exactly 1 result, got {len(matching_results)}"
        assert total >= 1, f"Total count should be at least 1, got {total}"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_transcript_id)
        )
        await get_database().execute(rooms.delete().where(rooms.c.id == test_room_id))


@pytest.mark.asyncio
async def test_search_private_room_requires_user_match():
    """Test that transcripts in private rooms require matching user_id."""
    test_room_id = f"private-room-test-{uuid.uuid4()}"
    test_transcript_id = f"private-transcript-{uuid.uuid4()}"
    owner_user = "user1"
    other_user = "user2"

    try:
        room_data = create_test_room_data(
            test_room_id, "Private Test Room", owner_user, is_shared=False
        )
        await get_database().execute(rooms.insert().values(**room_data))

        transcript_data = create_test_transcript_data(
            test_transcript_id,
            "Private Room Transcript",
            "Confidential Meeting",
            user_id=owner_user,
            room_id=test_room_id,
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nConfidential content",
        )
        transcript_data["duration"] = 900.0
        await get_database().execute(transcripts.insert().values(**transcript_data))

        params_other = SearchParameters(query_text="confidential", user_id=other_user)
        results, total = await search_controller.search_transcripts(params_other)
        found = any(r.id == test_transcript_id for r in results)
        assert (
            not found
        ), "Should NOT find private room transcript with different user_id"

        params_owner = SearchParameters(query_text="confidential", user_id=owner_user)
        results, total = await search_controller.search_transcripts(params_owner)
        found = any(r.id == test_transcript_id for r in results)
        assert found, "Should find private room transcript with matching user_id"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_transcript_id)
        )
        await get_database().execute(rooms.delete().where(rooms.c.id == test_room_id))


@pytest.mark.asyncio
async def test_search_no_room_requires_user_id():
    """Test that transcripts without rooms are only visible to their owner."""
    test_transcript_id = f"no-room-transcript-{uuid.uuid4()}"
    owner_user = "file-uploader"
    other_user = "another-user"

    try:
        transcript_data = create_test_transcript_data(
            test_transcript_id,
            "Uploaded File",
            "Direct Upload",
            user_id=owner_user,
            room_id=None,
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nUploaded content",
        )
        transcript_data["duration"] = 600.0
        await get_database().execute(transcripts.insert().values(**transcript_data))

        params_anon = SearchParameters(query_text="upload")
        results, total = await search_controller.search_transcripts(params_anon)
        found = any(r.id == test_transcript_id for r in results)
        assert not found, "Should NOT find room-less transcript without user_id"

        params_other = SearchParameters(query_text="upload", user_id=other_user)
        results, total = await search_controller.search_transcripts(params_other)
        found = any(r.id == test_transcript_id for r in results)
        assert not found, "Should NOT find room-less transcript with different user_id"

        params_owner = SearchParameters(query_text="upload", user_id=owner_user)
        results, total = await search_controller.search_transcripts(params_owner)
        found = any(r.id == test_transcript_id for r in results)
        assert found, "Should find room-less transcript with matching user_id"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_transcript_id)
        )


@pytest.mark.asyncio
async def test_search_returns_mixed_visibility():
    """Test that search correctly returns both owned and shared transcripts."""
    test_private_id = f"mixed-private-{uuid.uuid4()}"
    test_shared_id = f"mixed-shared-{uuid.uuid4()}"
    test_private_room = f"mixed-private-room-{uuid.uuid4()}"
    test_shared_room = f"mixed-shared-room-{uuid.uuid4()}"
    user1 = "mixed-user-1"
    user2 = "mixed-user-2"

    try:
        private_room_data = create_test_room_data(
            test_private_room, "User1 Private Room", user1, is_shared=False
        )
        await get_database().execute(rooms.insert().values(**private_room_data))

        shared_room_data = create_test_room_data(
            test_shared_room, "User2 Shared Room", user2, is_shared=True
        )
        await get_database().execute(rooms.insert().values(**shared_room_data))

        private_transcript_data = create_test_transcript_data(
            test_private_id,
            "User1 Private Transcript",
            "Strategy Discussion",
            user_id=user1,
            room_id=test_private_room,
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nStrategy planning",
        )
        private_transcript_data["duration"] = 1200.0
        await get_database().execute(
            transcripts.insert().values(**private_transcript_data)
        )

        shared_transcript_data = create_test_transcript_data(
            test_shared_id,
            "User2 Shared Transcript",
            "Strategy Workshop",
            user_id=user2,
            room_id=test_shared_room,
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nStrategy workshop",
        )
        await get_database().execute(
            transcripts.insert().values(**shared_transcript_data)
        )

        params = SearchParameters(query_text="strategy", user_id=user1)
        results, total = await search_controller.search_transcripts(params)
        result_ids = {r.id for r in results}

        assert (
            test_private_id in result_ids
        ), "Should find user's own private transcript"
        assert test_shared_id in result_ids, "Should find shared room transcript"
        assert (
            len(result_ids) >= 2
        ), f"Should find at least 2 transcripts, got {len(result_ids)}"
        assert total >= 2, f"Total count should be at least 2, got {total}"

    finally:
        await get_database().execute(
            transcripts.delete().where(
                transcripts.c.id.in_([test_private_id, test_shared_id])
            )
        )
        await get_database().execute(
            rooms.delete().where(rooms.c.id.in_([test_private_room, test_shared_room]))
        )


@pytest.mark.asyncio
async def test_search_shared_room_cross_user_visibility():
    """Test that shared room transcripts are visible to all authenticated users."""
    test_room_id = f"cross-user-shared-room-{uuid.uuid4()}"
    test_transcript_id = f"cross-user-transcript-{uuid.uuid4()}"
    creator_user = "creator-user"
    viewer_user = "viewer-user"

    try:
        room_data = create_test_room_data(
            test_room_id, "Cross-User Shared Room", creator_user, is_shared=True
        )
        await get_database().execute(rooms.insert().values(**room_data))

        transcript_data = create_test_transcript_data(
            test_transcript_id,
            "Cross-User Transcript",
            "Collaborative Session",
            user_id=creator_user,
            room_id=test_room_id,
            webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nCollaborative work",
        )
        transcript_data["duration"] = 2400.0
        await get_database().execute(transcripts.insert().values(**transcript_data))

        params = SearchParameters(query_text="collaborative", user_id=viewer_user)
        results, total = await search_controller.search_transcripts(params)

        matching_results = [r for r in results if r.id == test_transcript_id]
        assert (
            len(matching_results) == 1
        ), f"Expected exactly 1 matching result, got {len(matching_results)}"
        assert total >= 1, f"Total count should be at least 1, got {total}"

    finally:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id == test_transcript_id)
        )
        await get_database().execute(rooms.delete().where(rooms.c.id == test_room_id))
