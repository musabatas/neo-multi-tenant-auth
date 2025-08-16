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
    PermissionCacheProtocol,
    PermissionDataSourceProtocol,
    WildcardMatcherProtocol,
    
    # Service protocols
    GuestAuthServiceProtocol,
    CacheServiceProtocol,
    
    # Identity protocols
    UserIdentityResolverProtocol,
    
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
from .identity import DefaultUserIdentityResolver
from .registry import (
    PermissionRegistry, PermissionDefinition, get_permission_registry,
    PLATFORM_PERMISSIONS, TENANT_PERMISSIONS, PERMISSION_GROUPS
)
from .services import (
    AuthServiceWrapper, PermissionServiceWrapper, GuestAuthServiceWrapper,
    create_auth_service, create_permission_service, create_guest_auth_service,
    create_user_identity_resolver
)
from .permissions import (
    PermissionCacheManager, DefaultPermissionCacheManager,
    create_permission_cache_manager, create_wildcard_permission_matcher
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
    "PermissionCacheProtocol",
    "PermissionDataSourceProtocol",
    "WildcardMatcherProtocol",
    "GuestAuthServiceProtocol",
    "CacheServiceProtocol",
    "UserIdentityResolverProtocol",
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
    # Identity
    "DefaultUserIdentityResolver",
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
    "create_guest_auth_service",
    "create_user_identity_resolver",
    # Permission Cache Management
    "PermissionCacheManager",
    "DefaultPermissionCacheManager",
    "create_permission_cache_manager",
    "create_wildcard_permission_matcher"
]