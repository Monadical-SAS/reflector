import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def apikey_auth(apikey: str | None = Depends(oauth2_scheme)):
    required_key = os.environ.get("REFLECTOR_GPU_APIKEY")
    if not required_key:
        return
    if apikey and apikey == required_key:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )
