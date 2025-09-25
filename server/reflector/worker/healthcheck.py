import httpx
import structlog

from reflector.settings import settings
from reflector.worker.app import taskiq_broker

logger = structlog.get_logger(__name__)


@taskiq_broker.task
def healthcheck_ping():
    url = settings.HEALTHCHECK_URL
    if not url:
        return
    try:
        print("pinging healthcheck url", url)
        httpx.get(url, timeout=10)
    except Exception as e:
        logger.error("healthcheck_ping", error=str(e))
