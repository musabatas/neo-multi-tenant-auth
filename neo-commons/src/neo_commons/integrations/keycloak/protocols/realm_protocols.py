"""
Protocol definitions for realm management operations.

Provides protocol interfaces for database, cache, Keycloak client, and realm configuration.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List


@runtime_checkable
class DatabaseManagerProtocol(Protocol):
    """Protocol for database operations."""
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute query and return single row."""
        ...
    
    async def execute(self, query: str, *args) -> str:
        """Execute query and return status."""
        ...
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query and return multiple rows."""
        ...


@runtime_checkable
class CacheManagerProtocol(Protocol):
    """Protocol for cache operations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        ...
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        ...


@runtime_checkable
class KeycloakClientProtocol(Protocol):
    """Protocol for Keycloak client operations."""
    
    async def create_realm(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """Create a new realm."""
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
        """Create or update a user."""
        ...


@runtime_checkable
class RealmConfigProtocol(Protocol):
    """Protocol for realm configuration."""
    
    @property
    def realm_cache_ttl(self) -> int:
        """Cache TTL for realm data."""
        ...
    
    @property
    def password_policy(self) -> str:
        """Default password policy."""
        ...
    
    @property
    def default_locales(self) -> List[str]:
        """Default supported locales."""
        ...
    
    @property
    def brute_force_protection(self) -> Dict[str, Any]:
        """Brute force protection settings."""
        ...