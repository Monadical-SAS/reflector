"""
TaskIQ broker configuration for Reflector.

This module provides a production-ready TaskIQ broker configuration that handles
both test and production environments correctly. It includes retry middleware
for 1:1 parity with Celery and proper logging setup.
"""

import os

import structlog
from taskiq import InMemoryBroker
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from reflector.settings import settings

logger = structlog.get_logger(__name__)


def create_taskiq_broker():
    """
    Create and configure the TaskIQ broker based on environment.

    Returns:
        Configured TaskIQ broker instance with appropriate backend and middleware.
    """
    env = os.environ.get("ENVIRONMENT")

    if env == "pytest":
        # Test environment: Use InMemoryBroker with immediate execution
        logger.info("Configuring TaskIQ InMemoryBroker for test environment")
        broker = InMemoryBroker(await_inplace=True)

    else:
        # Production environment: Use Redis broker with result backend
        logger.info(
            "Configuring TaskIQ RedisStreamBroker for production environment",
            redis_url=settings.CELERY_BROKER_URL,
        )

        # Configure Redis result backend
        result_backend = RedisAsyncResultBackend(
            redis_url=settings.CELERY_BROKER_URL,
            result_ex_time=86400,  # Results expire after 24 hours
        )

        # Configure Redis stream broker
        broker = RedisStreamBroker(
            url=settings.CELERY_BROKER_URL,
            stream_name="taskiq:stream",  # Custom stream name for clarity
            consumer_group="taskiq:workers",  # Consumer group for load balancing
        ).with_result_backend(result_backend)

    # Add retry middleware for production parity with Celery
    # This provides automatic retries on task failures
    retry_middleware = SimpleRetryMiddleware(
        default_retry_count=3,  # Match Celery's default retry behavior
    )
    broker.add_middlewares(retry_middleware)

    logger.info(
        "TaskIQ broker configured successfully",
        broker_type=type(broker).__name__,
        has_result_backend=hasattr(broker, "_result_backend"),
        middleware_count=len(broker.middlewares),
    )

    return broker


# Create the global broker instance
taskiq_broker = create_taskiq_broker()

# Export the broker for use in task definitions
__all__ = ["taskiq_broker"]
