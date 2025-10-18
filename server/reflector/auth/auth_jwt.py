from typing import Annotated, List, Optional

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from reflector.db.user_api_keys import user_api_keys_controller
from reflector.logger import logger
from reflector.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

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
    email: Optional[str] = None

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


async def _authenticate_user(
    jwt_token: Optional[str],
    api_key: Optional[str],
    jwtauth: JWTAuth,
) -> UserInfo | None:
    user_infos: List[UserInfo] = []
    if api_key:
        user_api_key = await user_api_keys_controller.verify_key(api_key)
        if user_api_key:
            user_infos.append(UserInfo(sub=user_api_key.user_id, email=None))

    if jwt_token:
        try:
            payload = jwtauth.verify_token(jwt_token)
            sub = payload["sub"]
            email = payload["email"]
            user_infos.append(UserInfo(sub=sub, email=email))
        except JWTError as e:
            logger.error(f"JWT error: {e}")
            raise HTTPException(status_code=401, detail="Invalid authentication")

    if len(user_infos) == 0:
        return None

    if len(set([x.sub for x in user_infos])) > 1:
        raise JWTException(
            status_code=401,
            detail="Invalid authentication: more than one user provided",
        )

    return user_infos[0]


async def current_user(
    jwt_token: Annotated[Optional[str], Depends(oauth2_scheme)],
    api_key: Annotated[Optional[str], Depends(api_key_header)],
    jwtauth: JWTAuth = Depends(),
):
    user = await _authenticate_user(jwt_token, api_key, jwtauth)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def current_user_optional(
    jwt_token: Annotated[Optional[str], Depends(oauth2_scheme)],
    api_key: Annotated[Optional[str], Depends(api_key_header)],
    jwtauth: JWTAuth = Depends(),
):
    return await _authenticate_user(jwt_token, api_key, jwtauth)
