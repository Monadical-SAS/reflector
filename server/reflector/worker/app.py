import celery
import structlog
from celery import Celery
from celery.schedules import crontab
from reflector.settings import settings

logger = structlog.get_logger(__name__)
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
    }

    if settings.HEALTHCHECK_URL:
        app.conf.beat_schedule["healthcheck_ping"] = {
            "task": "reflector.worker.healthcheck.healthcheck_ping",
            "schedule": 60.0 * 10,
        }
        logger.info("Healthcheck enabled", url=settings.HEALTHCHECK_URL)
    else:
        logger.warning("Healthcheck disabled, no url configured")
