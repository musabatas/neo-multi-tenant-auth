"""
Keycloak integration for neo-commons library.
Protocol-based dependency injection for maximum reusability.
"""

# Import from reorganized directory structure
from .clients import (
    EnhancedKeycloakAsyncClient,
    KeycloakAsyncClient,  # Alias for convenience
    BaseKeycloakClient
)
from .managers import (
    EnhancedTokenManager,
    ValidationStrategy,
    TokenValidationException,
    DefaultTokenConfig,
    TenantRealmManager
)
from .operations import (
    KeycloakAdminOperations,
    KeycloakTokenOperations,
    KeycloakRealmOperations,
    KeycloakUserOperations
)
from .protocols import (
    KeycloakConfigProtocol,
    HttpClientProtocol,
    KeycloakTokenProtocol,
    KeycloakUserProtocol,
    KeycloakRealmProtocol,
    KeycloakAdminProtocol,
    TokenValidationConfigProtocol,
    TokenConfigProtocol,
    RealmConfigProtocol
)
from .config import (
    DefaultKeycloakConfig,
    HttpxHttpClient,
    DefaultTokenValidationConfig,
    DefaultRealmConfig
)
from .exceptions import (
    RealmManagerException,
    RealmNotConfiguredException,
    RealmCreationException
)

__all__ = [
    # Clients
    "EnhancedKeycloakAsyncClient",
    "KeycloakAsyncClient",  # Alias for convenience
    "BaseKeycloakClient",
    # Managers
    "EnhancedTokenManager",
    "ValidationStrategy",
    "TokenValidationException",
    "DefaultTokenConfig",
    "TenantRealmManager",
    # Operations
    "KeycloakAdminOperations",
    "KeycloakTokenOperations",
    "KeycloakRealmOperations",
    "KeycloakUserOperations",
    # Protocols
    "KeycloakConfigProtocol",
    "HttpClientProtocol",
    "KeycloakTokenProtocol",
    "KeycloakUserProtocol",
    "KeycloakRealmProtocol",
    "KeycloakAdminProtocol",
    "TokenValidationConfigProtocol",
    "TokenConfigProtocol",
    "RealmConfigProtocol",
    # Config
    "DefaultKeycloakConfig",
    "HttpxHttpClient",
    "DefaultTokenValidationConfig",
    "DefaultRealmConfig",
    # Exceptions
    "RealmManagerException",
    "RealmNotConfiguredException",
    "RealmCreationException"
]