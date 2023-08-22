from pydantic import BaseModel
from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class UserInfo(BaseModel):
    sub: str


class AccessTokenInfo(BaseModel):
    pass


def authenticated(token: Annotated[str, Depends(oauth2_scheme)]):
    return None


def current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    return None


def current_user_optional(token: Annotated[str, Depends(oauth2_scheme)]):
    return None
