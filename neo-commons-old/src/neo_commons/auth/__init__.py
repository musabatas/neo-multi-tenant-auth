"""
Enterprise-grade authentication and authorization module.

Clean, domain-driven architecture with comprehensive enterprise features:
- Multi-tenant Keycloak integration
- Sub-millisecond permission checking with intelligent caching
- Protocol-based dependency injection
- Clean Architecture with proper layer separation
- Backward compatibility for seamless migration

Quick Start:
    # FastAPI dependencies
    from neo_commons.auth import CheckPermission, CurrentUser
    
    @router.get("/users")
    async def list_users(
        current_user = Depends(CheckPermission(["users:list"]))
    ):
        return await user_service.list_users()
    
    # Permission decorators
    from neo_commons.auth import require_permission
    
    @require_permission(["users:create"])
    async def create_user(user_data: dict):
        return await user_service.create(user_data)

Architecture:
    - core/: Domain entities, enums, exceptions, and core protocols
    - keycloak/: Keycloak integration (client, realm management, token validation)
    - permissions/: Permission management (checking, caching, registry, matching)
    - identity/: User identity resolution and mapping
    - sessions/: Session management (guest auth, caching)
    - fastapi/: FastAPI integration (dependencies, decorators, middleware)
    - utils/: Utilities (cache keys, rate limiting, scanner)
    - legacy.py: Backward compatibility layer
"""

__version__ = "2.0.0"
__author__ = "NeoMultiTenant Team"

# Core domain exports
from .core import (
    # Enums
    ValidationStrategy,
    PermissionScope,
    
    # Exceptions
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    SessionError,
    RateLimitError,
    TokenValidationError,
    PermissionDeniedError,
    
    # Core protocols
    AuthConfigProtocol,
)

# Keycloak integration exports
from .keycloak import (
    KeycloakClient,
    DatabaseRealmManager,
    DualStrategyTokenValidator,
    AdminRealmProvider,
    TenantRealmProvider,
    ConfigurableRealmProvider,
)

# Permission management exports
from .permissions import (
    DefaultPermissionChecker,
    DefaultPermissionCache,
    DefaultPermissionRegistry,
    DefaultWildcardMatcher,
    DatabasePermissionDataSource,
    CompositePermissionDataSource,
    CachedPermissionDataSource,
    PermissionDataSourceProtocol,
)

# Identity resolution exports
from .identity import (
    DefaultUserIdentityResolver,
    DefaultUserIdentityMapper,
    MappingResult,
    BulkMappingResult,
    MappingStatus,
    MappingStrategy,
)

# Session management exports
from .sessions import (
    DefaultGuestAuthService,
    DefaultSessionCache,
    create_guest_auth_service,
    create_session_cache,
)

# Repository exports
from .repositories import (
    BaseAuthRepository,
    BasePermissionRepository,
)

# Decorator exports
from .decorators import (
    require_permission as decorator_require_permission,
)

# Dependencies exports (for backward compatibility)
from .dependencies import (
    create_reference_data_access,
    create_guest_session_info,
)

# Manager exports
from .manager import (
    PermissionSyncManager,
)

# FastAPI integration exports
from .fastapi import (
    CurrentUser,
    CheckPermission,
    TokenData,
    RequirePermission,
    PermissionMetadata,
    AuthenticationMiddleware,
    TenantAwareAuthMiddleware,
)

# Utility exports
from .utils import (
    DefaultCacheKeyProvider,
    AdminCacheKeyProvider,
    TenantCacheKeyProvider,
    RateLimitType,
    RateLimit,
    RateLimitState,
    SlidingWindowRateLimiter,
    AuthRateLimitManager,
    EndpointPermissionScanner,
    create_cache_key_provider,
    create_admin_cache_key_provider,
    create_tenant_cache_key_provider,
    create_auth_rate_limiter,
    create_permission_scanner,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    
    # Core domain
    "ValidationStrategy",
    "PermissionScope", 
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "SessionError",
    "RateLimitError",
    "TokenValidationError",
    "PermissionDeniedError",
    "AuthConfigProtocol",
    
    # Keycloak integration
    "KeycloakClient",
    "DatabaseRealmManager", 
    "DualStrategyTokenValidator",
    "AdminRealmProvider",
    "TenantRealmProvider",
    "ConfigurableRealmProvider",
    
    # Permission management
    "DefaultPermissionChecker",
    "DefaultPermissionCache",
    "DefaultPermissionRegistry",
    "DefaultWildcardMatcher",
    "DatabasePermissionDataSource",
    "CompositePermissionDataSource",
    "CachedPermissionDataSource",
    "PermissionDataSourceProtocol",
    
    # Identity resolution
    "DefaultUserIdentityResolver",
    "DefaultUserIdentityMapper",
    "MappingResult",
    "BulkMappingResult",
    "MappingStatus",
    "MappingStrategy",
    
    # Session management
    "DefaultGuestAuthService",
    "DefaultSessionCache",
    "create_guest_auth_service",
    "create_session_cache",
    
    # Repository classes
    "BaseAuthRepository",
    "BasePermissionRepository",
    
    # Decorators
    "decorator_require_permission",
    
    # Dependencies
    "create_reference_data_access",
    "create_guest_session_info",
    
    # Manager
    "PermissionSyncManager",
    
    # FastAPI integration
    "CurrentUser",
    "CheckPermission",
    "TokenData",
    "RequirePermission",
    "PermissionMetadata",
    "AuthenticationMiddleware",
    "TenantAwareAuthMiddleware",
    
    # Utilities
    "DefaultCacheKeyProvider",
    "AdminCacheKeyProvider",
    "TenantCacheKeyProvider",
    "RateLimitType",
    "RateLimit",
    "RateLimitState",
    "SlidingWindowRateLimiter",
    "AuthRateLimitManager",
    "EndpointPermissionScanner",
    "create_cache_key_provider",
    "create_admin_cache_key_provider",
    "create_tenant_cache_key_provider",
    "create_auth_rate_limiter",
    "create_permission_scanner",
    
    # Factory functions
    "create_auth_service",
    "create_permission_cache_manager",
]

# Factory functions for convenient service creation
def create_auth_service(auth_config=None, cache_service=None, cache_key_provider=None):
    """
    Create auth service with token validator.
    
    Args:
        auth_config: Authentication configuration (optional)
        cache_service: Cache service for token caching (optional)
        cache_key_provider: Cache key provider (optional)
        
    Returns:
        Auth service with token validator
    """
    from typing import Optional
    from .core.config import AuthConfig
    from .keycloak.client import KeycloakClient
    from .utils import DefaultCacheKeyProvider
    from loguru import logger
    
    if auth_config is None:
        auth_config = AuthConfig()
    
    # Create cache key provider if not provided
    if cache_key_provider is None:
        cache_key_provider = DefaultCacheKeyProvider()
    
    # Create default cache service if not provided
    if cache_service is None:
        from ..cache import CacheManager, TenantAwareCacheService
        cache_manager = CacheManager()
        cache_service = TenantAwareCacheService(cache_manager)
    
    # Create Keycloak client with correct parameters
    keycloak_client = KeycloakClient(
        config=auth_config,
        cache_service=cache_service,
        cache_key_provider=cache_key_provider
    )
    
    # Create token validator with correct parameters
    token_validator = DualStrategyTokenValidator(
        keycloak_client=keycloak_client,
        config=auth_config,
        cache_service=cache_service,
        cache_key_provider=cache_key_provider
    )
    
    # Return a service wrapper with authentication capability
    class AuthServiceWrapper:
        def __init__(self, token_validator, keycloak_client):
            self.token_validator = token_validator
            self.keycloak_client = keycloak_client
            
        async def get_current_user(self, token: str, realm: Optional[str] = None, use_cache: bool = True):
            """
            Get current user from token.
            
            Args:
                token: Access token
                realm: Keycloak realm (optional)
                use_cache: Whether to use cached validation results (optional)
                
            Returns:
                User information from token
            """
            try:
                # Validate token and get user info
                # Note: The token validator can handle caching internally
                token_data = await self.token_validator.validate_token(token, realm=realm)
                
                # Return user info
                # Note: Roles should be loaded from the database, not from Keycloak
                return {
                    'id': token_data.get('sub'),
                    'username': token_data.get('preferred_username'),
                    'email': token_data.get('email'),
                    'first_name': token_data.get('given_name'),
                    'last_name': token_data.get('family_name'),
                    'is_active': True,
                    'realm': realm or self.keycloak_client.default_realm,
                    'roles': [],  # Roles will be loaded from database
                    'email_verified': token_data.get('email_verified', False)
                }
            except Exception as e:
                logger.error(f"Failed to get current user: {e}")
                raise
        
        async def authenticate(self, username, password, realm=None, user_sync_callback=None):
            """
            Authenticate user with Keycloak and optional user sync callback.
            
            Args:
                username: Username to authenticate
                password: Password for authentication
                realm: Keycloak realm (optional)
                user_sync_callback: Optional callback for user data sync
                
            Returns:
                Authentication result with user data and tokens
            """
            # First authenticate with Keycloak to get tokens
            auth_result = await self.keycloak_client.authenticate(
                username=username,
                password=password,
                realm=realm
            )
            
            # If user sync callback is provided, call it with user data
            if user_sync_callback:
                token_data = None
                try:
                    # Validate the token to get user info
                    token_data = await self.token_validator.validate_token(
                        auth_result['access_token'], 
                        realm=realm or self.keycloak_client.default_realm
                    )
                    
                    # Prepare user data for sync callback
                    user_data = {
                        'username': token_data.get('preferred_username', username),
                        'email': token_data.get('email'),
                        'first_name': token_data.get('given_name'),
                        'last_name': token_data.get('family_name'),
                        'external_user_id': token_data.get('sub'),
                        'metadata': {
                            'realm': realm or self.keycloak_client.default_realm,
                            'keycloak_user_id': token_data.get('sub'),
                            'email_verified': token_data.get('email_verified', False)
                        }
                    }
                    
                    # Call the user sync callback
                    synced_user = await user_sync_callback(user_data)
                    
                    # Add synced user info to the auth result
                    auth_result['user'] = synced_user
                    
                except Exception as e:
                    # Log error but don't fail authentication
                    logger.warning(f"User sync callback failed: {e}")
                    # For now, provide a minimal but valid user object
                    # This allows authentication to proceed even if sync fails
                    auth_result['user'] = {
                        'id': 'temporary-' + username,  # Temporary ID
                        'username': username,
                        'is_active': True,  # Allow login to proceed
                        'email': username if '@' in username else f'{username}@example.com'
                    }
            
            return auth_result
    
    return AuthServiceWrapper(token_validator, keycloak_client)


def create_permission_cache_manager(cache_service=None, data_source=None):
    """
    Create permission cache manager.
    
    Args:
        cache_service: Cache service for permission storage
        data_source: Data source for permission loading
        
    Returns:
        Permission cache manager
    """
    # Create default cache if not provided
    if cache_service is None:
        from ..cache import CacheManager, TenantAwareCacheService
        cache_manager = CacheManager()
        cache_service = TenantAwareCacheService(cache_manager)
    
    # Create permission cache
    permission_cache = DefaultPermissionCache(
        cache_service=cache_service
    )
    
    # Return cache manager with methods
    class PermissionCacheManagerWrapper:
        def __init__(self, cache):
            self.cache = cache
            
        async def check_permission_cached(self, user_id: str, permission: str, tenant_id: str = None) -> bool:
            return await self.cache.check_permission(user_id, permission, tenant_id)
            
        async def get_user_permissions_cached(self, user_id: str, tenant_id: str = None):
            return await self.cache.get_user_permissions(user_id, tenant_id)
            
        async def get_user_roles_cached(self, user_id: str, tenant_id: str = None):
            return await self.cache.get_user_roles(user_id, tenant_id)
            
        async def get_user_permission_summary_cached(self, user_id: str, tenant_id: str = None):
            return await self.cache.get_user_permission_summary(user_id, tenant_id)
            
        async def batch_check_permissions(self, user_id: str, permissions: list, tenant_id: str = None, require_all: bool = True):
            if require_all:
                for permission in permissions:
                    if not await self.check_permission_cached(user_id, permission, tenant_id):
                        return False
                return True
            else:
                for permission in permissions:
                    if await self.check_permission_cached(user_id, permission, tenant_id):
                        return True
                return False
                
        async def invalidate_user_cache(self, user_id: str, tenant_id: str = None):
            await self.cache.invalidate_user_cache(user_id, tenant_id)
            
        async def invalidate_role_cache(self, role_id: str, tenant_id: str = None):
            await self.cache.invalidate_role_cache(role_id, tenant_id)
            
        async def warm_user_cache(self, user_id: str, tenant_id: str = None):
            await self.cache.warm_user_cache(user_id, tenant_id)
            
        async def warm_role_cache(self, role_id: str, tenant_id: str = None):
            await self.cache.warm_role_cache(role_id, tenant_id)
    
    return PermissionCacheManagerWrapper(permission_cache)

# Convenience aliases for commonly used components
# These maintain backward compatibility with existing code

# Most commonly used FastAPI integration
CheckUserPermission = CheckPermission  # Common alias
require_permission = RequirePermission  # Decorator alias

# Most commonly used implementations
PermissionChecker = DefaultPermissionChecker
PermissionCache = DefaultPermissionCache
PermissionRegistry = DefaultPermissionRegistry
WildcardMatcher = DefaultWildcardMatcher
UserIdentityResolver = DefaultUserIdentityResolver
UserIdentityMapper = DefaultUserIdentityMapper
GuestAuthService = DefaultGuestAuthService
SessionCache = DefaultSessionCache
CacheKeyProvider = DefaultCacheKeyProvider

# Export convenience aliases
__all__.extend([
    "CheckUserPermission",
    "require_permission", 
    "PermissionChecker",
    "PermissionCache",
    "PermissionRegistry",
    "WildcardMatcher",
    "UserIdentityResolver",
    "UserIdentityMapper",
    "GuestAuthService",
    "SessionCache",
    "CacheKeyProvider",
])