"""
Utility file for server side asynchronous task running and config objects
"""

import asyncio
import configparser
import contextlib
from functools import partial
from threading import Lock
from typing import ContextManager, Generic, TypeVar


class ReflectorConfig:
    """
    Create a single config object to share across the project
    """
    __config = None
    __secrets = None

    @staticmethod
    def get_config():
        """
        Load the configurations from the local config.ini file
        :return:
        """
        if ReflectorConfig.__config is None:
            ReflectorConfig.__config = configparser.ConfigParser()
            ReflectorConfig.__config.read('utils/config.ini')
        return ReflectorConfig.__config

    @staticmethod
    def get_secrets():
        """
        Load the configurations from the local config.ini file
        :return:
        """
        if ReflectorConfig.__secrets is None:
            ReflectorConfig.__secrets = configparser.ConfigParser()
            ReflectorConfig.__secrets.read('utils/secrets.ini')
        return ReflectorConfig.__secrets


CONFIG = ReflectorConfig.get_config()
SECRETS = ReflectorConfig.get_secrets()


def run_in_executor(func, *args, executor=None, **kwargs):
    """
    Run the function in an executor, unblocking the main loop
    :param func: Function to be run in executor
    :param args: function parameters
    :param executor: executor instance [Thread | Process]
    :param kwargs: Additional parameters
    :return: Future of function result upon completion
    """
    callback = partial(func, *args, **kwargs)
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, callback)


# Genetic type template
T = TypeVar("T")


class Mutex(Generic[T]):
    """
    Mutex class to implement lock/release of a shared
    protected variable
    """

    def __init__(self, value: T):
        """
        Create an instance of Mutex wrapper for the given resource
        :param value: Shared resources to be thread protected
        """
        self.__value = value
        self.__lock = Lock()

    @contextlib.contextmanager
    def lock(self) -> ContextManager[T]:
        """
        Lock the resource with a mutex to be used within a context block
        The lock is automatically released on context exit
        :return: Shared resource
        """
        self.__lock.acquire()
        try:
            yield self.__value
        finally:
            self.__lock.release()
