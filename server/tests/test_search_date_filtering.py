from datetime import datetime, timedelta, timezone

import pytest

from reflector.db import get_database
from reflector.db.search import SearchParameters, search_controller
from reflector.db.transcripts import SourceKind, transcripts


@pytest.mark.asyncio
class TestDateRangeIntegration:
    async def setup_test_transcripts(self):
        # Use a test user_id that will match in our search parameters
        test_user_id = "test-user-123"

        test_data = [
            {
                "id": "test-before-range",
                "created_at": datetime(2024, 1, 15, tzinfo=timezone.utc),
                "title": "Before Range Transcript",
                "user_id": test_user_id,
            },
            {
                "id": "test-start-boundary",
                "created_at": datetime(2024, 6, 1, tzinfo=timezone.utc),
                "title": "Start Boundary Transcript",
                "user_id": test_user_id,
            },
            {
                "id": "test-middle-range",
                "created_at": datetime(2024, 6, 15, tzinfo=timezone.utc),
                "title": "Middle Range Transcript",
                "user_id": test_user_id,
            },
            {
                "id": "test-end-boundary",
                "created_at": datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
                "title": "End Boundary Transcript",
                "user_id": test_user_id,
            },
            {
                "id": "test-after-range",
                "created_at": datetime(2024, 12, 31, tzinfo=timezone.utc),
                "title": "After Range Transcript",
                "user_id": test_user_id,
            },
        ]

        for data in test_data:
            full_data = {
                "id": data["id"],
                "name": data["id"],
                "status": "ended",
                "locked": False,
                "duration": 60.0,
                "created_at": data["created_at"],
                "title": data["title"],
                "short_summary": "Test summary",
                "long_summary": "Test long summary",
                "share_mode": "public",
                "source_kind": SourceKind.FILE,
                "audio_deleted": False,
                "reviewed": False,
                "user_id": data["user_id"],
            }

            await get_database().execute(transcripts.insert().values(**full_data))

        return test_data

    async def cleanup_test_transcripts(self, test_data):
        """Clean up test transcripts."""
        for data in test_data:
            await get_database().execute(
                transcripts.delete().where(transcripts.c.id == data["id"])
            )

    @pytest.mark.asyncio
    async def test_filter_with_from_datetime_only(self):
        """Test filtering with only from_datetime parameter."""
        test_data = await self.setup_test_transcripts()
        test_user_id = "test-user-123"

        try:
            params = SearchParameters(
                query_text=None,
                from_datetime=datetime(2024, 6, 1, tzinfo=timezone.utc),
                to_datetime=None,
                user_id=test_user_id,
            )

            results, total = await search_controller.search_transcripts(params)

            # Should include: start_boundary, middle, end_boundary, after
            result_ids = [r.id for r in results]
            assert "test-before-range" not in result_ids
            assert "test-start-boundary" in result_ids
            assert "test-middle-range" in result_ids
            assert "test-end-boundary" in result_ids
            assert "test-after-range" in result_ids

        finally:
            await self.cleanup_test_transcripts(test_data)

    @pytest.mark.asyncio
    async def test_filter_with_to_datetime_only(self):
        """Test filtering with only to_datetime parameter."""
        test_data = await self.setup_test_transcripts()
        test_user_id = "test-user-123"

        try:
            params = SearchParameters(
                query_text=None,
                from_datetime=None,
                to_datetime=datetime(2024, 6, 30, tzinfo=timezone.utc),
                user_id=test_user_id,
            )

            results, total = await search_controller.search_transcripts(params)

            result_ids = [r.id for r in results]
            assert "test-before-range" in result_ids
            assert "test-start-boundary" in result_ids
            assert "test-middle-range" in result_ids
            assert "test-end-boundary" not in result_ids
            assert "test-after-range" not in result_ids

        finally:
            await self.cleanup_test_transcripts(test_data)

    @pytest.mark.asyncio
    async def test_filter_with_both_datetimes(self):
        test_data = await self.setup_test_transcripts()
        test_user_id = "test-user-123"

        try:
            params = SearchParameters(
                query_text=None,
                from_datetime=datetime(2024, 6, 1, tzinfo=timezone.utc),
                to_datetime=datetime(
                    2024, 7, 1, tzinfo=timezone.utc
                ),  # Inclusive of 6/30
                user_id=test_user_id,
            )

            results, total = await search_controller.search_transcripts(params)

            result_ids = [r.id for r in results]
            assert "test-before-range" not in result_ids
            assert "test-start-boundary" in result_ids
            assert "test-middle-range" in result_ids
            assert "test-end-boundary" in result_ids
            assert "test-after-range" not in result_ids

        finally:
            await self.cleanup_test_transcripts(test_data)

    @pytest.mark.asyncio
    async def test_date_filter_with_room_and_source_kind(self):
        test_data = await self.setup_test_transcripts()
        test_user_id = "test-user-123"

        try:
            params = SearchParameters(
                query_text=None,
                from_datetime=datetime(2024, 6, 1, tzinfo=timezone.utc),
                to_datetime=datetime(2024, 7, 1, tzinfo=timezone.utc),
                source_kind=SourceKind.FILE,
                room_id=None,
                user_id=test_user_id,
            )

            results, total = await search_controller.search_transcripts(params)

            for result in results:
                assert result.source_kind == SourceKind.FILE
                assert result.created_at >= datetime(2024, 6, 1, tzinfo=timezone.utc)
                assert result.created_at <= datetime(2024, 7, 1, tzinfo=timezone.utc)

        finally:
            await self.cleanup_test_transcripts(test_data)

    @pytest.mark.asyncio
    async def test_empty_results_for_future_dates(self):
        test_data = await self.setup_test_transcripts()
        test_user_id = "test-user-123"

        try:
            params = SearchParameters(
                query_text=None,
                from_datetime=datetime(2099, 1, 1, tzinfo=timezone.utc),
                to_datetime=datetime(2099, 12, 31, tzinfo=timezone.utc),
                user_id=test_user_id,
            )

            results, total = await search_controller.search_transcripts(params)

            assert results == []
            assert total == 0

        finally:
            await self.cleanup_test_transcripts(test_data)

    @pytest.mark.asyncio
    async def test_date_only_input_handling(self):
        test_data = await self.setup_test_transcripts()
        test_user_id = "test-user-123"

        try:
            # Pydantic will parse date-only strings to datetime at midnight
            from_dt = datetime(2024, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
            to_dt = datetime(2024, 6, 16, 0, 0, 0, tzinfo=timezone.utc)

            params = SearchParameters(
                query_text=None,
                from_datetime=from_dt,
                to_datetime=to_dt,
                user_id=test_user_id,
            )

            results, total = await search_controller.search_transcripts(params)

            result_ids = [r.id for r in results]
            assert "test-middle-range" in result_ids
            assert "test-before-range" not in result_ids
            assert "test-after-range" not in result_ids

        finally:
            await self.cleanup_test_transcripts(test_data)


class TestDateValidationEdgeCases:
    """Edge case tests for datetime validation."""

    def test_timezone_aware_comparison(self):
        """Test that timezone-aware comparisons work correctly."""
        # PST time (UTC-8)
        pst = timezone(timedelta(hours=-8))
        pst_dt = datetime(2024, 6, 15, 8, 0, 0, tzinfo=pst)

        # UTC time equivalent (8AM PST = 4PM UTC)
        utc_dt = datetime(2024, 6, 15, 16, 0, 0, tzinfo=timezone.utc)

        assert pst_dt == utc_dt

    def test_mixed_timezone_input(self):
        """Test handling mixed timezone inputs."""
        pst = timezone(timedelta(hours=-8))
        ist = timezone(timedelta(hours=5, minutes=30))

        from_date = datetime(2024, 6, 15, 0, 0, 0, tzinfo=pst)  # PST midnight
        to_date = datetime(2024, 6, 15, 23, 59, 59, tzinfo=ist)  # IST end of day

        assert from_date.tzinfo is not None
        assert to_date.tzinfo is not None
        assert from_date < to_date
