"""Password-based authentication backend for selfhosted deployments.

Issues HS256 JWTs signed with settings.SECRET_KEY. Provides a POST /auth/login
endpoint for email/password authentication.
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from reflector.auth.password_utils import verify_password
from reflector.db.user_api_keys import user_api_keys_controller
from reflector.db.users import user_controller
from reflector.logger import logger
from reflector.settings import settings

if TYPE_CHECKING:
    from fastapi import WebSocket

# --- FastAPI security schemes (same pattern as auth_jwt.py) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# --- JWT configuration ---
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# --- Rate limiting (in-memory) ---
_login_attempts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX = 10  # max attempts per window


def _check_rate_limit(key: str) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.monotonic()
    attempts = _login_attempts[key]
    _login_attempts[key] = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    if len(_login_attempts[key]) >= RATE_LIMIT_MAX:
        return False
    _login_attempts[key].append(now)
    return True


# --- Pydantic models ---
class UserInfo(BaseModel):
    sub: str
    email: Optional[str] = None

    def __getitem__(self, key):
        return getattr(self, key)


class AccessTokenInfo(BaseModel):
    exp: Optional[int] = None
    sub: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# --- JWT token creation and verification ---
def _create_access_token(user_id: str, email: str) -> tuple[str, int]:
    """Create an HS256 JWT. Returns (token, expires_in_seconds)."""
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def _verify_token(token: str) -> dict:
    """Verify and decode an HS256 JWT."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])


# --- Authentication logic (mirrors auth_jwt._authenticate_user) ---
async def _authenticate_user(
    jwt_token: Optional[str],
    api_key: Optional[str],
) -> UserInfo | None:
    user_infos: list[UserInfo] = []

    if api_key:
        user_api_key = await user_api_keys_controller.verify_key(api_key)
        if user_api_key:
            user_infos.append(UserInfo(sub=user_api_key.user_id, email=None))

    if jwt_token:
        try:
            payload = _verify_token(jwt_token)
            user_id = payload["sub"]
            email = payload.get("email")
            user_infos.append(UserInfo(sub=user_id, email=email))
        except JWTError as e:
            logger.error(f"JWT error: {e}")
            raise HTTPException(status_code=401, detail="Invalid authentication")

    if len(user_infos) == 0:
        return None

    if len(set(x.sub for x in user_infos)) > 1:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication: more than one user provided",
        )

    return user_infos[0]


# --- FastAPI dependencies (exported, required by auth/__init__.py) ---
def authenticated(token: Annotated[str, Depends(oauth2_scheme)]):
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return None


async def current_user(
    jwt_token: Annotated[Optional[str], Depends(oauth2_scheme)],
    api_key: Annotated[Optional[str], Depends(api_key_header)],
):
    user = await _authenticate_user(jwt_token, api_key)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def current_user_optional(
    jwt_token: Annotated[Optional[str], Depends(oauth2_scheme)],
    api_key: Annotated[Optional[str], Depends(api_key_header)],
):
    return await _authenticate_user(jwt_token, api_key)


# --- WebSocket auth (same pattern as auth_jwt.py) ---
def parse_ws_bearer_token(
    websocket: "WebSocket",
) -> tuple[Optional[str], Optional[str]]:
    raw = websocket.headers.get("sec-websocket-protocol") or ""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) >= 2 and parts[0].lower() == "bearer":
        return parts[1], "bearer"
    return None, None


async def current_user_ws_optional(websocket: "WebSocket") -> Optional[UserInfo]:
    token, _ = parse_ws_bearer_token(websocket)
    if not token:
        return None
    return await _authenticate_user(token, None)


# --- Login router ---
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
        )

    user = await user_controller.get_by_email(body.email)
    if not user or not user.password_hash:
        print("invalid email")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user.password_hash):
        print("invalid pass")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token, expires_in = _create_access_token(user.id, user.email)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
    )
