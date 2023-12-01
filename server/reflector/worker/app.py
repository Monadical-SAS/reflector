import structlog
from celery import Celery
from reflector.settings import settings

logger = structlog.get_logger(__name__)
app = Celery(__name__)
app.conf.broker_url = settings.CELERY_BROKER_URL
app.conf.result_backend = settings.CELERY_RESULT_BACKEND
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks(
    [
        "reflector.pipelines.main_live_pipeline",
        "reflector.worker.healthcheck",
    ]
)

# crontab
app.conf.beat_schedule = {}

if settings.HEALTHCHECK_URL:
    app.conf.beat_schedule["healthcheck_ping"] = {
        "task": "reflector.worker.healthcheck.healthcheck_ping",
        "schedule": 60.0 * 10,
    }
    logger.info("Healthcheck enabled", url=settings.HEALTHCHECK_URL)
else:
    logger.warning("Healthcheck disabled, no url configured")
