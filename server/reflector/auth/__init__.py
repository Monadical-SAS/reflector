from reflector.settings import settings
from reflector.logger import logger
import importlib

logger.info(f"User authentication using {settings.AUTH_BACKEND}")
module_name = f"reflector.auth.auth_{settings.AUTH_BACKEND}"
auth_module = importlib.import_module(module_name)

UserInfo = auth_module.UserInfo
AccessTokenInfo = auth_module.AccessTokenInfo
authenticated = auth_module.authenticated
current_user = auth_module.current_user
current_user_optional = auth_module.current_user_optional
