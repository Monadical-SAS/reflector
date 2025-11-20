"""User table for storing Authentik user information."""

from datetime import datetime, timezone

import sqlalchemy
from pydantic import BaseModel, Field

from reflector.db import get_database, metadata
from reflector.utils import generate_uuid4
from reflector.utils.string import NonEmptyString

users = sqlalchemy.Table(
    "user",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("uid", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("email", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Index("idx_user_uid", "uid", unique=True),
    sqlalchemy.Index("idx_user_email", "email", unique=False),
)


class User(BaseModel):
    id: NonEmptyString = Field(default_factory=generate_uuid4)
    uid: NonEmptyString  # Authentik user UUID (from JWT 'sub')
    email: NonEmptyString
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserController:
    @staticmethod
    async def get_by_id(user_id: NonEmptyString) -> User | None:
        """Get user by internal ID."""
        query = users.select().where(users.c.id == user_id)
        result = await get_database().fetch_one(query)
        return User(**result) if result else None

    @staticmethod
    async def get_by_uid(uid: NonEmptyString) -> User | None:
        """Get user by Authentik UID."""
        query = users.select().where(users.c.uid == uid)
        result = await get_database().fetch_one(query)
        return User(**result) if result else None

    @staticmethod
    async def get_by_email(email: NonEmptyString) -> User | None:
        """Get user by email."""
        query = users.select().where(users.c.email == email)
        result = await get_database().fetch_one(query)
        return User(**result) if result else None

    @staticmethod
    async def create_or_update(
        id: NonEmptyString, uid: NonEmptyString, email: NonEmptyString
    ) -> User:
        """Create or update user from Authentik data."""
        existing = await UserController.get_by_uid(uid)
        now = datetime.now(timezone.utc)

        if existing:
            query = (
                users.update()
                .where(users.c.uid == uid)
                .values(email=email, updated_at=now)
            )
            await get_database().execute(query)
            return User(
                id=existing.id,
                uid=uid,
                email=email,
                created_at=existing.created_at,
                updated_at=now,
            )
        else:
            user = User(id=id, uid=uid, email=email, created_at=now, updated_at=now)
            query = users.insert().values(**user.model_dump())
            await get_database().execute(query)
            return user

    @staticmethod
    async def list_all() -> list[User]:
        """List all users."""
        query = users.select().order_by(users.c.created_at.desc())
        results = await get_database().fetch_all(query)
        return [User(**r) for r in results]


user_controller = UserController()
