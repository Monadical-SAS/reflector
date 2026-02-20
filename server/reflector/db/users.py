"""User table for storing user information."""

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
    sqlalchemy.Column("email", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("authentik_uid", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("password_hash", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Index("idx_user_authentik_uid", "authentik_uid", unique=True),
    sqlalchemy.Index("idx_user_email", "email", unique=False),
)


class User(BaseModel):
    id: NonEmptyString = Field(default_factory=generate_uuid4)
    email: NonEmptyString
    authentik_uid: NonEmptyString
    password_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserController:
    @staticmethod
    async def get_by_id(user_id: NonEmptyString) -> User | None:
        query = users.select().where(users.c.id == user_id)
        result = await get_database().fetch_one(query)
        return User(**result) if result else None

    @staticmethod
    async def get_by_authentik_uid(authentik_uid: NonEmptyString) -> User | None:
        query = users.select().where(users.c.authentik_uid == authentik_uid)
        result = await get_database().fetch_one(query)
        return User(**result) if result else None

    @staticmethod
    async def get_by_email(email: NonEmptyString) -> User | None:
        query = users.select().where(users.c.email == email)
        result = await get_database().fetch_one(query)
        return User(**result) if result else None

    @staticmethod
    async def create_or_update(
        id: NonEmptyString,
        authentik_uid: NonEmptyString,
        email: NonEmptyString,
        password_hash: str | None = None,
    ) -> User:
        existing = await UserController.get_by_authentik_uid(authentik_uid)
        now = datetime.now(timezone.utc)

        if existing:
            update_values: dict = {"email": email, "updated_at": now}
            if password_hash is not None:
                update_values["password_hash"] = password_hash
            query = (
                users.update()
                .where(users.c.authentik_uid == authentik_uid)
                .values(**update_values)
            )
            await get_database().execute(query)
            return User(
                id=existing.id,
                authentik_uid=authentik_uid,
                email=email,
                password_hash=password_hash or existing.password_hash,
                created_at=existing.created_at,
                updated_at=now,
            )
        else:
            user = User(
                id=id,
                authentik_uid=authentik_uid,
                email=email,
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )
            query = users.insert().values(**user.model_dump())
            await get_database().execute(query)
            return user

    @staticmethod
    async def set_password_hash(user_id: NonEmptyString, password_hash: str) -> None:
        now = datetime.now(timezone.utc)
        query = (
            users.update()
            .where(users.c.id == user_id)
            .values(password_hash=password_hash, updated_at=now)
        )
        await get_database().execute(query)

    @staticmethod
    async def list_all() -> list[User]:
        query = users.select().order_by(users.c.created_at.desc())
        results = await get_database().fetch_all(query)
        return [User(**r) for r in results]

    @staticmethod
    async def get_by_ids(user_ids: list[NonEmptyString]) -> dict[str, User]:
        query = users.select().where(users.c.id.in_(user_ids))
        results = await get_database().fetch_all(query)
        return {user.id: User(**user) for user in results}


user_controller = UserController()
