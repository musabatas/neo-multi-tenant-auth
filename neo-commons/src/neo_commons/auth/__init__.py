"""
Neo-Commons Auth Infrastructure

Enterprise-grade authentication and authorization infrastructure with:
- Protocol-based dependency injection for maximum flexibility
- Multi-tenant Keycloak integration with realm management
- Sub-millisecond permission checking with intelligent caching
- Token validation with dual-strategy support (local + introspection)
- Permission decorators with tenant context support
"""

from .protocols import (
    # Core Keycloak protocols
    KeycloakClientProtocol,
    RealmProviderProtocol,
    RealmManagerProtocol,
    TokenValidatorProtocol,
    
    # Permission protocols
    PermissionValidatorProtocol,
    PermissionRegistryProtocol,
    PermissionDecoratorProtocol,
    PermissionCheckerProtocol,
    
    # Service protocols
    GuestAuthServiceProtocol,
    CacheServiceProtocol,
    
    # Configuration protocols
    AuthConfigProtocol,
    CacheKeyProviderProtocol,
    
    # Enums
    ValidationStrategy,
    PermissionScope
)

# Import key classes for convenience
from .decorators import RequirePermission, require_permission, PermissionMetadata
from .dependencies import (
    CurrentUser, CheckPermission, TokenData, GuestOrAuthenticated, GuestSessionInfo
)
from .registry import (
    PermissionRegistry, PermissionDefinition, get_permission_registry,
    PLATFORM_PERMISSIONS, TENANT_PERMISSIONS, PERMISSION_GROUPS
)
from .services import (
    AuthServiceWrapper, PermissionServiceWrapper, GuestAuthServiceWrapper,
    create_auth_service, create_permission_service, create_guest_auth_service
)

__all__ = [
    # Protocols
    "KeycloakClientProtocol",
    "RealmProviderProtocol",
    "RealmManagerProtocol",
    "TokenValidatorProtocol",
    "PermissionValidatorProtocol",
    "PermissionRegistryProtocol",
    "PermissionDecoratorProtocol",
    "PermissionCheckerProtocol",
    "GuestAuthServiceProtocol",
    "CacheServiceProtocol",
    "AuthConfigProtocol",
    "CacheKeyProviderProtocol",
    # Enums
    "ValidationStrategy",
    "PermissionScope",
    # Decorators
    "RequirePermission",
    "require_permission",
    "PermissionMetadata",
    # Dependencies
    "CurrentUser",
    "CheckPermission",
    "TokenData",
    "GuestOrAuthenticated",
    "GuestSessionInfo",
    # Registry
    "PermissionRegistry",
    "PermissionDefinition",
    "get_permission_registry",
    "PLATFORM_PERMISSIONS",
    "TENANT_PERMISSIONS",
    "PERMISSION_GROUPS",
    # Services
    "AuthServiceWrapper",
    "PermissionServiceWrapper",
    "GuestAuthServiceWrapper",
    "create_auth_service",
    "create_permission_service",
    "create_guest_auth_service"
]