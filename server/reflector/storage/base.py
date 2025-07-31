import importlib

from pydantic import BaseModel

from reflector.settings import settings


class FileResult(BaseModel):
    filename: str
    url: str


class Storage:
    _registry = {}
    CONFIG_SETTINGS = []

    @classmethod
    def register(cls, name, kclass):
        cls._registry[name] = kclass

    @classmethod
    def get_instance(cls, name: str, settings_prefix: str = ""):
        if name not in cls._registry:
            module_name = f"reflector.storage.storage_{name}"
            importlib.import_module(module_name)

        # gather specific configuration for the processor
        # search `TRANSCRIPT_BACKEND_XXX_YYY`, push to constructor as `backend_xxx_yyy`
        config = {}
        name_upper = name.upper()
        config_prefix = f"{settings_prefix}{name_upper}_"
        for key, value in settings:
            if key.startswith(config_prefix):
                config_name = key[len(settings_prefix) :].lower()
                config[config_name] = value

        return cls._registry[name](**config)

    async def put_file(self, filename: str, data: bytes) -> FileResult:
        return await self._put_file(filename, data)

    async def _put_file(self, filename: str, data: bytes) -> FileResult:
        raise NotImplementedError

    async def delete_file(self, filename: str):
        return await self._delete_file(filename)

    async def _delete_file(self, filename: str):
        raise NotImplementedError

    async def get_file_url(self, filename: str) -> str:
        return await self._get_file_url(filename)

    async def _get_file_url(self, filename: str) -> str:
        raise NotImplementedError

    async def get_file(self, filename: str):
        return await self._get_file(filename)

    async def _get_file(self, filename: str):
        raise NotImplementedError
