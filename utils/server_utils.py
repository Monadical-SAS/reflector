import asyncio
from functools import partial

def run_in_executor(func, *args, executor=None, **kwargs):
    callback = partial(func, *args, **kwargs)
    loop = asyncio.get_event_loop()
    return asyncio.get_event_loop().run_in_executor(executor, callback)
