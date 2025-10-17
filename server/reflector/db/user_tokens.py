import hmac
import secrets
from datetime import datetime, timezone
from hashlib import sha256

import sqlalchemy
from pydantic import BaseModel, Field

from reflector.db import get_database, metadata
from reflector.settings import settings
from reflector.utils import generate_uuid4

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
    id: str = Field(default_factory=generate_uuid4)
    user_id: str
    token_hash: str
    name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserTokenController:
    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_token(token: str) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode(), token.encode(), digestmod=sha256
        ).hexdigest()

    async def create_token(
        self,
        user_id: str,
        name: str | None = None,
    ) -> tuple[UserToken, str]:
        """Returns (UserToken, plaintext_token). Plaintext shown only once."""
        plaintext = self.generate_token()
        token = UserToken(
            user_id=user_id,
            token_hash=self.hash_token(plaintext),
            name=name,
        )
        query = user_tokens.insert().values(**token.model_dump())
        await get_database().execute(query)
        return token, plaintext

    async def verify_token(self, plaintext_token: str) -> UserToken | None:
        token_hash = self.hash_token(plaintext_token)
        query = user_tokens.select().where(
            user_tokens.c.token_hash == token_hash,
        )
        result = await get_database().fetch_one(query)
        return UserToken(**result) if result else None

    async def get_by_user_id(self, user_id: str) -> list[UserToken]:
        query = (
            user_tokens.select()
            .where(user_tokens.c.user_id == user_id)
            .order_by(user_tokens.c.created_at.desc())
        )
        results = await get_database().fetch_all(query)
        return [UserToken(**r) for r in results]

    async def delete_token(self, token_id: str, user_id: str) -> bool:
        check = user_tokens.select().where(user_tokens.c.id == token_id)
        existing = await get_database().fetch_one(check)

        if not existing:
            return False  # Token doesn't exist - idempotent

        if existing["user_id"] != user_id:
            raise ValueError(f"Token {token_id} belongs to another user")

        query = user_tokens.delete().where(user_tokens.c.id == token_id)
        await get_database().execute(query)
        return True  # If we get here, the token was deleted


user_tokens_controller = UserTokenController()
