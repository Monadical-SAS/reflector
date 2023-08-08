from reflector.logger import logger
import asyncio


def retry(fn):
    async def decorated(*args, **kwargs):
        retry_max = kwargs.pop("retry_max", 5)
        retry_delay = kwargs.pop("retry_delay", 2)
        retry_ignore_exc_types = kwargs.pop("retry_ignore_exc_types", ())
        result = None
        attempt = 0
        last_exception = None
        for attempt in range(retry_max):
            try:
                result = await fn(*args, **kwargs)
                if result:
                    return result
            except retry_ignore_exc_types as e:
                last_exception = e
            logger.debug(
                f"Retrying {fn} - in {retry_delay} seconds "
                f"- attempt {attempt + 1}/{retry_max}"
            )
            await asyncio.sleep(retry_delay)
        if last_exception is not None:
            raise type(last_exception) from last_exception
        return result

    return decorated
