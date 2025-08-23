"""
Base authentication protocols and enums.

Core protocol definitions for authentication configuration and
shared enums used across the auth module.
"""

from typing import Optional, Protocol, runtime_checkable
from enum import Enum


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
    """Protocol for providing cache keys for authentication data."""
    
    def get_user_permissions_key(self, user_id: str, tenant_id: str) -> str:
        """Get cache key for user permissions."""
        ...
    
    def get_user_roles_key(self, user_id: str, tenant_id: str) -> str:
        """Get cache key for user roles."""
        ...
    
    def get_permission_check_key(self, user_id: str, permission: str, 
                                 resource_id: Optional[str] = None) -> str:
        """Get cache key for permission check results."""
        ...
    
    def get_token_validation_key(self, token_hash: str, realm: str) -> str:
        """Get cache key for token validation results."""
        ...
    
    def get_realm_config_key(self, realm: str) -> str:
        """Get cache key for realm configuration."""
        ...
    
    def get_user_session_key(self, user_id: str, session_id: str) -> str:
        """Get cache key for user session data."""
        ...
    
    def get_permission_wildcard_key(self, pattern: str, tenant_id: str) -> str:
        """Get cache key for wildcard permission patterns."""
        ...