from reflector.logger import logger
from time import monotonic
from httpx import HTTPStatusError, Response
from random import random
import asyncio


class RetryException(Exception):
    pass


class RetryTimeoutException(RetryException):
    pass


class RetryHTTPException(RetryException):
    pass


def retry(fn):
    async def decorated(*args, **kwargs):
        retry_attempts = kwargs.pop("retry_attempts", None)
        retry_timeout = kwargs.pop("retry_timeout", 60)
        retry_backoff_interval = kwargs.pop("retry_backoff_interval", 0.1)
        retry_jitter = kwargs.pop("retry_jitter", 0.1)
        retry_backoff_max = kwargs.pop("retry_backoff_max", 3)
        retry_httpx_status_stop = kwargs.pop(
            "retry_httpx_status_stop",
            (
                401,  # auth issue
                404,  # not found
                413,  # payload too large
                418,  # teapot
            ),
        )
        retry_ignore_exc_types = kwargs.pop("retry_ignore_exc_types", (Exception,))

        result = None
        last_exception = None
        attempts = 0
        start = monotonic()
        fn_name = fn.__name__

        # goal: retry until timeout
        while True:
            if monotonic() - start > retry_timeout:
                raise RetryTimeoutException()

            jitter = random() * retry_jitter
            retry_backoff_interval = min(
                retry_backoff_interval * 2 + jitter, retry_backoff_max
            )

            try:
                result = await fn(*args, **kwargs)
                if isinstance(result, Response):
                    result.raise_for_status()
                if result:
                    return result
            except HTTPStatusError as e:
                status_code = e.response.status_code
                logger.debug(f"HTTP status {status_code} - {e}")
                if status_code in retry_httpx_status_stop:
                    message = f"HTTP status {status_code} is in retry_httpx_status_stop"
                    raise RetryHTTPException(message) from e
            except retry_ignore_exc_types as e:
                last_exception = e

            logger.debug(
                f"Retrying {fn_name} - in {retry_backoff_interval:.1f}s "
                f"({monotonic() - start:.1f}s / {retry_timeout:.1f}s)"
            )
            attempts += 1

            if retry_attempts is not None and attempts >= retry_attempts:
                raise RetryException(f"Retry attempts exceeded: {retry_attempts}")

            await asyncio.sleep(retry_backoff_interval)

        if last_exception is not None:
            raise type(last_exception) from last_exception
        return result

    return decorated
