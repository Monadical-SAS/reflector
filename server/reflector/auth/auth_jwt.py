from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from reflector.logger import logger
from reflector.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

jwt_public_key = open(f"reflector/auth/jwt/keys/{settings.AUTH_JWT_PUBLIC_KEY}").read()
jwt_algorithm = settings.AUTH_JWT_ALGORITHM
jwt_audience = settings.AUTH_JWT_AUDIENCE


class JWTException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

    def __str__(self):
        return f"<JWTException {self.status_code}: {self.detail}>"


class UserInfo(BaseModel):
    sub: str

    def __getitem__(self, key):
        return getattr(self, key)


class AccessTokenInfo(BaseModel):
    exp: Optional[int] = None
    sub: Optional[str] = None


class JWTAuth:
    def verify_token(self, token: str):
        try:
            payload = jwt.decode(
                token,
                jwt_public_key,
                algorithms=[jwt_algorithm],
                audience=jwt_audience,
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT error: {e}")
            raise


def authenticated(token: Annotated[str, Depends(oauth2_scheme)]):
    if token is None:
        raise JWTException(status_code=401, detail="Not authenticated")
    return None


def current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    jwtauth: JWTAuth = Depends(),
):
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwtauth.verify_token(token)
        sub = payload["sub"]
        return UserInfo(sub=sub)
    except JWTError as e:
        logger.error(f"JWT error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication")


def current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    jwtauth: JWTAuth = Depends(),
):
    # we accept no token, but if one is provided, it must be a valid one.
    if token is None:
        return None
    try:
        payload = jwtauth.verify_token(token)
        sub = payload["sub"]
        return UserInfo(sub=sub)
    except JWTError as e:
        logger.error(f"JWT error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication")
