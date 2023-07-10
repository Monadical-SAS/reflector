import asyncio
import contextlib
from functools import partial
from threading import Lock
from typing import ContextManager, Generic, TypeVar


def run_in_executor(func, *args, executor=None, **kwargs):
    callback = partial(func, *args, **kwargs)
    loop = asyncio.get_event_loop()
    return asyncio.get_event_loop().run_in_executor(executor, callback)


T = TypeVar("T")


class Mutex(Generic[T]):
    def __init__(self, value: T):
        self.__value = value
        self.__lock = Lock()

    @contextlib.contextmanager
    def lock(self) -> ContextManager[T]:
        self.__lock.acquire()
        try:
            yield self.__value
        finally:
            self.__lock.release()
