"""
Auth protocol interfaces organized by concern.

This module consolidates all authentication and authorization protocols
while maintaining backward compatibility with the previous single-file structure.
"""

# Core configuration and enums
from .base import (
    ValidationStrategy,
    PermissionScope,
    AuthConfigProtocol,
    CacheKeyProviderProtocol,
)

# Keycloak integration protocols
from .keycloak import (
    KeycloakClientProtocol,
    RealmProviderProtocol,
    RealmManagerProtocol,
    TokenValidatorProtocol,
)

# Permission management protocols
from .permissions import (
    PermissionValidatorProtocol,
    PermissionRegistryProtocol,
    PermissionDecoratorProtocol,
    PermissionCheckerProtocol,
    PermissionCacheProtocol,
    PermissionDataSourceProtocol,
    WildcardMatcherProtocol,
)

# Service protocols
from .services import (
    GuestAuthServiceProtocol,
    CacheServiceProtocol,
    UserIdentityResolverProtocol,
)

__all__ = [
    # Enums and config
    "ValidationStrategy",
    "PermissionScope",
    "AuthConfigProtocol",
    "CacheKeyProviderProtocol",
    
    # Keycloak protocols
    "KeycloakClientProtocol",
    "RealmProviderProtocol",
    "RealmManagerProtocol",
    "TokenValidatorProtocol",
    
    # Permission protocols
    "PermissionValidatorProtocol",
    "PermissionRegistryProtocol",
    "PermissionDecoratorProtocol",
    "PermissionCheckerProtocol",
    "PermissionCacheProtocol",
    "PermissionDataSourceProtocol",
    "WildcardMatcherProtocol",
    
    # Service protocols
    "GuestAuthServiceProtocol",
    "CacheServiceProtocol",
    "UserIdentityResolverProtocol",
]