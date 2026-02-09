"""Tests for DAG status REST enrichment on search and transcript GET endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from reflector.db.search import _fetch_dag_statuses


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
