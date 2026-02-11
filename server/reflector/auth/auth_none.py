from pydantic import BaseModel


class UserInfo(BaseModel):
    sub: str


class AccessTokenInfo(BaseModel):
    pass


def authenticated():
    return None


def current_user():
    return None


def current_user_optional():
    return None
