import asyncio
import pytest
import httpx
from reflector.utils.retry import (
    retry,
    RetryTimeoutException,
    RetryHTTPException,
    RetryException,
)


@pytest.mark.asyncio
async def test_retry_redirect(httpx_mock):
    async def custom_response(request: httpx.Request):
        if request.url.path == "/hello":
            await asyncio.sleep(1)
            return httpx.Response(
                status_code=303, headers={"location": "https://test_url/redirected"}
            )
        elif request.url.path == "/redirected":
            return httpx.Response(status_code=200, json={"hello": "world"})
        else:
            raise Exception("Unexpected path")

    httpx_mock.add_callback(custom_response)
    async with httpx.AsyncClient() as client:
        # timeout should not triggered, as it will end up ok
        # even though the first request is a 303 and took more that 0.5
        resp = await retry(client.get)(
            "https://test_url/hello",
            retry_timeout=0.5,
            follow_redirects=True,
        )
        assert resp.json() == {"hello": "world"}


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
