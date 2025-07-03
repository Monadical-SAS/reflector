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
        retry_logger = kwargs.pop("logger", logger)

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
                retry_logger.exception(e)
                status_code = e.response.status_code
                
                # Log detailed error information including response body
                try:
                    response_text = e.response.text
                    response_headers = dict(e.response.headers)
                    retry_logger.error(
                        f"HTTP {status_code} error for {e.request.method} {e.request.url}\n"
                        f"Response headers: {response_headers}\n"
                        f"Response body: {response_text}"
                    )
                    
                    # Special handling for 500 errors - log request body and generate curl
                    if status_code == 500:
                        try:
                            request_body = ""
                            if hasattr(e.request, 'content') and e.request.content:
                                request_body = e.request.content.decode('utf-8') if isinstance(e.request.content, bytes) else str(e.request.content)
                            
                            # Generate curl command for manual retry
                            curl_headers = ""
                            if hasattr(e.request, 'headers') and e.request.headers:
                                for header_name, header_value in e.request.headers.items():
                                    curl_headers += f" -H '{header_name}: {header_value}'"
                            
                            curl_data = ""
                            if request_body:
                                # Escape single quotes in request body for curl
                                escaped_body = request_body.replace("'", "'\"'\"'")
                                curl_data = f" -d '{escaped_body}'"
                            
                            curl_command = f"curl --http1.1 -X {e.request.method}{curl_headers}{curl_data} '{e.request.url}'"
                            
                            retry_logger.error(
                                f"HTTP 500 error details:\n"
                                f"Request body: {request_body}\n"
                                f"Manual retry curl command:\n{curl_command}"
                            )
                        except Exception as curl_error:
                            retry_logger.warning(f"Failed to generate curl command: {curl_error}")
                            
                except Exception as log_error:
                    retry_logger.warning(f"Failed to log detailed error info: {log_error}")
                    retry_logger.debug(f"HTTP status {status_code} - {e}")
                
                if status_code in retry_httpx_status_stop:
                    message = f"HTTP status {status_code} is in retry_httpx_status_stop"
                    raise RetryHTTPException(message) from e
            except retry_ignore_exc_types as e:
                retry_logger.exception(e)
                last_exception = e

            retry_logger.debug(
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
