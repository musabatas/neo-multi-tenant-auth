"""
Keycloak protocol definitions.

Protocol interfaces for Keycloak client implementations.
"""
from .protocols import (
    KeycloakConfigProtocol,
    HttpClientProtocol,
    KeycloakTokenProtocol,
    KeycloakUserProtocol,
    KeycloakRealmProtocol,
    KeycloakAdminProtocol
)
from .client_protocols import (
    TokenValidationConfigProtocol
)
from .token_protocols import (
    CacheManagerProtocol as TokenCacheProtocol,
    KeycloakClientProtocol as TokenKeycloakClientProtocol,
    TokenConfigProtocol
)
from .realm_protocols import (
    DatabaseManagerProtocol,
    CacheManagerProtocol as RealmCacheProtocol,
    KeycloakClientProtocol as RealmKeycloakClientProtocol,
    RealmConfigProtocol
)

__all__ = [
    # Main protocols from protocols.py
    "KeycloakConfigProtocol",
    "HttpClientProtocol",
    "KeycloakTokenProtocol",
    "KeycloakUserProtocol",
    "KeycloakRealmProtocol",
    "KeycloakAdminProtocol",
    # Client protocols
    "TokenValidationConfigProtocol",
    # Token protocols
    "TokenCacheProtocol",
    "TokenKeycloakClientProtocol",
    "TokenConfigProtocol",
    # Realm protocols
    "DatabaseManagerProtocol",
    "RealmCacheProtocol",
    "RealmKeycloakClientProtocol",
    "RealmConfigProtocol"
]