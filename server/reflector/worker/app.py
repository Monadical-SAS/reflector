import celery
import structlog
from celery import Celery
from celery.schedules import crontab

from reflector.settings import settings

logger = structlog.get_logger(__name__)

# Polling intervals (seconds)
POLL_DAILY_RECORDINGS_INTERVAL_SEC = 15.0  # Dev: 15s, Prod: 180s
if celery.current_app.main != "default":
    logger.info(f"Celery already configured ({celery.current_app})")
    app = celery.current_app
else:
    app = Celery(__name__)
    app.conf.broker_url = settings.CELERY_BROKER_URL
    app.conf.result_backend = settings.CELERY_RESULT_BACKEND
    app.conf.broker_connection_retry_on_startup = True
    app.autodiscover_tasks(
        [
            "reflector.pipelines.main_live_pipeline",
            "reflector.worker.healthcheck",
            "reflector.worker.process",
            "reflector.worker.cleanup",
            "reflector.worker.ics_sync",
        ]
    )

    # crontab
    app.conf.beat_schedule = {
        "process_messages": {
            "task": "reflector.worker.process.process_messages",
            "schedule": float(settings.SQS_POLLING_TIMEOUT_SECONDS),
        },
        "process_meetings": {
            "task": "reflector.worker.process.process_meetings",
            "schedule": float(settings.SQS_POLLING_TIMEOUT_SECONDS),
        },
        "reprocess_failed_recordings": {
            "task": "reflector.worker.process.reprocess_failed_recordings",
            "schedule": crontab(hour=5, minute=0),  # Midnight EST
        },
        "reprocess_failed_daily_recordings": {
            "task": "reflector.worker.process.reprocess_failed_daily_recordings",
            "schedule": crontab(hour=5, minute=0),  # Midnight EST
        },
        "poll_daily_recordings": {
            "task": "reflector.worker.process.poll_daily_recordings",
            "schedule": POLL_DAILY_RECORDINGS_INTERVAL_SEC,
        },
        "trigger_daily_reconciliation": {
            "task": "reflector.worker.process.trigger_daily_reconciliation",
            "schedule": 30.0,  # Every 30 seconds (queues poll tasks for all active meetings)
        },
        "sync_all_ics_calendars": {
            "task": "reflector.worker.ics_sync.sync_all_ics_calendars",
            "schedule": 60.0,  # Run every minute to check which rooms need sync
        },
        "create_upcoming_meetings": {
            "task": "reflector.worker.ics_sync.create_upcoming_meetings",
            "schedule": 30.0,  # Run every 30 seconds to create upcoming meetings
        },
    }

    if settings.PUBLIC_MODE:
        app.conf.beat_schedule["cleanup_old_public_data"] = {
            "task": "reflector.worker.cleanup.cleanup_old_public_data_task",
            "schedule": crontab(hour=3, minute=0),
        }
        logger.info(
            "Public mode cleanup enabled",
            retention_days=settings.PUBLIC_DATA_RETENTION_DAYS,
        )

    if settings.HEALTHCHECK_URL:
        app.conf.beat_schedule["healthcheck_ping"] = {
            "task": "reflector.worker.healthcheck.healthcheck_ping",
            "schedule": 60.0 * 10,
        }
        logger.info("Healthcheck enabled", url=settings.HEALTHCHECK_URL)
    else:
        logger.warning("Healthcheck disabled, no url configured")
