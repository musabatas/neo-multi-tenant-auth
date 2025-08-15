"""
External integrations for neo-commons library.
Protocol-based dependency injection for maximum reusability across different API services.
"""

# Import Keycloak integration - main components
from .keycloak import (
    # Clients
    EnhancedKeycloakAsyncClient,
    KeycloakAsyncClient,  # Alias for convenience
    BaseKeycloakClient,
    # Managers  
    EnhancedTokenManager,
    TenantRealmManager,
    # Protocols
    TokenValidationConfigProtocol,
    HttpClientProtocol,
    KeycloakConfigProtocol,
    # Config
    DefaultTokenValidationConfig,
    DefaultKeycloakConfig,
    # Exceptions
    RealmManagerException
)

__all__ = [
    # Clients
    "EnhancedKeycloakAsyncClient", 
    "KeycloakAsyncClient",  # Alias for convenience
    "BaseKeycloakClient",
    # Managers
    "EnhancedTokenManager",
    "TenantRealmManager",
    # Protocols
    "TokenValidationConfigProtocol",
    "HttpClientProtocol",
    "KeycloakConfigProtocol",
    # Config
    "DefaultTokenValidationConfig",
    "DefaultKeycloakConfig",
    # Exceptions
    "RealmManagerException"
]