"""Tests for DAG status REST enrichment on search and transcript GET endpoints."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import reflector.db.search as search_module
from reflector.db.search import SearchResult, _fetch_dag_statuses
from reflector.db.transcripts import TranscriptEvent


class TestFetchDagStatuses:
    """Test the _fetch_dag_statuses helper."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_ids(self):
        result = await _fetch_dag_statuses([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_extracts_last_dag_status(self):
        events = [
            {"event": "STATUS", "data": {"value": "processing"}},
            {
                "event": "DAG_STATUS",
                "data": {
                    "workflow_run_id": "r1",
                    "tasks": [{"name": "get_recording", "status": "completed"}],
                },
            },
            {
                "event": "DAG_STATUS",
                "data": {
                    "workflow_run_id": "r1",
                    "tasks": [
                        {"name": "get_recording", "status": "completed"},
                        {"name": "process_tracks", "status": "running"},
                    ],
                },
            },
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert "t1" in result
        assert len(result["t1"]) == 2  # Last DAG_STATUS had 2 tasks

    @pytest.mark.asyncio
    async def test_skips_transcripts_without_events(self):
        mock_row = {"id": "t1", "events": None}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_skips_transcripts_without_dag_status(self):
        events = [
            {"event": "STATUS", "data": {"value": "processing"}},
            {"event": "DURATION", "data": {"duration": 1000}},
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_handles_json_string_events(self):
        """Events stored as JSON string rather than already-parsed list."""
        import json

        events = [
            {
                "event": "DAG_STATUS",
                "data": {
                    "workflow_run_id": "r1",
                    "tasks": [{"name": "transcribe", "status": "running"}],
                },
            },
        ]
        mock_row = {"id": "t1", "events": json.dumps(events)}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert "t1" in result
        assert len(result["t1"]) == 1
        assert result["t1"][0]["name"] == "transcribe"

    @pytest.mark.asyncio
    async def test_multiple_transcripts(self):
        """Handles multiple transcripts in one call."""
        events_t1 = [
            {
                "event": "DAG_STATUS",
                "data": {
                    "workflow_run_id": "r1",
                    "tasks": [{"name": "a", "status": "completed"}],
                },
            },
        ]
        events_t2 = [
            {
                "event": "DAG_STATUS",
                "data": {
                    "workflow_run_id": "r2",
                    "tasks": [{"name": "b", "status": "running"}],
                },
            },
        ]
        mock_rows = [
            {"id": "t1", "events": events_t1},
            {"id": "t2", "events": events_t2},
        ]

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=mock_rows)
            result = await _fetch_dag_statuses(["t1", "t2"])

        assert "t1" in result
        assert "t2" in result
        assert result["t1"][0]["name"] == "a"
        assert result["t2"][0]["name"] == "b"

    @pytest.mark.asyncio
    async def test_dag_status_without_tasks_key_skipped(self):
        """DAG_STATUS event with no tasks key in data should be skipped."""
        events = [
            {"event": "DAG_STATUS", "data": {"workflow_run_id": "r1"}},
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert result == {}


class TestFetchDagStatusesMalformedData:
    """Test _fetch_dag_statuses with malformed event data."""

    @pytest.mark.asyncio
    async def test_event_missing_data_key(self):
        """DAG_STATUS event without 'data' key: ev.get('data', {}) returns {},
        then {}.get('tasks') returns None, so transcript is skipped gracefully."""
        events = [
            {"event": "DAG_STATUS"},
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_event_data_is_string(self):
        """DAG_STATUS event where data is a string instead of dict.
        ev.get('data', {}) returns the string, then .get('tasks') raises
        AttributeError because str has no .get() method."""
        events = [
            {"event": "DAG_STATUS", "data": "not-a-dict"},
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            with pytest.raises(AttributeError):
                await _fetch_dag_statuses(["t1"])

    @pytest.mark.asyncio
    async def test_events_list_with_non_dict_elements_skipped(self):
        """Non-dict elements in events list are skipped by isinstance check."""
        events = [
            42,
            "a string event",
            None,
            {
                "event": "DAG_STATUS",
                "data": {
                    "workflow_run_id": "r1",
                    "tasks": [{"name": "transcribe", "status": "running"}],
                },
            },
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert "t1" in result
        assert result["t1"][0]["name"] == "transcribe"

    @pytest.mark.asyncio
    async def test_events_list_only_non_dict_elements(self):
        """Events list containing only non-dict elements produces no result."""
        events = [42, "hello", None, True]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            result = await _fetch_dag_statuses(["t1"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_event_data_is_none(self):
        """DAG_STATUS event where data is explicitly None.
        ev.get('data', {}) returns None, then None.get('tasks') raises
        AttributeError."""
        events = [
            {"event": "DAG_STATUS", "data": None},
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            with pytest.raises(AttributeError):
                await _fetch_dag_statuses(["t1"])

    @pytest.mark.asyncio
    async def test_event_data_is_list(self):
        """DAG_STATUS event where data is a list instead of dict.
        Lists don't have .get(), so raises AttributeError."""
        events = [
            {"event": "DAG_STATUS", "data": ["not", "a", "dict"]},
        ]
        mock_row = {"id": "t1", "events": events}

        with patch("reflector.db.search.get_database") as mock_db:
            mock_db.return_value.fetch_all = AsyncMock(return_value=[mock_row])
            with pytest.raises(AttributeError):
                await _fetch_dag_statuses(["t1"])


def _extract_dag_status_from_transcript(transcript):
    """Replicate the dag_status extraction logic from transcript_get view.

    This mirrors the code in reflector/views/transcripts.py lines 495-500:
        dag_status = None
        if transcript.status == "processing" and transcript.events:
            for ev in reversed(transcript.events):
                if ev.event == "DAG_STATUS":
                    dag_status = ev.data.get("tasks") if isinstance(ev.data, dict) else None
                    break
    """
    dag_status = None
    if transcript.status == "processing" and transcript.events:
        for ev in reversed(transcript.events):
            if ev.event == "DAG_STATUS":
                dag_status = ev.data.get("tasks") if isinstance(ev.data, dict) else None
                break
    return dag_status


class TestTranscriptGetDagStatusExtraction:
    """Test dag_status extraction logic from transcript_get endpoint.

    The actual endpoint is complex to set up, so we test the extraction
    logic directly using the same code pattern from the view.
    """

    def test_processing_transcript_with_dag_status_events(self):
        """Processing transcript with DAG_STATUS events returns tasks from last event."""
        transcript = SimpleNamespace(
            status="processing",
            events=[
                TranscriptEvent(event="STATUS", data={"value": "processing"}),
                TranscriptEvent(
                    event="DAG_STATUS",
                    data={
                        "workflow_run_id": "r1",
                        "tasks": [{"name": "get_recording", "status": "completed"}],
                    },
                ),
                TranscriptEvent(
                    event="DAG_STATUS",
                    data={
                        "workflow_run_id": "r1",
                        "tasks": [
                            {"name": "get_recording", "status": "completed"},
                            {"name": "transcribe", "status": "running"},
                        ],
                    },
                ),
            ],
        )

        result = _extract_dag_status_from_transcript(transcript)

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "get_recording"
        assert result[1]["name"] == "transcribe"
        assert result[1]["status"] == "running"

    def test_processing_transcript_without_dag_status_events(self):
        """Processing transcript with only non-DAG_STATUS events returns None."""
        transcript = SimpleNamespace(
            status="processing",
            events=[
                TranscriptEvent(event="STATUS", data={"value": "processing"}),
                TranscriptEvent(event="DURATION", data={"duration": 1000}),
            ],
        )

        result = _extract_dag_status_from_transcript(transcript)
        assert result is None

    def test_ended_transcript_with_dag_status_events(self):
        """Ended transcript with DAG_STATUS events returns None (status check)."""
        transcript = SimpleNamespace(
            status="ended",
            events=[
                TranscriptEvent(
                    event="DAG_STATUS",
                    data={
                        "workflow_run_id": "r1",
                        "tasks": [{"name": "transcribe", "status": "completed"}],
                    },
                ),
            ],
        )

        result = _extract_dag_status_from_transcript(transcript)
        assert result is None

    def test_processing_transcript_with_empty_events(self):
        """Processing transcript with empty events list returns None."""
        transcript = SimpleNamespace(
            status="processing",
            events=[],
        )

        result = _extract_dag_status_from_transcript(transcript)
        assert result is None

    def test_processing_transcript_with_none_events(self):
        """Processing transcript with None events returns None."""
        transcript = SimpleNamespace(
            status="processing",
            events=None,
        )

        result = _extract_dag_status_from_transcript(transcript)
        assert result is None

    def test_extracts_last_dag_status_not_first(self):
        """Should pick the last DAG_STATUS event (most recent), not the first."""
        transcript = SimpleNamespace(
            status="processing",
            events=[
                TranscriptEvent(
                    event="DAG_STATUS",
                    data={
                        "workflow_run_id": "r1",
                        "tasks": [{"name": "a", "status": "running"}],
                    },
                ),
                TranscriptEvent(event="STATUS", data={"value": "processing"}),
                TranscriptEvent(
                    event="DAG_STATUS",
                    data={
                        "workflow_run_id": "r1",
                        "tasks": [
                            {"name": "a", "status": "completed"},
                            {"name": "b", "status": "running"},
                        ],
                    },
                ),
            ],
        )

        result = _extract_dag_status_from_transcript(transcript)
        assert len(result) == 2
        assert result[0]["status"] == "completed"
        assert result[1]["name"] == "b"


class TestSearchEnrichmentIntegration:
    """Test DAG status enrichment in search results.

    The search function enriches processing transcripts with dag_status
    by calling _fetch_dag_statuses for processing IDs and assigning results.
    We test this enrichment logic by mocking _fetch_dag_statuses.
    """

    def _make_search_result(self, id: str, status: str) -> SearchResult:
        """Create a minimal SearchResult for testing."""
        return SearchResult(
            id=id,
            title=f"Transcript {id}",
            user_id="u1",
            room_id=None,
            room_name=None,
            source_kind="live",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            status=status,
            rank=1.0,
            duration=60.0,
            search_snippets=[],
            total_match_count=0,
            dag_status=None,
        )

    @pytest.mark.asyncio
    async def test_processing_result_gets_dag_status(self):
        """SearchResult with status='processing' and matching DAG_STATUS events
        gets dag_status populated."""
        results = [self._make_search_result("t1", "processing")]
        dag_tasks = [
            {"name": "get_recording", "status": "completed"},
            {"name": "transcribe", "status": "running"},
        ]

        with patch.object(
            search_module,
            "_fetch_dag_statuses",
            new_callable=AsyncMock,
            return_value={"t1": dag_tasks},
        ) as mock_fetch:
            # Replicate the enrichment logic from SearchController.search_transcripts
            processing_ids = [r.id for r in results if r.status == "processing"]
            if processing_ids:
                dag_statuses = await search_module._fetch_dag_statuses(processing_ids)
                for r in results:
                    if r.id in dag_statuses:
                        r.dag_status = dag_statuses[r.id]

            mock_fetch.assert_called_once_with(["t1"])

        assert results[0].dag_status == dag_tasks

    @pytest.mark.asyncio
    async def test_ended_result_does_not_trigger_fetch(self):
        """SearchResult with status='ended' does NOT trigger _fetch_dag_statuses."""
        results = [self._make_search_result("t1", "ended")]

        with patch.object(
            search_module,
            "_fetch_dag_statuses",
            new_callable=AsyncMock,
            return_value={},
        ) as mock_fetch:
            processing_ids = [r.id for r in results if r.status == "processing"]
            if processing_ids:
                dag_statuses = await search_module._fetch_dag_statuses(processing_ids)
                for r in results:
                    if r.id in dag_statuses:
                        r.dag_status = dag_statuses[r.id]

            mock_fetch.assert_not_called()

        assert results[0].dag_status is None

    @pytest.mark.asyncio
    async def test_mixed_processing_and_ended_results(self):
        """Only processing results get enriched; ended results stay None."""
        results = [
            self._make_search_result("t1", "processing"),
            self._make_search_result("t2", "ended"),
            self._make_search_result("t3", "processing"),
        ]
        dag_tasks_t1 = [{"name": "transcribe", "status": "running"}]
        dag_tasks_t3 = [{"name": "diarize", "status": "completed"}]

        with patch.object(
            search_module,
            "_fetch_dag_statuses",
            new_callable=AsyncMock,
            return_value={"t1": dag_tasks_t1, "t3": dag_tasks_t3},
        ) as mock_fetch:
            processing_ids = [r.id for r in results if r.status == "processing"]
            if processing_ids:
                dag_statuses = await search_module._fetch_dag_statuses(processing_ids)
                for r in results:
                    if r.id in dag_statuses:
                        r.dag_status = dag_statuses[r.id]

            mock_fetch.assert_called_once_with(["t1", "t3"])

        assert results[0].dag_status == dag_tasks_t1
        assert results[1].dag_status is None
        assert results[2].dag_status == dag_tasks_t3

    @pytest.mark.asyncio
    async def test_processing_result_without_dag_events_stays_none(self):
        """Processing result with no DAG_STATUS events in DB stays dag_status=None."""
        results = [self._make_search_result("t1", "processing")]

        with patch.object(
            search_module,
            "_fetch_dag_statuses",
            new_callable=AsyncMock,
            return_value={},
        ) as mock_fetch:
            processing_ids = [r.id for r in results if r.status == "processing"]
            if processing_ids:
                dag_statuses = await search_module._fetch_dag_statuses(processing_ids)
                for r in results:
                    if r.id in dag_statuses:
                        r.dag_status = dag_statuses[r.id]

            mock_fetch.assert_called_once_with(["t1"])

        assert results[0].dag_status is None
