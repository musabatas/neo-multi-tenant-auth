"""Authentication core events.

Domain events for authentication platform following maximum separation.
Each event represents exactly one authentication lifecycle occurrence.
"""

from .user_authenticated import UserAuthenticated
from .user_logged_out import UserLoggedOut
from .token_refreshed import TokenRefreshed
from .session_expired import SessionExpired
from .authentication_failed import AuthenticationFailedEvent

__all__ = [
    "UserAuthenticated",
    "UserLoggedOut", 
    "TokenRefreshed",
    "SessionExpired",
    "AuthenticationFailedEvent",
]