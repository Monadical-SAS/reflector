# Video Platform Abstraction Layer
"""
This module provides an abstraction layer for different video conferencing platforms.
It allows seamless switching between providers (Whereby, Daily.co, etc.) without
changing the core application logic.
"""

from .base import MeetingData, VideoPlatformClient, VideoPlatformConfig
from .registry import get_platform_client, register_platform

__all__ = [
    "VideoPlatformClient",
    "VideoPlatformConfig",
    "MeetingData",
    "get_platform_client",
    "register_platform",
]
