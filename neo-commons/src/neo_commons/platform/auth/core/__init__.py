"""Core authentication domain objects.

This module provides the clean core of the authentication platform following
maximum separation principle. Contains only domain objects with no external
dependencies or business logic.

Components:
- value_objects: Immutable authentication value objects
- exceptions: Authentication-specific domain exceptions  
- protocols: Contract definitions for external dependencies
- entities: Core authentication domain entities
- events: Authentication lifecycle events

Architecture:
- Zero external dependencies
- Immutable value objects
- Clear contract boundaries
- Event-driven design
"""

# Core exports - only value objects, exceptions, and protocols
from .value_objects import AccessToken, RefreshToken, TokenClaims, PublicKey, SessionId, RealmIdentifier
from .exceptions import AuthenticationFailed, TokenExpired, InvalidSignature, PublicKeyError, RealmNotFound, SessionInvalid
from .protocols import TokenValidator, PublicKeyProvider, SessionManager, RealmProvider, PermissionLoader
from .entities import AuthSession, TokenMetadata, RealmConfig, UserContext
from .events import UserAuthenticated, UserLoggedOut, TokenRefreshed, SessionExpired, AuthenticationFailedEvent

__all__ = [
    # Value Objects
    "AccessToken",
    "RefreshToken", 
    "TokenClaims",
    "PublicKey",
    "SessionId",
    "RealmIdentifier",
    
    # Exceptions
    "AuthenticationFailed",
    "TokenExpired",
    "InvalidSignature", 
    "PublicKeyError",
    "RealmNotFound",
    "SessionInvalid",
    
    # Protocols
    "TokenValidator",
    "PublicKeyProvider",
    "SessionManager",
    "RealmProvider", 
    "PermissionLoader",
    
    # Entities
    "AuthSession",
    "TokenMetadata",
    "RealmConfig",
    "UserContext",
    
    # Events
    "UserAuthenticated",
    "UserLoggedOut",
    "TokenRefreshed", 
    "SessionExpired",
    "AuthenticationFailedEvent",
]