"""Authentication domain exceptions.

Domain-specific exceptions for authentication platform following maximum separation.
Each exception handles exactly one authentication failure scenario.
"""

from .authentication_failed import AuthenticationFailed
from .token_expired import TokenExpired
from .invalid_signature import InvalidSignature
from .public_key_error import PublicKeyError
from .realm_not_found import RealmNotFound
from .session_invalid import SessionInvalid

__all__ = [
    "AuthenticationFailed",
    "TokenExpired", 
    "InvalidSignature",
    "PublicKeyError",
    "RealmNotFound",
    "SessionInvalid",
]