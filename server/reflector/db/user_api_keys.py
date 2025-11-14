import hmac
import secrets
from datetime import datetime, timezone
from hashlib import sha256

import sqlalchemy
from pydantic import BaseModel, Field

from reflector.db import get_database, metadata
from reflector.settings import settings
from reflector.utils import generate_uuid4
from reflector.utils.string import NonEmptyString

user_api_keys = sqlalchemy.Table(
    "user_api_key",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("key_hash", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Index("idx_user_api_key_hash", "key_hash", unique=True),
    sqlalchemy.Index("idx_user_api_key_user_id", "user_id"),
)


class UserApiKey(BaseModel):
    id: NonEmptyString = Field(default_factory=generate_uuid4)
    user_id: NonEmptyString
    key_hash: NonEmptyString
    name: NonEmptyString | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserApiKeyController:
    @staticmethod
    def generate_key() -> NonEmptyString:
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_key(key: NonEmptyString) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode(), key.encode(), digestmod=sha256
        ).hexdigest()

    @classmethod
    async def create_key(
        cls,
        user_id: NonEmptyString,
        name: NonEmptyString | None = None,
    ) -> tuple[UserApiKey, NonEmptyString]:
        plaintext = cls.generate_key()
        api_key = UserApiKey(
            user_id=user_id,
            key_hash=cls.hash_key(plaintext),
            name=name,
        )
        query = user_api_keys.insert().values(**api_key.model_dump())
        await get_database().execute(query)
        return api_key, plaintext

    @classmethod
    async def verify_key(cls, plaintext_key: NonEmptyString) -> UserApiKey | None:
        key_hash = cls.hash_key(plaintext_key)
        query = user_api_keys.select().where(
            user_api_keys.c.key_hash == key_hash,
        )
        result = await get_database().fetch_one(query)
        return UserApiKey(**result) if result else None

    @staticmethod
    async def list_by_user_id(user_id: NonEmptyString) -> list[UserApiKey]:
        query = (
            user_api_keys.select()
            .where(user_api_keys.c.user_id == user_id)
            .order_by(user_api_keys.c.created_at.desc())
        )
        results = await get_database().fetch_all(query)
        return [UserApiKey(**r) for r in results]

    @staticmethod
    async def delete_key(key_id: NonEmptyString, user_id: NonEmptyString) -> bool:
        query = user_api_keys.delete().where(
            (user_api_keys.c.id == key_id) & (user_api_keys.c.user_id == user_id)
        )
        result = await get_database().execute(query)
        # asyncpg returns None for DELETE, consider it success if no exception
        return result is None or result > 0


user_api_keys_controller = UserApiKeyController()
