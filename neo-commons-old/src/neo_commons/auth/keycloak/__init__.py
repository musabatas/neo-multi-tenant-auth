"""
Keycloak integration module.

Provides enterprise-grade Keycloak integration including client management,
realm operations, token validation, and multi-tenant realm management.
"""

# Protocol definitions
from .protocols import (
    KeycloakClientProtocol,
    RealmManagerProtocol,
    RealmProviderProtocol,
    TokenValidatorProtocol,
)

# Core implementations
from .client import KeycloakClient
from .realm_manager import DatabaseRealmManager
from .token_validator import DualStrategyTokenValidator

# Realm providers
from .realm_provider import (
    AdminRealmProvider,
    TenantRealmProvider,
    ConfigurableRealmProvider,
)

__all__ = [
    # Protocols
    "KeycloakClientProtocol",
    "RealmManagerProtocol", 
    "RealmProviderProtocol",
    "TokenValidatorProtocol",
    
    # Core implementations
    "KeycloakClient",
    "DatabaseRealmManager",
    "DualStrategyTokenValidator",
    
    # Realm providers
    "AdminRealmProvider",
    "TenantRealmProvider",
    "ConfigurableRealmProvider",
]