"""
Core authentication protocols and contracts.

Defines the fundamental protocol interfaces for authentication configuration,
cache management, and core auth operations used throughout the auth system.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable
from .enums import ValidationStrategy, CacheStrategy


@runtime_checkable
class AuthConfigProtocol(Protocol):
    """
    Protocol for authentication configuration dependency injection.
    
    Provides access to all authentication-related configuration values
    including Keycloak settings, JWT validation parameters, and defaults.
    """
    
    @property
    def keycloak_url(self) -> str:
        """Keycloak server base URL."""
        ...
    
    @property
    def admin_client_id(self) -> str:
        """Admin client ID for Keycloak operations."""
        ...
    
    @property
    def admin_client_secret(self) -> str:
        """Admin client secret for Keycloak operations."""
        ...
    
    @property
    def admin_username(self) -> str:
        """Admin username for Keycloak management."""
        ...
    
    @property
    def admin_password(self) -> str:
        """Admin password for Keycloak management."""
        ...
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT signing algorithm (e.g., RS256)."""
        ...
    
    @property
    def jwt_verify_audience(self) -> bool:
        """Whether to verify JWT audience claims."""
        ...
    
    @property
    def jwt_verify_issuer(self) -> bool:
        """Whether to verify JWT issuer claims."""
        ...
    
    @property
    def jwt_audience(self) -> Optional[str]:
        """Expected JWT audience value."""
        ...
    
    @property
    def jwt_issuer(self) -> Optional[str]:
        """Expected JWT issuer value."""
        ...
    
    @property
    def default_realm(self) -> str:
        """Default Keycloak realm for authentication."""
        ...
    
    @property
    def default_validation_strategy(self) -> ValidationStrategy:
        """Default token validation strategy."""
        ...
    
    @property
    def cache_strategy(self) -> CacheStrategy:
        """Default caching strategy for auth data."""
        ...
    
    @property
    def cache_ttl_permissions(self) -> int:
        """Cache TTL for permission data (seconds)."""
        ...
    
    @property
    def cache_ttl_tokens(self) -> int:
        """Cache TTL for token validation (seconds)."""
        ...
    
    @property
    def cache_ttl_sessions(self) -> int:
        """Cache TTL for session data (seconds)."""
        ...


@runtime_checkable
class CacheKeyProviderProtocol(Protocol):
    """
    Protocol for providing consistent cache keys across the auth system.
    
    Ensures cache key generation follows consistent patterns with proper
    namespacing and collision avoidance across different auth operations.
    """
    
    def get_user_permissions_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Generate cache key for user permissions."""
        ...
    
    def get_user_roles_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """Generate cache key for user roles."""
        ...
    
    def get_permission_check_key(
        self, 
        user_id: str, 
        permission: str, 
        tenant_id: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> str:
        """Generate cache key for permission check results."""
        ...
    
    def get_token_validation_key(self, token_hash: str, realm: str) -> str:
        """Generate cache key for token validation results."""
        ...
    
    def get_realm_config_key(self, realm: str) -> str:
        """Generate cache key for realm configuration."""
        ...
    
    def get_user_session_key(self, user_id: str, session_id: str) -> str:
        """Generate cache key for user session data."""
        ...
    
    def get_permission_wildcard_key(self, pattern: str, tenant_id: Optional[str] = None) -> str:
        """Generate cache key for wildcard permission patterns."""
        ...
    
    def get_realm_public_key_cache_key(self, realm: str) -> str:
        """Generate cache key for realm public keys."""
        ...
    
    def get_user_identity_mapping_key(self, external_id: str, provider: str) -> str:
        """Generate cache key for user identity mappings."""
        ...


@runtime_checkable
class HealthCheckProtocol(Protocol):
    """
    Protocol for health checking auth system components.
    
    Provides standardized health check interface for monitoring
    the availability and performance of auth components.
    """
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the component.
        
        Returns:
            Dictionary with health status information:
            - status: 'healthy', 'degraded', or 'unhealthy'
            - latency: Response time in milliseconds
            - details: Additional health information
        """
        ...
    
    async def ready_check(self) -> bool:
        """
        Check if component is ready to handle requests.
        
        Returns:
            True if component is ready, False otherwise
        """
        ...


@runtime_checkable
class MetricsProtocol(Protocol):
    """
    Protocol for collecting auth system metrics.
    
    Provides standardized interface for collecting performance
    and usage metrics from auth components.
    """
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        ...
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric value."""
        ...
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        ...
    
    def record_timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric in milliseconds."""
        ...


@runtime_checkable
class AuditLogProtocol(Protocol):
    """
    Protocol for audit logging auth events.
    
    Provides standardized interface for logging security-relevant
    events with proper context and metadata.
    """
    
    async def log_authentication_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log authentication-related events."""
        ...
    
    async def log_authorization_event(
        self,
        event_type: str,
        user_id: str,
        permission: str,
        resource: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log authorization-related events."""
        ...
    
    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Log security-related events."""
        ...


@runtime_checkable
class RateLimiterProtocol(Protocol):
    """
    Protocol for rate limiting auth operations.
    
    Provides rate limiting capabilities to prevent abuse
    and ensure fair usage of auth resources.
    """
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int = 1
    ) -> Dict[str, Any]:
        """
        Check if operation is within rate limits.
        
        Returns:
            Dictionary with rate limit information:
            - allowed: Whether operation is allowed
            - remaining: Remaining requests in window
            - reset_time: When the window resets
            - retry_after: Seconds to wait before retry
        """
        ...
    
    async def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a specific key."""
        ...


__all__ = [
    "AuthConfigProtocol",
    "CacheKeyProviderProtocol", 
    "HealthCheckProtocol",
    "MetricsProtocol",
    "AuditLogProtocol",
    "RateLimiterProtocol",
]