"""Authentication core entities.

Domain entities for authentication platform following maximum separation.
Each entity handles exactly one authentication domain concept.
"""

from .auth_session import AuthSession
from .token_metadata import TokenMetadata
from .realm_config import RealmConfig
from .user_context import UserContext

__all__ = [
    "AuthSession",
    "TokenMetadata",
    "RealmConfig",
    "UserContext",
]