"""
Service protocols for authentication and authorization.

Protocol definitions for high-level service operations including
guest authentication, caching, and user identity resolution.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class GuestAuthServiceProtocol(Protocol):
    """Protocol for guest authentication service."""
    
    async def create_guest_session(
        self,
        session_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new guest session."""
        ...
    
    async def get_guest_session(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get guest session by ID."""
        ...
    
    async def update_guest_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update guest session data."""
        ...
    
    async def delete_guest_session(
        self,
        session_id: str
    ) -> bool:
        """Delete guest session."""
        ...


@runtime_checkable
class CacheServiceProtocol(Protocol):
    """Protocol for cache service operations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...


@runtime_checkable
class UserIdentityResolverProtocol(Protocol):
    """Protocol for resolving user identity across different ID systems."""
    
    async def resolve_user_id(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> str:
        """
        Resolve user ID to platform user ID.
        
        Handles mapping between Keycloak user IDs and platform user IDs.
        """
        ...
    
    async def get_external_user_id(
        self,
        platform_user_id: str,
        provider: str = "keycloak"
    ) -> Optional[str]:
        """Get external user ID for platform user."""
        ...
    
    async def get_platform_user_id(
        self,
        external_user_id: str,
        provider: str = "keycloak"
    ) -> Optional[str]:
        """Get platform user ID for external user."""
        ...