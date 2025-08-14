"""
External integrations for neo-commons library.
Protocol-based dependency injection for maximum reusability across different API services.
"""

# Import Keycloak integration
from .keycloak import (
    KeycloakClient,
    DefaultTokenValidationConfig,
    TokenValidationConfigProtocol,
    HttpClientProtocol,
    create_keycloak_client,
    get_keycloak_client,
    set_global_keycloak_client
)

__all__ = [
    "KeycloakClient",
    "DefaultTokenValidationConfig", 
    "TokenValidationConfigProtocol",
    "HttpClientProtocol",
    "create_keycloak_client",
    "get_keycloak_client",
    "set_global_keycloak_client"
]