"""Tests for full-text search functionality."""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, TypedDict
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


class RoomTestData(TypedDict):
    """Type definition for room test data."""

    id: str
    name: str
    user_id: str
    is_shared: bool
    created_at: datetime


class TranscriptTestData(TypedDict, total=False):
    """Type definition for transcript test data."""

    # Required fields
    id: str
    name: str
    title: str
    status: str
    created_at: datetime
    duration: float
    source_kind: SourceKind
    topics: str
    events: str
    participants: str
    webvtt: Optional[str]

    # Optional fields
    room_id: Optional[str]
    user_id: Optional[str]
    locked: bool
    short_summary: Optional[str]
    long_summary: Optional[str]
    source_language: str
    target_language: str
    reviewed: bool
    audio_location: str
    share_mode: str


# Test constants
DEFAULT_DURATION = 1800.0
SHORT_DURATION = 600.0
LONG_DURATION = 2400.0
DEFAULT_WEBVTT = "WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nTest content"
RANK_MIN = 0.0
RANK_MAX = 1.0


@pytest.fixture
async def db_cleanup():
    """Fixture to track and cleanup database entities after test."""
    transcript_ids: List[str] = []
    room_ids: List[str] = []

    class Tracker:
        def add_transcript(self, id: str) -> None:
            transcript_ids.append(id)

        def add_room(self, id: str) -> None:
            room_ids.append(id)

        def add_transcripts(self, ids: List[str]) -> None:
            transcript_ids.extend(ids)

        def add_rooms(self, ids: List[str]) -> None:
            room_ids.extend(ids)

    yield Tracker()

    # Cleanup after test
    if transcript_ids:
        await get_database().execute(
            transcripts.delete().where(transcripts.c.id.in_(transcript_ids))
        )
    if room_ids:
        await get_database().execute(rooms.delete().where(rooms.c.id.in_(room_ids)))


def create_test_room_data(
    room_id: str, name: str, user_id: str, is_shared: bool
) -> RoomTestData:
    """Helper to create consistent room test data."""
    return RoomTestData(
        id=room_id,
        name=name,
        user_id=user_id,
        is_shared=is_shared,
        created_at=datetime.now(timezone.utc),
    )


def create_test_transcript_data(
    transcript_id: str,
    name: str,
    title: str,
    user_id: Optional[str] = None,
    room_id: Optional[str] = None,
    webvtt: str = DEFAULT_WEBVTT,
    duration: float = DEFAULT_DURATION,
    source_kind: Optional[SourceKind] = None,
) -> TranscriptTestData:
    """Helper to create consistent transcript test data."""
    if source_kind is None:
        source_kind = SourceKind.ROOM if room_id else SourceKind.FILE

    return TranscriptTestData(
        id=transcript_id,
        name=name,
        title=title,
        status="completed",
        room_id=room_id,
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        duration=duration,
        source_kind=source_kind,
        topics=json.dumps([]),
        events=json.dumps([]),
        participants=json.dumps([]),
        webvtt=webvtt,
    )


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
async def test_empty_transcript_title_only_match(db_cleanup):
    """Test that transcripts with title-only matches return empty snippets."""
    test_id = f"test-empty-{uuid.uuid4()}"
    test_user = f"test-user-empty-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

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

    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for title search, got {len(matching)}"
    assert total >= 1, f"Total should be at least 1, got {total}"
    found = matching[0]
    assert found.search_snippets == []
    assert found.total_match_count == 0


@pytest.mark.asyncio
async def test_search_with_long_summary(db_cleanup):
    """Test that long_summary content is searchable."""
    test_id = f"test-long-summary-{uuid.uuid4()}"
    test_user = f"test-user-summary-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

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

    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for long_summary search, got {len(matching)}"
    assert total >= 1, f"Total should be at least 1, got {total}"

    test_result = next((r for r in results if r.id == test_id), None)
    assert test_result
    assert (
        len(test_result.search_snippets) > 0
    ), f"Expected snippets for 'quantum computing', got {test_result.search_snippets}"
    assert "quantum computing" in test_result.search_snippets[0].lower()


@pytest.mark.asyncio
async def test_search_by_title_word(db_cleanup):
    """Test searching for a transcript by a word in its title."""
    test_id = f"test-title-word-{uuid.uuid4()}"
    test_user = f"test-user-title-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

    test_data = create_test_transcript_data(
        test_id,
        "Test Search Transcript",
        "Engineering Planning Meeting Q4 2024",
        user_id=test_user,
        webvtt="""WEBVTT

00:00:00.000 --> 00:00:10.000
Welcome to our engineering planning meeting for Q4 2024.""",
    )
    await get_database().execute(transcripts.insert().values(**test_data))

    params = SearchParameters(query_text="planning", user_id=test_user)
    results, total = await search_controller.search_transcripts(params)

    assert total >= 1, f"Expected at least 1 result for 'planning', got {total}"
    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for 'planning', got {len(matching)}"


@pytest.mark.asyncio
async def test_search_by_webvtt_content(db_cleanup):
    """Test searching for a transcript by content in its WebVTT captions."""
    test_id = f"test-webvtt-search-{uuid.uuid4()}"
    test_user = f"test-user-webvtt-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

    test_data = create_test_transcript_data(
        test_id,
        "Test WebVTT Search",
        "Technical Discussion",
        user_id=test_user,
        webvtt="""WEBVTT

00:00:00.000 --> 00:00:10.000
We need to implement PostgreSQL tsvector for better performance.""",
    )
    await get_database().execute(transcripts.insert().values(**test_data))

    params = SearchParameters(query_text="tsvector", user_id=test_user)
    results, total = await search_controller.search_transcripts(params)

    assert total >= 1, f"Expected at least 1 result for 'tsvector', got {total}"
    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for 'tsvector', got {len(matching)}"


@pytest.mark.asyncio
async def test_search_by_multiple_words(db_cleanup):
    """Test searching for a transcript using multiple words."""
    test_id = f"test-multi-word-{uuid.uuid4()}"
    test_user = f"test-user-multi-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

    test_data = create_test_transcript_data(
        test_id,
        "Test Multi Word",
        "Engineering Planning Meeting Q4 2024",
        user_id=test_user,
        webvtt="""WEBVTT

00:00:00.000 --> 00:00:10.000
Welcome to our engineering planning meeting for Q4 2024.""",
    )
    await get_database().execute(transcripts.insert().values(**test_data))

    params = SearchParameters(query_text="engineering planning", user_id=test_user)
    results, total = await search_controller.search_transcripts(params)

    assert (
        total >= 1
    ), f"Expected at least 1 result for 'engineering planning', got {total}"
    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for multi-word search, got {len(matching)}"

    # Verify result metadata
    test_result = matching[0]
    assert test_result.title == "Engineering Planning Meeting Q4 2024"
    assert test_result.status == "completed"
    assert test_result.duration == DEFAULT_DURATION
    assert (
        RANK_MIN <= test_result.rank <= RANK_MAX
    ), f"Rank should be normalized to {RANK_MIN}-{RANK_MAX}"


@pytest.mark.asyncio
async def test_search_with_or_operator(db_cleanup):
    """Test search using OR operator to match multiple terms."""
    test_id = f"test-or-operator-{uuid.uuid4()}"
    test_user = f"test-user-or-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

    test_data = create_test_transcript_data(
        test_id,
        "Test OR Operator",
        "Database Performance",
        user_id=test_user,
        webvtt="""WEBVTT

00:00:00.000 --> 00:00:10.000
We need to implement PostgreSQL tsvector for better performance.""",
    )
    await get_database().execute(transcripts.insert().values(**test_data))

    params = SearchParameters(query_text="tsvector OR nosuchword", user_id=test_user)
    results, total = await search_controller.search_transcripts(params)

    assert total >= 1, f"Expected at least 1 result for OR query, got {total}"
    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for OR query, got {len(matching)}"


@pytest.mark.parametrize(
    "query,operator_type",
    [
        ("tsvector OR nosuchword", "OR"),
        ("tsvector AND PostgreSQL", "AND"),
    ],
)
@pytest.mark.asyncio
async def test_search_boolean_operators(db_cleanup, query, operator_type):
    """Test search using boolean operators."""
    test_id = f"test-{operator_type.lower()}-operator-{uuid.uuid4()}"
    test_user = f"test-user-{operator_type.lower()}-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

    test_data = create_test_transcript_data(
        test_id,
        f"Test {operator_type} Operator",
        "Database Performance",
        user_id=test_user,
        webvtt="""WEBVTT

00:00:00.000 --> 00:00:10.000
We need to implement PostgreSQL tsvector for better performance.""",
    )
    await get_database().execute(transcripts.insert().values(**test_data))

    params = SearchParameters(query_text=query, user_id=test_user)
    results, total = await search_controller.search_transcripts(params)

    assert (
        total >= 1
    ), f"Expected at least 1 result for {operator_type} query, got {total}"
    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for {operator_type} query, got {len(matching)}"


@pytest.mark.asyncio
async def test_search_exact_phrase(db_cleanup):
    """Test searching for an exact phrase using quotes."""
    test_id = f"test-exact-phrase-{uuid.uuid4()}"
    test_user = f"test-user-phrase-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)

    test_data = create_test_transcript_data(
        test_id,
        "Test Exact Phrase",
        "Search Implementation",
        user_id=test_user,
        webvtt="""WEBVTT

00:00:00.000 --> 00:00:10.000
Today we'll discuss the implementation of full-text search.""",
    )
    await get_database().execute(transcripts.insert().values(**test_data))

    params = SearchParameters(query_text='"full-text search"', user_id=test_user)
    results, total = await search_controller.search_transcripts(params)

    assert total >= 1, f"Expected at least 1 result for exact phrase, got {total}"
    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for exact phrase, got {len(matching)}"


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
async def test_search_shared_room_visible_to_anonymous(db_cleanup):
    """Test that transcripts in shared rooms are searchable without user_id."""
    test_room_id = f"shared-room-test-{uuid.uuid4()}"
    test_transcript_id = f"shared-transcript-{uuid.uuid4()}"
    owner_user = "room-owner"
    db_cleanup.add_room(test_room_id)
    db_cleanup.add_transcript(test_transcript_id)
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


@pytest.mark.asyncio
async def test_search_private_room_requires_user_match(db_cleanup):
    """Test that transcripts in private rooms require matching user_id."""
    test_room_id = f"private-room-test-{uuid.uuid4()}"
    test_transcript_id = f"private-transcript-{uuid.uuid4()}"
    owner_user = "user1"
    other_user = "user2"
    db_cleanup.add_room(test_room_id)
    db_cleanup.add_transcript(test_transcript_id)
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
    matching = [r for r in results if r.id == test_transcript_id]
    assert (
        len(matching) == 0
    ), f"Should NOT find private room transcript with different user_id, but found {len(matching)}"

    params_owner = SearchParameters(query_text="confidential", user_id=owner_user)
    results, total = await search_controller.search_transcripts(params_owner)
    matching = [r for r in results if r.id == test_transcript_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for owner search, got {len(matching)}"


@pytest.mark.asyncio
async def test_search_no_room_requires_user_id(db_cleanup):
    """Test that transcripts without rooms are only visible to their owner."""
    test_transcript_id = f"no-room-transcript-{uuid.uuid4()}"
    owner_user = "file-uploader"
    other_user = "another-user"
    db_cleanup.add_transcript(test_transcript_id)
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
    matching = [r for r in results if r.id == test_transcript_id]
    assert (
        len(matching) == 0
    ), f"Should NOT find room-less transcript without user_id, but found {len(matching)}"

    params_other = SearchParameters(query_text="upload", user_id=other_user)
    results, total = await search_controller.search_transcripts(params_other)
    matching = [r for r in results if r.id == test_transcript_id]
    assert (
        len(matching) == 0
    ), f"Should NOT find room-less transcript with different user_id, but found {len(matching)}"

    params_owner = SearchParameters(query_text="upload", user_id=owner_user)
    results, total = await search_controller.search_transcripts(params_owner)
    matching = [r for r in results if r.id == test_transcript_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for owner search, got {len(matching)}"


@pytest.mark.asyncio
async def test_user_sees_own_private_and_others_shared(db_cleanup):
    """Test that users see their own private transcripts plus all shared transcripts."""
    # Setup: Create unique IDs for test isolation
    test_private_id = f"private-{uuid.uuid4()}"
    test_shared_id = f"shared-{uuid.uuid4()}"
    test_private_room = f"private-room-{uuid.uuid4()}"
    test_shared_room = f"shared-room-{uuid.uuid4()}"
    user1 = f"user1-{uuid.uuid4()}"
    user2 = f"user2-{uuid.uuid4()}"
    db_cleanup.add_rooms([test_private_room, test_shared_room])
    db_cleanup.add_transcripts([test_private_id, test_shared_id])
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
    await get_database().execute(transcripts.insert().values(**private_transcript_data))

    shared_transcript_data = create_test_transcript_data(
        test_shared_id,
        "User2 Shared Transcript",
        "Strategy Workshop",
        user_id=user2,
        room_id=test_shared_room,
        webvtt="WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nStrategy workshop",
    )
    await get_database().execute(transcripts.insert().values(**shared_transcript_data))

    params = SearchParameters(query_text="strategy", user_id=user1)
    results, total = await search_controller.search_transcripts(params)
    result_ids = {r.id for r in results}

    assert test_private_id in result_ids, "Should find user's own private transcript"
    assert test_shared_id in result_ids, "Should find shared room transcript"
    assert (
        len(result_ids) >= 2
    ), f"Should find at least 2 transcripts, got {len(result_ids)}"
    assert total >= 2, f"Total count should be at least 2, got {total}"


@pytest.mark.asyncio
async def test_search_shared_room_cross_user_visibility(db_cleanup):
    """Test that shared room transcripts are visible to all authenticated users."""
    test_room_id = f"cross-user-shared-room-{uuid.uuid4()}"
    test_transcript_id = f"cross-user-transcript-{uuid.uuid4()}"
    creator_user = "creator-user"
    viewer_user = "viewer-user"
    db_cleanup.add_room(test_room_id)
    db_cleanup.add_transcript(test_transcript_id)
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


@pytest.mark.asyncio
async def test_long_summary_snippet_prioritization(db_cleanup):
    """Test that snippets from long_summary are prioritized over webvtt content."""
    test_id = f"test-snippet-priority-{uuid.uuid4()}"
    test_user = f"test-user-priority-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)
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

    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for robotics search, got {len(matching)}"
    test_result = matching[0]

    snippets = test_result.search_snippets
    assert len(snippets) > 0, "Should have at least one snippet"

    first_snippet = snippets[0].lower()
    assert (
        "advanced robotics" in first_snippet or "autonomous" in first_snippet
    ), f"First snippet should be from long_summary with detailed content. Got: {snippets[0]}"

    assert len(snippets) <= 3, "Should respect max snippets limit of 3"

    for snippet in snippets:
        assert (
            "robotics" in snippet.lower()
        ), f"Snippet should contain search term: {snippet}"


@pytest.mark.asyncio
async def test_long_summary_only_search(db_cleanup):
    """Test searching for content that only exists in long_summary."""
    test_id = f"test-long-only-{uuid.uuid4()}"
    test_user = f"test-user-longonly-{uuid.uuid4()}"
    db_cleanup.add_transcript(test_id)
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

    matching = [r for r in results if r.id == test_id]
    assert (
        len(matching) == 1
    ), f"Expected exactly 1 match for cryptocurrency search, got {len(matching)}"
    test_result = matching[0]
    assert (
        len(test_result.search_snippets) > 0
    ), f"Expected snippets for 'cryptocurrency', got {test_result.search_snippets}"

    snippet = test_result.search_snippets[0].lower()
    assert "cryptocurrency" in snippet, "Snippet should contain the search term"

    params2 = SearchParameters(query_text="yield farming", user_id=test_user)
    results2, total2 = await search_controller.search_transcripts(params2)

    matching2 = [r for r in results2 if r.id == test_id]
    assert (
        len(matching2) == 1
    ), f"Expected exactly 1 match for 'yield farming', got {len(matching2)}"
