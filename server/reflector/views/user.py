from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()


class UserInfo(BaseModel):
    sub: str
    email: Optional[str]
    email_verified: Optional[bool]


@router.get("/me")
async def user_me(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> UserInfo | None:
    return user
