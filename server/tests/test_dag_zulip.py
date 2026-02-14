"""
Tests for Hatchet DAG Status -> Zulip Live Updates.

Tests cover:
- _dag_zulip_enabled() guard logic
- create_dag_zulip_message: sends + stores message ID
- update_dag_zulip_message: updates existing; noop when no message_id
- delete_dag_zulip_message: deletes + clears; handles InvalidMessageError
- delete_zulip_message: sends HTTP DELETE; raises on 400
- with_error_handling integration: calls update after success + failure
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.db.transcripts import Transcript


@pytest.fixture
def dag_settings():
    """Patch settings for DAG Zulip tests."""
    with patch("reflector.hatchet.dag_zulip.settings") as mock_settings:
        mock_settings.ZULIP_REALM = "zulip.example.com"
        mock_settings.ZULIP_DAG_STREAM = "dag-stream"
        mock_settings.ZULIP_DAG_TOPIC = "dag-topic"
        mock_settings.ZULIP_BOT_EMAIL = "bot@example.com"
        mock_settings.ZULIP_API_KEY = "fake-key"
        yield mock_settings


@pytest.fixture
def dag_settings_disabled():
    """Patch settings with DAG Zulip disabled."""
    with patch("reflector.hatchet.dag_zulip.settings") as mock_settings:
        mock_settings.ZULIP_REALM = "zulip.example.com"
        mock_settings.ZULIP_DAG_STREAM = None
        mock_settings.ZULIP_DAG_TOPIC = None
        yield mock_settings


@pytest.fixture
def mock_transcript():
    return Transcript(
        id="test-transcript-id",
        name="Test",
        status="processing",
        source_kind="room",
        zulip_message_id=None,
    )


@pytest.fixture
def mock_transcript_with_zulip_id():
    return Transcript(
        id="test-transcript-id",
        name="Test",
        status="processing",
        source_kind="room",
        zulip_message_id=42,
    )


class TestDagZulipEnabled:
    def test_enabled_when_all_set(self, dag_settings):
        from reflector.hatchet.dag_zulip import _dag_zulip_enabled

        assert _dag_zulip_enabled() is True

    def test_disabled_when_realm_missing(self, dag_settings):
        dag_settings.ZULIP_REALM = None
        from reflector.hatchet.dag_zulip import _dag_zulip_enabled

        assert _dag_zulip_enabled() is False

    def test_disabled_when_stream_missing(self, dag_settings):
        dag_settings.ZULIP_DAG_STREAM = None
        from reflector.hatchet.dag_zulip import _dag_zulip_enabled

        assert _dag_zulip_enabled() is False

    def test_disabled_when_topic_missing(self, dag_settings):
        dag_settings.ZULIP_DAG_TOPIC = None
        from reflector.hatchet.dag_zulip import _dag_zulip_enabled

        assert _dag_zulip_enabled() is False


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
class TestCreateDagZulipMessage:
    async def test_sends_and_stores_message_id(self, dag_settings, mock_transcript):
        mock_run_details = MagicMock()
        rendered_md = "**DAG** rendered"

        with (
            patch(
                "reflector.hatchet.client.HatchetClientManager.get_client"
            ) as mock_get_client,
            patch(
                "reflector.tools.render_hatchet_run.render_run_detail",
                return_value=rendered_md,
            ),
            patch(
                "reflector.zulip.send_message_to_zulip",
                new_callable=AsyncMock,
                return_value={"id": 99},
            ) as mock_send,
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript,
            ),
            patch(
                "reflector.db.transcripts.transcripts_controller.update",
                new_callable=AsyncMock,
            ) as mock_update,
        ):
            mock_client = MagicMock()
            mock_client.runs.aio_get = AsyncMock(return_value=mock_run_details)
            mock_get_client.return_value = mock_client

            from reflector.hatchet.dag_zulip import create_dag_zulip_message

            await create_dag_zulip_message("test-transcript-id", "workflow-run-123")

            mock_send.assert_called_once_with("dag-stream", "dag-topic", rendered_md)
            mock_update.assert_called_once_with(
                mock_transcript, {"zulip_message_id": 99}
            )

    async def test_noop_when_disabled(self, dag_settings_disabled):
        with patch(
            "reflector.zulip.send_message_to_zulip",
            new_callable=AsyncMock,
        ) as mock_send:
            from reflector.hatchet.dag_zulip import create_dag_zulip_message

            await create_dag_zulip_message("test-transcript-id", "workflow-run-123")
            mock_send.assert_not_called()

    async def test_logs_warning_on_failure(self, dag_settings, mock_transcript):
        with (
            patch(
                "reflector.hatchet.client.HatchetClientManager.get_client"
            ) as mock_get_client,
            patch(
                "reflector.tools.render_hatchet_run.render_run_detail",
                return_value="rendered",
            ),
            patch(
                "reflector.zulip.send_message_to_zulip",
                new_callable=AsyncMock,
                side_effect=Exception("Zulip down"),
            ),
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript,
            ),
            patch("reflector.hatchet.dag_zulip.logger") as mock_logger,
        ):
            mock_client = MagicMock()
            mock_client.runs.aio_get = AsyncMock(return_value=MagicMock())
            mock_get_client.return_value = mock_client

            from reflector.hatchet.dag_zulip import create_dag_zulip_message

            # Should not raise
            await create_dag_zulip_message("test-transcript-id", "workflow-run-123")
            mock_logger.warning.assert_called()


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
class TestUpdateDagZulipMessage:
    async def test_updates_existing_message(
        self, dag_settings, mock_transcript_with_zulip_id
    ):
        mock_run_details = MagicMock()
        rendered_md = "**DAG** updated"

        with (
            patch(
                "reflector.hatchet.client.HatchetClientManager.get_client"
            ) as mock_get_client,
            patch(
                "reflector.tools.render_hatchet_run.render_run_detail",
                return_value=rendered_md,
            ),
            patch(
                "reflector.zulip.update_zulip_message",
                new_callable=AsyncMock,
            ) as mock_update,
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript_with_zulip_id,
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.fresh_db_connection"
            ) as mock_fresh_db,
        ):
            mock_client = MagicMock()
            mock_client.runs.aio_get = AsyncMock(return_value=mock_run_details)
            mock_get_client.return_value = mock_client
            mock_fresh_db.return_value.__aenter__ = AsyncMock()
            mock_fresh_db.return_value.__aexit__ = AsyncMock(return_value=False)

            from reflector.hatchet.dag_zulip import update_dag_zulip_message

            await update_dag_zulip_message("test-transcript-id", "workflow-run-123")

            mock_update.assert_called_once_with(
                42, "dag-stream", "dag-topic", rendered_md
            )

    async def test_appends_error_banner(
        self, dag_settings, mock_transcript_with_zulip_id
    ):
        mock_run_details = MagicMock()
        rendered_md = "**DAG** updated"

        with (
            patch(
                "reflector.hatchet.client.HatchetClientManager.get_client"
            ) as mock_get_client,
            patch(
                "reflector.tools.render_hatchet_run.render_run_detail",
                return_value=rendered_md,
            ),
            patch(
                "reflector.zulip.update_zulip_message",
                new_callable=AsyncMock,
            ) as mock_update,
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript_with_zulip_id,
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.fresh_db_connection"
            ) as mock_fresh_db,
        ):
            mock_client = MagicMock()
            mock_client.runs.aio_get = AsyncMock(return_value=mock_run_details)
            mock_get_client.return_value = mock_client
            mock_fresh_db.return_value.__aenter__ = AsyncMock()
            mock_fresh_db.return_value.__aexit__ = AsyncMock(return_value=False)

            from reflector.hatchet.dag_zulip import update_dag_zulip_message

            await update_dag_zulip_message(
                "test-transcript-id",
                "workflow-run-123",
                error_message="get_recording failed: connection timeout",
            )

            call_args = mock_update.call_args
            content = call_args[0][3]
            assert rendered_md in content
            assert "get_recording failed: connection timeout" in content

    async def test_noop_when_no_message_id(self, dag_settings, mock_transcript):
        with (
            patch(
                "reflector.zulip.update_zulip_message",
                new_callable=AsyncMock,
            ) as mock_update,
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript,
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.fresh_db_connection"
            ) as mock_fresh_db,
        ):
            mock_fresh_db.return_value.__aenter__ = AsyncMock()
            mock_fresh_db.return_value.__aexit__ = AsyncMock(return_value=False)

            from reflector.hatchet.dag_zulip import update_dag_zulip_message

            await update_dag_zulip_message("test-transcript-id", "workflow-run-123")
            mock_update.assert_not_called()

    async def test_noop_when_disabled(self, dag_settings_disabled):
        with patch(
            "reflector.zulip.update_zulip_message",
            new_callable=AsyncMock,
        ) as mock_update:
            from reflector.hatchet.dag_zulip import update_dag_zulip_message

            await update_dag_zulip_message("test-transcript-id", "workflow-run-123")
            mock_update.assert_not_called()


@pytest.mark.usefixtures("setup_database")
@pytest.mark.asyncio
class TestDeleteDagZulipMessage:
    async def test_deletes_and_clears(
        self, dag_settings, mock_transcript_with_zulip_id
    ):
        with (
            patch(
                "reflector.zulip.delete_zulip_message",
                new_callable=AsyncMock,
            ) as mock_delete,
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript_with_zulip_id,
            ),
            patch(
                "reflector.db.transcripts.transcripts_controller.update",
                new_callable=AsyncMock,
            ) as mock_tc_update,
        ):
            from reflector.hatchet.dag_zulip import delete_dag_zulip_message

            await delete_dag_zulip_message("test-transcript-id")

            mock_delete.assert_called_once_with(42)
            mock_tc_update.assert_called_once_with(
                mock_transcript_with_zulip_id, {"zulip_message_id": None}
            )

    async def test_noop_when_no_message_id(self, dag_settings, mock_transcript):
        with (
            patch(
                "reflector.zulip.delete_zulip_message",
                new_callable=AsyncMock,
            ) as mock_delete,
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript,
            ),
        ):
            from reflector.hatchet.dag_zulip import delete_dag_zulip_message

            await delete_dag_zulip_message("test-transcript-id")
            mock_delete.assert_not_called()

    async def test_handles_invalid_message_error(
        self, dag_settings, mock_transcript_with_zulip_id
    ):
        from reflector.zulip import InvalidMessageError

        with (
            patch(
                "reflector.zulip.delete_zulip_message",
                new_callable=AsyncMock,
                side_effect=InvalidMessageError("gone"),
            ),
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript_with_zulip_id,
            ),
            patch(
                "reflector.db.transcripts.transcripts_controller.update",
                new_callable=AsyncMock,
            ) as mock_tc_update,
            patch("reflector.hatchet.dag_zulip.logger"),
        ):
            from reflector.hatchet.dag_zulip import delete_dag_zulip_message

            # Should not raise; should still clear the message_id
            await delete_dag_zulip_message("test-transcript-id")
            mock_tc_update.assert_called_once_with(
                mock_transcript_with_zulip_id, {"zulip_message_id": None}
            )

    async def test_noop_when_disabled(self, dag_settings_disabled):
        with patch(
            "reflector.zulip.delete_zulip_message",
            new_callable=AsyncMock,
        ) as mock_delete:
            from reflector.hatchet.dag_zulip import delete_dag_zulip_message

            await delete_dag_zulip_message("test-transcript-id")
            mock_delete.assert_not_called()


@pytest.mark.asyncio
class TestDeleteZulipMessage:
    async def test_sends_delete_request(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "success"}

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("reflector.zulip.httpx.AsyncClient", return_value=mock_client):
            with patch("reflector.zulip.settings") as mock_settings:
                mock_settings.ZULIP_REALM = "zulip.example.com"
                mock_settings.ZULIP_BOT_EMAIL = "bot@example.com"
                mock_settings.ZULIP_API_KEY = "fake-key"

                from reflector.zulip import delete_zulip_message

                result = await delete_zulip_message(123)
                assert result == {"result": "success"}

                mock_client.delete.assert_called_once()
                call_args = mock_client.delete.call_args
                assert "123" in call_args.args[0]

    async def test_raises_invalid_message_on_400(self):
        from reflector.zulip import InvalidMessageError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"msg": "Invalid message(s)"}

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("reflector.zulip.httpx.AsyncClient", return_value=mock_client):
            with patch("reflector.zulip.settings") as mock_settings:
                mock_settings.ZULIP_REALM = "zulip.example.com"
                mock_settings.ZULIP_BOT_EMAIL = "bot@example.com"
                mock_settings.ZULIP_API_KEY = "fake-key"

                from reflector.zulip import delete_zulip_message

                with pytest.raises(InvalidMessageError):
                    await delete_zulip_message(999)


@pytest.mark.asyncio
class TestWithErrorHandlingDagUpdate:
    """Test that with_error_handling calls update_dag_zulip_message."""

    async def test_calls_update_on_success(self):
        from reflector.hatchet.constants import TaskName
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            PipelineInput,
            with_error_handling,
        )

        mock_ctx = MagicMock()
        mock_ctx.workflow_run_id = "wfr-123"

        input_data = PipelineInput(
            recording_id="rec-1",
            tracks=[{"s3_key": "k"}],
            bucket_name="bucket",
            transcript_id="tid-1",
        )

        @with_error_handling(TaskName.GET_RECORDING)
        async def fake_task(input: PipelineInput, ctx) -> str:
            return "ok"

        with patch(
            "reflector.hatchet.workflows.daily_multitrack_pipeline.update_dag_zulip_message",
            new_callable=AsyncMock,
        ) as mock_update:
            result = await fake_task(input_data, mock_ctx)
            assert result == "ok"
            mock_update.assert_called_once_with("tid-1", "wfr-123")

    async def test_calls_update_on_failure_with_error_message(self):
        from reflector.hatchet.constants import TaskName
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            PipelineInput,
            with_error_handling,
        )

        mock_ctx = MagicMock()
        mock_ctx.workflow_run_id = "wfr-123"

        input_data = PipelineInput(
            recording_id="rec-1",
            tracks=[{"s3_key": "k"}],
            bucket_name="bucket",
            transcript_id="tid-1",
        )

        @with_error_handling(TaskName.GET_RECORDING)
        async def failing_task(input: PipelineInput, ctx) -> str:
            raise ValueError("boom")

        with (
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.update_dag_zulip_message",
                new_callable=AsyncMock,
            ) as mock_update,
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.set_workflow_error_status",
                new_callable=AsyncMock,
            ),
        ):
            with pytest.raises(ValueError, match="boom"):
                await failing_task(input_data, mock_ctx)
            mock_update.assert_called_once_with(
                "tid-1", "wfr-123", error_message="get_recording failed: boom"
            )

    async def test_dag_failure_doesnt_affect_task(self):
        """DAG update failure should not prevent task from succeeding."""
        from reflector.hatchet.constants import TaskName
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            PipelineInput,
            with_error_handling,
        )

        mock_ctx = MagicMock()
        mock_ctx.workflow_run_id = "wfr-123"

        input_data = PipelineInput(
            recording_id="rec-1",
            tracks=[{"s3_key": "k"}],
            bucket_name="bucket",
            transcript_id="tid-1",
        )

        @with_error_handling(TaskName.GET_RECORDING)
        async def ok_task(input: PipelineInput, ctx) -> str:
            return "ok"

        with patch(
            "reflector.hatchet.workflows.daily_multitrack_pipeline.update_dag_zulip_message",
            new_callable=AsyncMock,
            side_effect=Exception("zulip exploded"),
        ):
            result = await ok_task(input_data, mock_ctx)
            assert result == "ok"
