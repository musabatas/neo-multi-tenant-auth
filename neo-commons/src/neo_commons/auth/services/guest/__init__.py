"""
Guest Authentication Services

Neo-commons guest authentication module providing session management, rate limiting,
and anonymous user tracking for public endpoints.

Key Features:
- Session management with configurable TTL
- IP-based and session-based rate limiting  
- Protocol-based design for service independence
- Configurable session providers for business rules
- Redis caching with automatic cleanup
"""

from .service import DefaultGuestAuthService
from .provider import (
    GuestSessionProvider,
    DefaultGuestSessionProvider, 
    create_guest_session_provider
)
from .factory import create_guest_auth_service

__all__ = [
    "DefaultGuestAuthService",
    "GuestSessionProvider", 
    "DefaultGuestSessionProvider",
    "create_guest_session_provider",
    "create_guest_auth_service"
]