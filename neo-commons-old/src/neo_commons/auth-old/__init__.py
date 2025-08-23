"""
Neo-Commons Auth Infrastructure

Enterprise-grade authentication and authorization infrastructure with:
- Protocol-based dependency injection for maximum flexibility
- Multi-tenant Keycloak integration with realm management
- Sub-millisecond permission checking with intelligent caching
- Token validation with dual-strategy support (local + introspection)
- Permission decorators with tenant context support

Quick Start:
    # Basic permission checking
    from neo_commons.auth.dependencies import CheckPermission
    
    @router.get("/users")
    async def list_users(
        current_user = Depends(CheckPermission(["users:list"]))
    ):
        return await user_service.list_users()
    
    # Multiple permissions with OR logic
    @router.post("/admin/reset")
    async def admin_reset(
        current_user = Depends(CheckPermission(
            ["admin:reset", "system:maintenance"], 
            require_all=False
        ))
    ):
        return await admin_service.reset_system()
    
    # Guest access with fallback
    from neo_commons.auth.dependencies import GuestOrAuthenticated
    
    @router.get("/public/stats")
    async def public_stats(
        user_info = Depends(GuestOrAuthenticated())
    ):
        # user_info is either CurrentUser or GuestSessionInfo
        return await stats_service.get_public_stats()

Architecture:
    - Protocols: Define contracts for all authentication components
    - Dependencies: FastAPI dependency injection for route protection
    - Decorators: Function-level permission enforcement
    - Implementations: Keycloak, Redis, and database integrations
    - Permissions: Caching, validation, and wildcard matching
    - Services: High-level auth orchestration and compatibility layers

Performance:
    - Sub-millisecond permission checks with Redis caching
    - Automatic cache invalidation on permission changes
    - Efficient wildcard permission matching (users.*.read)
    - Connection pooling for database and Keycloak operations
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
    create_auth_service, create_permission_service, 
    create_guest_auth_service, create_guest_auth_service_wrapper,
    create_default_guest_service, create_restrictive_guest_service, create_liberal_guest_service,
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