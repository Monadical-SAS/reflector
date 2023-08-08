import pytest
import httpx
from reflector.utils.retry import (
    retry,
    RetryTimeoutException,
    RetryHTTPException,
    RetryException,
)


@pytest.mark.asyncio
async def test_retry_httpx(httpx_mock):
    # this code should be force a retry
    httpx_mock.add_response(status_code=500)
    async with httpx.AsyncClient() as client:
        with pytest.raises(RetryTimeoutException):
            await retry(client.get)("https://test_url", retry_timeout=0.1)

    # but if we add it in the retry_httpx_status_stop, it should not retry
    async with httpx.AsyncClient() as client:
        with pytest.raises(RetryHTTPException):
            await retry(client.get)(
                "https://test_url", retry_timeout=5, retry_httpx_status_stop=[500]
            )


@pytest.mark.asyncio
async def test_retry_normal():
    left = 3

    async def retry_before_success():
        nonlocal left
        if left > 0:
            left -= 1
            raise Exception("test")
        return True

    result = await retry(retry_before_success)()
    assert result is True
    assert left == 0


@pytest.mark.asyncio
async def test_retry_max_attempts():
    left = 3

    async def retry_before_success():
        nonlocal left
        if left > 0:
            left -= 1
            raise Exception("test")
        return True

    with pytest.raises(RetryException):
        await retry(retry_before_success)(retry_attempts=2)
