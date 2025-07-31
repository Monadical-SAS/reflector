import httpx
import structlog
from celery import shared_task

from reflector.settings import settings

logger = structlog.get_logger(__name__)


@shared_task
def healthcheck_ping():
    url = settings.HEALTHCHECK_URL
    if not url:
        return
    try:
        print("pinging healthcheck url", url)
        httpx.get(url, timeout=10)
    except Exception as e:
        logger.error("healthcheck_ping", error=str(e))
