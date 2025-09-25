import os

import structlog
from taskiq import InMemoryBroker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from reflector.settings import settings

logger = structlog.get_logger(__name__)

env = os.environ.get("ENVIRONMENT")
if env and env == "pytest":
    taskiq_broker = InMemoryBroker(await_inplace=True)
else:
    result_backend = RedisAsyncResultBackend(
        redis_url=settings.CELERY_BROKER_URL,
        result_ex_time=86400,
    )
    taskiq_broker = RedisStreamBroker(
        url=settings.CELERY_BROKER_URL,
    ).with_result_backend(result_backend)
