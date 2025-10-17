import hmac
import secrets
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal, Union

import sqlalchemy
from pydantic import BaseModel, Field

from reflector.db import get_database, metadata
from reflector.settings import settings
from reflector.utils import generate_uuid4
from reflector.utils.string import NonEmptyString

user_tokens = sqlalchemy.Table(
    "user_token",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("token_hash", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Index("idx_user_token_hash", "token_hash", unique=True),
    sqlalchemy.Index("idx_user_token_user_id", "user_id"),
)


class UserToken(BaseModel):
    id: NonEmptyString = Field(default_factory=generate_uuid4)
    user_id: NonEmptyString
    token_hash: NonEmptyString
    name: NonEmptyString | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserTokenController:
    @staticmethod
    def generate_token() -> NonEmptyString:
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_token(token: NonEmptyString) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode(), token.encode(), digestmod=sha256
        ).hexdigest()

    @classmethod
    async def create_token(
        cls,
        user_id: NonEmptyString,
        name: NonEmptyString | None = None,
    ) -> tuple[UserToken, NonEmptyString]:
        """Returns (UserToken, plaintext_token). Plaintext shown only once."""
        plaintext = cls.generate_token()
        token = UserToken(
            user_id=user_id,
            token_hash=cls.hash_token(plaintext),
            name=name,
        )
        query = user_tokens.insert().values(**token.model_dump())
        await get_database().execute(query)
        return token, plaintext

    @classmethod
    async def verify_token(cls, plaintext_token: NonEmptyString) -> UserToken | None:
        token_hash = cls.hash_token(plaintext_token)
        query = user_tokens.select().where(
            user_tokens.c.token_hash == token_hash,
        )
        result = await get_database().fetch_one(query)
        return UserToken(**result) if result else None

    @staticmethod
    async def list_by_user_id(user_id: NonEmptyString) -> list[UserToken]:
        query = (
            user_tokens.select()
            .where(user_tokens.c.user_id == user_id)
            .order_by(user_tokens.c.created_at.desc())
        )
        results = await get_database().fetch_all(query)
        return [UserToken(**r) for r in results]

    @staticmethod
    async def delete_token(
        token_id: NonEmptyString, user_id: NonEmptyString
    ) -> Union[None, Literal["not-yours", "not-here"]]:
        existing = await get_database().fetch_one(
            user_tokens.select().where(user_tokens.c.id == token_id)
        )

        if not existing:
            return "not-here"

        if existing["user_id"] != user_id:
            return "not-yours"

        query = user_tokens.delete().where(user_tokens.c.id == token_id)
        await get_database().execute(query)
        return None


user_tokens_controller = UserTokenController()
