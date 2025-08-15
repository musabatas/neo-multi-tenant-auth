"""
Advanced token management protocols and interfaces.

Provides protocol definitions for enhanced token validation and caching.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List
from datetime import datetime, timezone


@runtime_checkable
class CacheManagerProtocol(Protocol):
    """Protocol for cache operations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        ...
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        ...
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        ...


@runtime_checkable
class KeycloakClientProtocol(Protocol):
    """Protocol for Keycloak client operations."""
    
    async def introspect_token(
        self, 
        token: str,
        realm: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """Introspect token with Keycloak."""
        ...
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """Refresh token with Keycloak."""
        ...
    
    async def get_realm_public_key(
        self,
        realm: str
    ) -> str:
        """Get realm public key."""
        ...
    
    async def logout(
        self,
        refresh_token: str,
        realm: str,
        client_id: str,
        client_secret: str
    ) -> bool:
        """Logout user."""
        ...


@runtime_checkable
class TokenConfigProtocol(Protocol):
    """Protocol for token configuration."""
    
    @property
    def keycloak_admin_realm(self) -> str:
        """Admin realm name."""
        ...
    
    @property
    def keycloak_url(self) -> str:
        """Keycloak server URL."""
        ...
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT algorithm for validation."""
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
    def token_cache_ttl(self) -> int:
        """Token cache TTL in seconds."""
        ...
    
    @property
    def public_key_cache_ttl(self) -> int:
        """Public key cache TTL in seconds."""
        ...
    
    @property
    def local_validation_enabled(self) -> bool:
        """Whether local JWT validation is enabled."""
        ...
    
    @property
    def introspection_enabled(self) -> bool:
        """Whether token introspection is enabled."""
        ...
    
    @property
    def dual_validation_threshold(self) -> float:
        """Threshold for dual validation strategy."""
        ...