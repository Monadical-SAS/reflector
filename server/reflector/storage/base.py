import importlib
from typing import BinaryIO, Union

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

    # Credential properties for API passthrough
    @property
    def bucket_name(self) -> str:
        """Default bucket name for this storage instance."""
        raise NotImplementedError

    @property
    def region(self) -> str:
        """AWS region for this storage instance."""
        raise NotImplementedError

    @property
    def access_key_id(self) -> str | None:
        """AWS access key ID (None for role-based auth). Prefer key_credentials property."""
        return None

    @property
    def secret_access_key(self) -> str | None:
        """AWS secret access key (None for role-based auth). Prefer key_credentials property."""
        return None

    @property
    def role_arn(self) -> str | None:
        """AWS IAM role ARN for role-based auth (None for key-based auth). Prefer role_credential property."""
        return None

    @property
    def key_credentials(self) -> tuple[str, str]:
        """
        Get (access_key_id, secret_access_key) for key-based auth.
        Raises ValueError if storage uses IAM role instead.
        """
        raise NotImplementedError

    @property
    def role_credential(self) -> str:
        """
        Get IAM role ARN for role-based auth.
        Raises ValueError if storage uses access keys instead.
        """
        raise NotImplementedError

    async def put_file(
        self, filename: str, data: Union[bytes, BinaryIO], bucket: str | None = None
    ) -> FileResult:
        """Upload data. bucket: override instance default if provided."""
        return await self._put_file(filename, data, bucket)

    async def _put_file(
        self, filename: str, data: Union[bytes, BinaryIO], bucket: str | None = None
    ) -> FileResult:
        raise NotImplementedError

    async def delete_file(self, filename: str, bucket: str | None = None):
        """Delete file. bucket: override instance default if provided."""
        return await self._delete_file(filename, bucket)

    async def _delete_file(self, filename: str, bucket: str | None = None):
        raise NotImplementedError

    async def get_file_url(
        self,
        filename: str,
        operation: str = "get_object",
        expires_in: int = 3600,
        bucket: str | None = None,
    ) -> str:
        """Generate presigned URL. bucket: override instance default if provided."""
        return await self._get_file_url(filename, operation, expires_in, bucket)

    async def _get_file_url(
        self,
        filename: str,
        operation: str = "get_object",
        expires_in: int = 3600,
        bucket: str | None = None,
    ) -> str:
        raise NotImplementedError

    async def get_file(self, filename: str, bucket: str | None = None):
        """Download file. bucket: override instance default if provided."""
        return await self._get_file(filename, bucket)

    async def _get_file(self, filename: str, bucket: str | None = None):
        raise NotImplementedError

    async def list_objects(
        self, prefix: str = "", bucket: str | None = None
    ) -> list[str]:
        """List object keys. bucket: override instance default if provided."""
        return await self._list_objects(prefix, bucket)

    async def _list_objects(
        self, prefix: str = "", bucket: str | None = None
    ) -> list[str]:
        raise NotImplementedError
