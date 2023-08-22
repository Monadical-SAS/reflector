from fastapi.security import OAuth2AuthorizationCodeBearer
from fief_client import FiefAccessTokenInfo, FiefAsync, FiefUserInfo
from fief_client.integrations.fastapi import FiefAuth
from reflector.settings import settings

fief = FiefAsync(
    settings.AUTH_FIEF_URL,
    settings.AUTH_FIEF_CLIENT_ID,
    settings.AUTH_FIEF_CLIENT_SECRET,
)

scheme = OAuth2AuthorizationCodeBearer(
    f"{settings.AUTH_FIEF_URL}/authorize",
    f"{settings.AUTH_FIEF_URL}/api/token",
    scopes={"openid": "openid", "offline_access": "offline_access"},
    auto_error=False,
)

auth = FiefAuth(fief, scheme)

UserInfo = FiefUserInfo
AccessTokenInfo = FiefAccessTokenInfo
authenticated = auth.authenticated()
current_user = auth.current_user()
current_user_optional = auth.current_user(optional=True)
