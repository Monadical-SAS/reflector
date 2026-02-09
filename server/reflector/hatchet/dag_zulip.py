"""
Hatchet DAG Status -> Zulip Live Updates.

Posts/updates/deletes a Zulip message showing the Hatchet workflow DAG status.
All functions are fire-and-forget (catch + warning log on failure).

Note: Uses deferred imports throughout for fork-safety,
consistent with the pipeline pattern in daily_multitrack_pipeline.py.
"""

from reflector.logger import logger
from reflector.settings import settings


def _dag_zulip_enabled() -> bool:
    return bool(
        settings.ZULIP_REALM and settings.ZULIP_DAG_STREAM and settings.ZULIP_DAG_TOPIC
    )


async def create_dag_zulip_message(transcript_id: str, workflow_run_id: str) -> None:
    """Post initial DAG status to Zulip. Called at dispatch time (normal DB context)."""
    if not _dag_zulip_enabled():
        return

    try:
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415
        from reflector.hatchet.client import HatchetClientManager  # noqa: PLC0415
        from reflector.tools.render_hatchet_run import (  # noqa: PLC0415
            render_run_detail,
        )
        from reflector.zulip import send_message_to_zulip  # noqa: PLC0415

        client = HatchetClientManager.get_client()
        details = await client.runs.aio_get(workflow_run_id)
        content = render_run_detail(details)

        response = await send_message_to_zulip(
            settings.ZULIP_DAG_STREAM, settings.ZULIP_DAG_TOPIC, content
        )
        message_id = response.get("id")

        if message_id:
            transcript = await transcripts_controller.get_by_id(transcript_id)
            if transcript:
                await transcripts_controller.update(
                    transcript, {"zulip_message_id": message_id}
                )
    except Exception:
        logger.warning(
            "[DAG Zulip] Failed to create DAG message",
            transcript_id=transcript_id,
            workflow_run_id=workflow_run_id,
            exc_info=True,
        )


async def update_dag_zulip_message(
    transcript_id: str,
    workflow_run_id: str,
    error_message: str | None = None,
) -> None:
    """Update existing DAG status in Zulip. Called from Hatchet worker (forked).

    Args:
        error_message: If set, appended as an error banner to the rendered DAG.
    """
    if not _dag_zulip_enabled():
        return

    try:
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415
        from reflector.hatchet.client import HatchetClientManager  # noqa: PLC0415
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (  # noqa: PLC0415
            fresh_db_connection,
        )
        from reflector.tools.render_hatchet_run import (  # noqa: PLC0415
            render_run_detail,
        )
        from reflector.zulip import update_zulip_message  # noqa: PLC0415

        async with fresh_db_connection():
            transcript = await transcripts_controller.get_by_id(transcript_id)
            if not transcript or not transcript.zulip_message_id:
                return

            client = HatchetClientManager.get_client()
            details = await client.runs.aio_get(workflow_run_id)
            content = render_run_detail(details)

            if error_message:
                content += f"\n\n:cross_mark: **{error_message}**"

            await update_zulip_message(
                transcript.zulip_message_id,
                settings.ZULIP_DAG_STREAM,
                settings.ZULIP_DAG_TOPIC,
                content,
            )
    except Exception:
        logger.warning(
            "[DAG Zulip] Failed to update DAG message",
            transcript_id=transcript_id,
            workflow_run_id=workflow_run_id,
            exc_info=True,
        )


async def delete_dag_zulip_message(transcript_id: str) -> None:
    """Delete DAG Zulip message and clear zulip_message_id.

    Called from post_zulip task (already inside fresh_db_connection).
    Swallows InvalidMessageError (message already deleted).
    """
    if not _dag_zulip_enabled():
        return

    try:
        from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415
        from reflector.zulip import (  # noqa: PLC0415
            InvalidMessageError,
            delete_zulip_message,
        )

        transcript = await transcripts_controller.get_by_id(transcript_id)
        if not transcript or not transcript.zulip_message_id:
            return

        try:
            await delete_zulip_message(transcript.zulip_message_id)
        except InvalidMessageError:
            logger.warning(
                "[DAG Zulip] Message already deleted",
                transcript_id=transcript_id,
                zulip_message_id=transcript.zulip_message_id,
            )

        await transcripts_controller.update(transcript, {"zulip_message_id": None})
    except Exception:
        logger.warning(
            "[DAG Zulip] Failed to delete DAG message",
            transcript_id=transcript_id,
            exc_info=True,
        )
