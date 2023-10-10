"""
Plugin manager
==============

This module allow plugins to be registered and be called at
specific place in the code.
"""

import importlib
from enum import StrEnum

from reflector.logger import logger
from reflector.settings import settings

logger = logger.bind(module="plugins.manager")


class Plugin:
    async def load(self):
        pass

    async def unload(self):
        pass

    async def hook(self, name, *args, **kwargs):
        pass


class PluginManager:
    _registry = {}
    _instances = []

    Hook = StrEnum("Hook", ["TRANSCRIPT_TOPIC"])

    @classmethod
    def register(cls, name, klass):
        cls._registry[name] = klass

    @classmethod
    async def load_plugins(cls):
        logger.info("Loading plugins")
        # load plugins
        for name in settings.PLUGINS:
            module_name = f"reflector.plugins.{name}"
            logger.info(f"Loading plugin {module_name}")
            importlib.import_module(module_name)

        # call load plugin on each
        for plugin in cls._registry.values():
            instance = plugin()
            cls._instances.append(instance)
            await instance.load()

    @classmethod
    async def unload_plugins(cls):
        logger.info("Unloading plugins")
        for instance in cls._instances:
            await instance.unload()

    @classmethod
    async def hook(cls, name, **kwargs):
        for instance in cls._instances:
            await instance.hook(name, **kwargs)
