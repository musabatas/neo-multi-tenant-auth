"""
Authentication and Authorization Protocol Definitions

Protocol interfaces for authentication services, permission management,
and authorization workflows. These protocols define the contracts that
concrete implementations must follow.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class AuthServiceProtocol(Protocol):
    """Protocol for authentication service implementations."""

    async def authenticate(
        self, 
        username: str, 
        password: str, 
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user credentials and return token information.
        
        Args:
            username: User's username or email
            password: User's password
            tenant_id: Optional tenant context for multi-tenant auth
            
        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            AuthenticationError: When credentials are invalid
            TenantNotFoundError: When tenant_id is invalid
        """
        ...

    async def get_current_user(
        self, 
        token: str, 
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get current user information from token.
        
        Args:
            token: JWT access token
            use_cache: Whether to use cached user data
            
        Returns:
            Dictionary containing user information
            
        Raises:
            TokenExpiredError: When token has expired
            TokenInvalidError: When token is malformed or invalid
        """
        ...

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary containing new access_token and expires_in
            
        Raises:
            TokenExpiredError: When refresh token has expired
            TokenInvalidError: When refresh token is invalid
        """
        ...

    async def validate_token(
        self, 
        token: str, 
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Validate token without retrieving user data.
        
        Args:
            token: JWT access token to validate
            tenant_id: Optional tenant context for validation
            
        Returns:
            True if token is valid, False otherwise
        """
        ...


@runtime_checkable
class PermissionServiceProtocol(Protocol):
    """Protocol for permission and authorization service implementations."""

    async def check_permission(
        self, 
        user_id: str, 
        permission: str, 
        tenant_id: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has specific permission with sub-millisecond performance.
        
        Args:
            user_id: User identifier
            permission: Permission string (e.g., "users:read", "tenants:admin")
            tenant_id: Tenant context for permission check
            resource_id: Optional specific resource identifier
            
        Returns:
            True if user has permission, False otherwise
        """
        ...

    async def get_user_permissions(
        self, 
        user_id: str, 
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user with caching.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant context for permissions
            
        Returns:
            List of permission dictionaries with details
        """
        ...

    async def get_user_roles(
        self, 
        user_id: str, 
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all roles assigned to a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant context for roles
            
        Returns:
            List of role dictionaries with details
        """
        ...

    async def invalidate_user_cache(
        self, 
        user_id: str, 
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Invalidate cached permissions and roles for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant context for cache invalidation
        """
        ...

    async def bulk_check_permissions(
        self, 
        user_id: str, 
        permissions: List[str],
        tenant_id: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Check multiple permissions efficiently.
        
        Args:
            user_id: User identifier
            permissions: List of permission strings to check
            tenant_id: Tenant context for permission checks
            
        Returns:
            Dictionary mapping permission strings to boolean results
        """
        ...