"""
Keycloak integration protocols.

Protocol definitions for Keycloak operations including realm management,
token operations, and user management across multi-tenant environments.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from ..core import ValidationStrategy


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
            UserNotFoundError: If tenant doesn't exist
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
            UserNotFoundError: Tenant not found
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
        realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user and get tokens.
        
        Args:
            username: Username or email
            password: User password
            realm: Realm name for authentication (optional, uses default if None)
            client_id: Client ID for authentication (optional, uses default if None)
            client_secret: Client secret for authentication (optional)
            
        Returns:
            Token response with access_token, refresh_token, expires_in, realm, authenticated_at
            
        Raises:
            AuthenticationError: Invalid credentials
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
            AuthenticationError: Token is invalid or expired
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
            AuthenticationError: Refresh token invalid or expired
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
            AuthenticationError: Token is invalid
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
            AuthenticationError: Token invalid or expired
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
    """Protocol for JWT token validation with multiple strategies."""
    
    async def validate_token(
        self,
        token: str,
        realm: str,
        strategy: ValidationStrategy = ValidationStrategy.LOCAL,
        critical: bool = False
    ) -> Dict[str, Any]:
        """
        Validate JWT token using specified strategy.
        
        Args:
            token: JWT token to validate
            realm: Realm name for validation
            strategy: Validation strategy to use
            critical: Whether this is critical operation (forces introspection)
            
        Returns:
            Validated token claims and metadata
            
        Raises:
            AuthenticationError: Token is invalid or expired
            ExternalServiceError: Validation service unavailable
        """
        ...
    
    async def is_token_revoked(self, token: str) -> bool:
        """
        Check if a token has been revoked.
        
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
        Revoke a token (add to revocation list).
        
        Args:
            token: Token to revoke
            realm: Realm name
            
        Returns:
            True if revoked successfully
        """
        ...
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        realm: str
    ) -> Dict[str, Any]:
        """
        Authenticate user with username/password and return token data.
        
        Args:
            username: User's username or email
            password: User's password  
            realm: Authentication realm
            
        Returns:
            Token data with user information and metadata
            
        Raises:
            AuthenticationError: Invalid credentials
        """
        ...


__all__ = [
    "RealmProviderProtocol",
    "RealmManagerProtocol", 
    "KeycloakClientProtocol",
    "TokenValidatorProtocol",
]