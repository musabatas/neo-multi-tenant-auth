"""
Auth Infrastructure Protocol Interfaces

Comprehensive protocol definitions for enterprise-grade authentication
and authorization infrastructure. These protocols enable:

- Multi-tenant Keycloak integration with realm resolution
- Token validation with dual strategies (local + introspection)  
- Permission checking with tenant context support
- Parameterized cache key management for multi-service deployments
- Configuration injection for service independence
- Intelligent permission caching with wildcard matching
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Tuple, Union, Set
from enum import Enum
from datetime import datetime


class ValidationStrategy(Enum):
    """Token validation strategies."""
    LOCAL = "local"  # Fast JWT validation
    INTROSPECTION = "introspection"  # Secure server-side validation
    DUAL = "dual"  # Both validations


class PermissionScope(Enum):
    """Permission scope levels."""
    PLATFORM = "platform"  # Platform-wide permissions
    TENANT = "tenant"  # Tenant-scoped permissions
    USER = "user"  # User-specific permissions


@runtime_checkable
class AuthConfigProtocol(Protocol):
    """Protocol for authentication configuration injection."""
    
    @property
    def keycloak_url(self) -> str:
        """Keycloak server URL."""
        ...
    
    @property
    def admin_client_id(self) -> str:
        """Admin client ID."""
        ...
    
    @property
    def admin_client_secret(self) -> str:
        """Admin client secret."""
        ...
    
    @property
    def admin_username(self) -> str:
        """Admin username."""
        ...
    
    @property
    def admin_password(self) -> str:
        """Admin password."""
        ...
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT signing algorithm."""
        ...
    
    @property
    def jwt_verify_audience(self) -> bool:
        """Whether to verify JWT audience."""
        ...
    
    @property
    def jwt_verify_issuer(self) -> bool:
        """Whether to verify JWT issuer."""
        ...
    
    @property
    def jwt_audience(self) -> Optional[str]:
        """Expected JWT audience."""
        ...
    
    @property
    def jwt_issuer(self) -> Optional[str]:
        """Expected JWT issuer."""
        ...
    
    @property
    def default_realm(self) -> str:
        """Default realm for authentication."""
        ...
    
    @property
    def default_validation_strategy(self) -> ValidationStrategy:
        """Default token validation strategy."""
        ...


@runtime_checkable
class CacheKeyProviderProtocol(Protocol):
    """Protocol for cache key generation with service namespacing."""
    
    def get_token_cache_key(self, user_id: str, session_id: str) -> str:
        """Generate cache key for user tokens."""
        ...
    
    def get_introspection_cache_key(self, token_hash: str) -> str:
        """Generate cache key for token introspection results."""
        ...
    
    def get_public_key_cache_key(self, realm: str) -> str:
        """Generate cache key for realm public keys."""
        ...
    
    def get_permission_cache_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Generate cache key for user permissions."""
        ...
    
    def get_revocation_cache_key(self, token_hash: str) -> str:
        """Generate cache key for revoked tokens."""
        ...


@runtime_checkable
class RealmProviderProtocol(Protocol):
    """Protocol for realm resolution in multi-tenant environments."""
    
    async def get_admin_realm(self) -> str:
        """
        Get the admin realm name for platform operations.
        
        Returns:
            Admin realm name
        """
        ...
    
    async def get_tenant_realm(self, tenant_id: str) -> str:
        """
        Get realm name for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant-specific realm name
            
        Raises:
            TenantNotFoundError: If tenant doesn't exist
        """
        ...
    
    async def resolve_realm_from_context(self, context: Dict[str, Any]) -> str:
        """
        Resolve realm from request context.
        
        Args:
            context: Request context containing tenant info
            
        Returns:
            Appropriate realm name for the context
        """
        ...
    
    async def get_realm_for_user(self, user_id: str) -> str:
        """
        Get realm for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Realm name where user is registered
        """
        ...


@runtime_checkable
class RealmManagerProtocol(Protocol):
    """Protocol for multi-tenant realm management operations."""
    
    async def get_realm_for_tenant(
        self,
        tenant_id: str,
        use_cache: bool = True
    ) -> str:
        """
        Get the Keycloak realm name for a tenant from database.
        
        CRITICAL: Never assume realm naming pattern!
        Always read from database column `tenants.external_auth_realm`
        
        Args:
            tenant_id: Tenant UUID
            use_cache: Whether to use cache
            
        Returns:
            Realm name from database
            
        Raises:
            NotFoundError: Tenant not found
            ExternalServiceError: Tenant not active or realm not configured
        """
        ...
    
    async def ensure_realm_exists(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ensure a realm exists in Keycloak with proper configuration.
        
        Args:
            realm_name: Unique realm identifier
            display_name: Human-readable realm name
            settings: Additional realm settings
            
        Returns:
            True if realm exists or was created
            
        Raises:
            ExternalServiceError: Failed to create realm
        """
        ...
    
    async def configure_realm_client(
        self,
        realm_name: str,
        client_id: str,
        client_name: Optional[str] = None,
        redirect_uris: Optional[List[str]] = None,
        web_origins: Optional[List[str]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Configure a client application in a realm.
        
        Args:
            realm_name: Realm name
            client_id: Client identifier
            client_name: Client display name
            redirect_uris: Allowed redirect URIs
            web_origins: Allowed web origins for CORS
            settings: Additional client settings
            
        Returns:
            Client configuration
            
        Raises:
            ExternalServiceError: Failed to configure client
        """
        ...
    
    async def create_tenant_realm(
        self,
        tenant_id: str,
        realm_name: str,
        display_name: str,
        admin_email: str,
        admin_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a complete realm setup for a new tenant.
        
        Args:
            tenant_id: Tenant UUID
            realm_name: Unique realm identifier
            display_name: Tenant display name
            admin_email: Admin user email
            admin_password: Admin password (generated if not provided)
            
        Returns:
            Realm setup information including admin credentials
            
        Raises:
            ConflictError: Realm already exists
            ExternalServiceError: Setup failed
        """
        ...
    
    async def deactivate_tenant_realm(
        self,
        tenant_id: str
    ) -> bool:
        """
        Deactivate a tenant's realm (soft delete).
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if deactivated successfully
        """
        ...
    
    async def clear_tenant_realm_cache(self, tenant_id: str) -> bool:
        """
        Clear cached realm information for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if cache cleared
        """
        ...


@runtime_checkable  
class KeycloakClientProtocol(Protocol):
    """Protocol for Keycloak operations with realm parameterization."""
    
    async def authenticate(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and get tokens.
        
        Args:
            username: Username or email
            password: User password
            realm: Realm name for authentication (optional, uses default if None)
            
        Returns:
            Token response with access_token, refresh_token, expires_in, realm, authenticated_at
            
        Raises:
            UnauthorizedError: Invalid credentials
            ExternalServiceError: Keycloak connection failed
        """
        ...
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Introspect token to check if active and get claims.
        
        Args:
            token: Access token to introspect
            realm: Realm name for introspection (optional, uses default if None)
            
        Returns:
            Introspection response with active status and claims
            
        Raises:
            UnauthorizedError: Token is invalid or expired
            ExternalServiceError: Keycloak connection failed
        """
        ...
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            realm: Realm name for token refresh (optional, uses default if None)
            
        Returns:
            New token response with access_token, refresh_token, realm, refreshed_at
            
        Raises:
            UnauthorizedError: Refresh token invalid or expired
            ExternalServiceError: Keycloak connection failed
        """
        ...
    
    async def get_userinfo(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user information from token.
        
        Args:
            token: Access token
            realm: Realm name for userinfo (optional, uses default if None)
            
        Returns:
            User information from token
            
        Raises:
            UnauthorizedError: Token is invalid
            ExternalServiceError: Keycloak connection failed
        """
        ...
    
    async def logout(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> bool:
        """
        Logout user session.
        
        Args:
            refresh_token: Refresh token to revoke
            realm: Realm name for logout (optional, uses default if None)
            
        Returns:
            True if logout successful
        """
        ...
    
    async def decode_token(
        self,
        token: str,
        realm: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Decode and optionally validate JWT token.
        
        Args:
            token: JWT token to decode
            realm: Realm name for validation (optional, uses default if None)
            validate: Whether to validate token signature
            
        Returns:
            Decoded token claims
            
        Raises:
            UnauthorizedError: Token invalid or expired
        """
        ...
    
    async def get_realm_public_key(
        self,
        realm: Optional[str] = None,
        force_refresh: bool = False
    ) -> str:
        """
        Get public key for realm with caching.
        
        Args:
            realm: Realm name (optional, uses default if None)
            force_refresh: Force refresh cached key
            
        Returns:
            Public key in PEM format
        """
        ...
    
    # Admin operations for realm management
    async def create_realm(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """
        Create a new realm (admin operation).
        
        Args:
            realm_name: Unique realm identifier
            display_name: Human-readable realm name
            enabled: Whether realm is enabled
            
        Returns:
            True if realm created successfully
            
        Raises:
            ConflictError: Realm already exists
            ExternalServiceError: Creation failed
        """
        ...
    
    async def get_user_by_username(
        self,
        username: str,
        realm: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by username in a realm.
        
        Args:
            username: Username to search for
            realm: Realm name (optional, uses default if None)
            
        Returns:
            User data if found, None otherwise
        """
        ...
    
    async def create_or_update_user(
        self,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        realm: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create or update a user in Keycloak.
        
        Args:
            username: Username
            email: Email address
            first_name: First name
            last_name: Last name
            realm: Realm name (optional, uses default if None)
            attributes: Additional user attributes
            
        Returns:
            User data
        """
        ...


@runtime_checkable
class TokenValidatorProtocol(Protocol):
    """Protocol for token validation with strategy selection."""
    
    async def validate_token(
        self,
        token: str,
        realm: str,
        strategy: ValidationStrategy = ValidationStrategy.LOCAL,
        critical: bool = False
    ) -> Dict[str, Any]:
        """
        Validate token using specified strategy.
        
        Args:
            token: JWT token to validate
            realm: Realm name for validation
            strategy: Validation strategy to use
            critical: Whether this is critical operation (forces introspection)
            
        Returns:
            Token claims with validation metadata
            
        Raises:
            UnauthorizedError: Token invalid or expired
        """
        ...
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        realm: str
    ) -> Dict[str, Any]:
        """
        Authenticate user with username/password.
        
        Args:
            username: User's username
            password: User's password
            realm: Authentication realm
            
        Returns:
            Token data with user information
            
        Raises:
            UnauthorizedError: Invalid credentials
        """
        ...
    
    async def is_token_revoked(self, token: str) -> bool:
        """
        Check if token has been revoked.
        
        Args:
            token: Token to check
            
        Returns:
            True if token is revoked
        """
        ...
    
    async def revoke_token(
        self,
        token: str,
        realm: str
    ) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            realm: Realm name
            
        Returns:
            True if revoked successfully
        """
        ...
    
    async def refresh_if_needed(
        self,
        token: str,
        refresh_token: str,
        realm: str
    ) -> Optional[Tuple[str, str]]:
        """
        Check if token needs refresh and refresh if necessary.
        
        Args:
            token: Current access token
            refresh_token: Refresh token
            realm: Realm name
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if refreshed
        """
        ...
    
    async def clear_user_tokens(self, user_id: str) -> int:
        """
        Clear all cached tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens cleared
        """
        ...


@runtime_checkable
class PermissionValidatorProtocol(Protocol):
    """Protocol for permission checking with tenant context."""
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None,
        scope: PermissionScope = PermissionScope.PLATFORM
    ) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            user_id: User identifier
            permission: Permission code (e.g., "users:read")
            tenant_id: Optional tenant context
            scope: Permission scope level
            
        Returns:
            True if user has permission
        """
        ...
    
    async def check_any_permission(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        scope: PermissionScope = PermissionScope.PLATFORM
    ) -> bool:
        """
        Check if user has any of the specified permissions.
        
        Args:
            user_id: User identifier
            permissions: List of permission codes
            tenant_id: Optional tenant context
            scope: Permission scope level
            
        Returns:
            True if user has any permission
        """
        ...
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        scope: Optional[PermissionScope] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for user.
        
        Args:
            user_id: User identifier
            tenant_id: Optional tenant context
            scope: Optional scope filter
            
        Returns:
            List of permission objects
        """
        ...
    
    async def invalidate_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Invalidate cached permissions for user.
        
        Args:
            user_id: User identifier
            tenant_id: Optional tenant context
        """
        ...


@runtime_checkable
class PermissionRegistryProtocol(Protocol):
    """Protocol for permission registry and definitions."""
    
    def get_platform_permissions(self) -> List[Dict[str, Any]]:
        """
        Get all platform-level permissions.
        
        Returns:
            List of platform permission definitions
        """
        ...
    
    def get_tenant_permissions(self) -> List[Dict[str, Any]]:
        """
        Get all tenant-level permissions.
        
        Returns:
            List of tenant permission definitions
        """
        ...
    
    def get_permission_groups(self) -> Dict[str, List[str]]:
        """
        Get permission groups for easier assignment.
        
        Returns:
            Dictionary mapping group names to permission lists
        """
        ...
    
    def validate_permission(self, permission: Dict[str, Any]) -> bool:
        """
        Validate permission definition structure.
        
        Args:
            permission: Permission definition to validate
            
        Returns:
            True if permission is valid
        """
        ...
    
    def find_permission(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Find permission by code.
        
        Args:
            code: Permission code to find
            
        Returns:
            Permission definition if found
        """
        ...
    
    def get_permissions_by_scope(self, scope: PermissionScope) -> List[Dict[str, Any]]:
        """
        Get permissions filtered by scope.
        
        Args:
            scope: Permission scope to filter by
            
        Returns:
            List of permissions for the scope
        """
        ...


@runtime_checkable
class PermissionDecoratorProtocol(Protocol):
    """Protocol for permission decorators with metadata extraction."""
    
    def extract_permission_metadata(self, func: Any) -> List[Dict[str, Any]]:
        """
        Extract permission metadata from decorated function.
        
        Args:
            func: Function to extract metadata from
            
        Returns:
            List of permission requirements
        """
        ...
    
    def has_permissions(self, func: Any) -> bool:
        """
        Check if function has permission requirements.
        
        Args:
            func: Function to check
            
        Returns:
            True if function has permissions
        """
        ...
    
    def create_permission_decorator(
        self,
        permission: Union[str, List[str]],
        scope: PermissionScope = PermissionScope.PLATFORM,
        description: Optional[str] = None,
        is_dangerous: bool = False,
        requires_mfa: bool = False,
        requires_approval: bool = False,
        any_of: bool = False
    ) -> Any:
        """
        Create permission decorator with specified requirements.
        
        Args:
            permission: Permission code(s) required
            scope: Permission scope level
            description: Human-readable description
            is_dangerous: Whether this is dangerous operation
            requires_mfa: Whether MFA is required
            requires_approval: Whether approval workflow required
            any_of: If True, needs ANY permission; if False, needs ALL
            
        Returns:
            Decorator function
        """
        ...


@runtime_checkable
class PermissionCheckerProtocol(Protocol):
    """Protocol for comprehensive permission checking with caching."""
    
    async def check_permission(
        self,
        user_id: str,
        permissions: List[str],
        scope: str = "platform",
        tenant_id: Optional[str] = None,
        any_of: bool = False
    ) -> bool:
        """
        Check if user has required permissions.
        
        Args:
            user_id: User identifier
            permissions: List of permission codes to check
            scope: Permission scope (platform/tenant/user)
            tenant_id: Optional tenant context
            any_of: If True, requires ANY permission; if False, requires ALL
            
        Returns:
            True if user has required permissions
        """
        ...
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Optional tenant context
            
        Returns:
            List of user permissions with metadata
        """
        ...


@runtime_checkable
class GuestAuthServiceProtocol(Protocol):
    """Protocol for guest authentication and session management."""
    
    async def get_or_create_guest_session(
        self,
        session_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get or create a guest session.
        
        Args:
            session_token: Existing session token
            ip_address: Client IP address
            user_agent: Client user agent
            referrer: Request referrer
            
        Returns:
            Guest session data
            
        Raises:
            RateLimitError: If rate limits exceeded
        """
        ...
    
    async def get_session_stats(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get guest session statistics.
        
        Args:
            session_token: Session token
            
        Returns:
            Session statistics if found
        """
        ...


@runtime_checkable
class CacheServiceProtocol(Protocol):
    """Protocol for cache service operations."""
    
    async def get(self, key: str) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        ...
    
    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
        """
        ...
    
    async def health_check(self) -> bool:
        """
        Check cache service health.
        
        Returns:
            True if cache is healthy
        """
        ...


@runtime_checkable
class UserIdentityResolverProtocol(Protocol):
    """
    Protocol for resolving user identities across different authentication providers.
    
    This protocol handles the critical mapping between external authentication provider
    user IDs (e.g., Keycloak) and internal platform user IDs. It provides a unified
    interface for user ID resolution with caching support and fallback strategies.
    
    Key Use Cases:
    - Map Keycloak `sub` claims to platform user IDs
    - Handle both authenticated and service-to-service scenarios
    - Support multiple authentication providers (future expansion)
    - Provide consistent user identity across all platform services
    """
    
    async def resolve_platform_user_id(
        self,
        external_provider: str,
        external_id: str,
        fallback_to_external: bool = True
    ) -> Optional[str]:
        """
        Resolve external authentication provider ID to platform user ID.
        
        Args:
            external_provider: Authentication provider name (e.g., "keycloak")
            external_id: External user ID from the provider
            fallback_to_external: If True, return external_id when no mapping found
            
        Returns:
            Platform user ID if mapping exists, external_id if fallback enabled, None otherwise
            
        Raises:
            ExternalServiceError: Provider lookup failed
        """
        ...
    
    async def resolve_user_context(
        self,
        user_id: str,
        provider_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve user ID to complete user context with platform metadata.
        
        This method attempts to determine if the provided user_id is already
        a platform user ID or needs mapping from an external provider.
        
        Args:
            user_id: User ID (could be platform or external)
            provider_hint: Optional hint about the likely provider
            
        Returns:
            Dictionary containing:
            - platform_user_id: Internal platform user ID
            - external_user_id: Original external ID (if mapped)
            - provider: Authentication provider name
            - user_metadata: Additional user information
            - is_mapped: Whether ID mapping was performed
            
        Raises:
            NotFoundError: User not found in any context
        """
        ...
    
    async def cache_user_mapping(
        self,
        external_provider: str,
        external_id: str,
        platform_user_id: str,
        ttl: int = 3600
    ) -> None:
        """
        Cache user ID mapping for faster subsequent lookups.
        
        Args:
            external_provider: Authentication provider name
            external_id: External user ID
            platform_user_id: Platform user ID
            ttl: Cache time-to-live in seconds
        """
        ...
    
    async def invalidate_user_mapping(
        self,
        user_id: str,
        provider: Optional[str] = None
    ) -> None:
        """
        Invalidate cached user ID mappings.
        
        Args:
            user_id: User ID (platform or external)
            provider: Optional provider to limit invalidation scope
        """
        ...
    
    async def get_supported_providers(self) -> List[str]:
        """
        Get list of supported authentication providers.
        
        Returns:
            List of provider names (e.g., ["keycloak", "oauth2", "saml"])
        """
        ...


@runtime_checkable
class PermissionCacheProtocol(Protocol):
    """
    Protocol for permission caching implementations.
    
    Provides intelligent caching strategies for permission data including
    user permissions, roles, and permission summaries with tenant isolation.
    """
    
    async def check_permission_cached(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission using cached data.
        
        Args:
            user_id: User UUID
            permission: Permission name (e.g., "users:read")
            tenant_id: Optional tenant context
            
        Returns:
            True if user has the permission
        """
        ...
    
    async def get_user_permissions_cached(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user with caching.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details
        """
        ...
    
    async def warm_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Warm the cache for a user by pre-loading permission data.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
        """
        ...
    
    async def invalidate_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Invalidate all cached data for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant to clear specific cache
        """
        ...


@runtime_checkable
class PermissionDataSourceProtocol(Protocol):
    """
    Protocol for permission data sources.
    
    Defines the interface for loading permission data from databases
    or other storage systems.
    """
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission in data source."""
        ...
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user permissions from data source."""
        ...
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user roles from data source."""
        ...
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """Get user permission summary from data source."""
        ...
    
    async def get_users_with_role(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get list of user IDs with specific role."""
        ...


@runtime_checkable
class WildcardMatcherProtocol(Protocol):
    """
    Protocol for wildcard permission matching.
    
    Provides pattern matching for permission strings including
    wildcard support (e.g., "users:*" matches "users:read").
    """
    
    def matches_permission(
        self,
        required_permission: str,
        granted_permission: str
    ) -> bool:
        """
        Check if granted permission matches required permission.
        
        Args:
            required_permission: Permission being checked
            granted_permission: Permission that was granted
            
        Returns:
            True if granted permission satisfies required permission
        """
        ...
    
    def expand_wildcard_permissions(
        self,
        permissions: List[str]
    ) -> Set[str]:
        """
        Expand wildcard permissions to include all possible matches.
        
        Args:
            permissions: List of permission strings (may include wildcards)
            
        Returns:
            Set of expanded permission strings
        """
        ...