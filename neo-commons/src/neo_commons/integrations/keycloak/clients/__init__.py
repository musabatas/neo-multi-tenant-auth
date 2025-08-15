"""
Keycloak client implementations.

Provides async clients for Keycloak integration.
"""
from .async_client import EnhancedKeycloakAsyncClient
from .base_client import BaseKeycloakClient

# Convenience alias for the recommended client
KeycloakAsyncClient = EnhancedKeycloakAsyncClient

__all__ = [
    "EnhancedKeycloakAsyncClient",
    "KeycloakAsyncClient",  # Alias for convenience
    "BaseKeycloakClient",  # Base class for advanced use cases
]