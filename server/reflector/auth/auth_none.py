from pydantic import BaseModel
from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserInfo(BaseModel):
    sub: str


class AccessTokenInfo(BaseModel):
    pass


def authenticated(token: Annotated[str, Depends(oauth2_scheme)]):
    def _authenticated():
        return None

    return _authenticated


def current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    def _current_user():
        return None

    return _current_user


def current_user_optional(token: Annotated[str, Depends(oauth2_scheme)]):
    def _current_user_optional():
        return None

    return _current_user_optional
