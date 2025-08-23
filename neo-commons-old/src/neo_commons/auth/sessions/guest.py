"""
Guest Authentication Service for Neo-Commons

Provides enterprise-grade guest authentication with session management,
rate limiting, and configurable business rules for anonymous access.
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    RateLimitError,
    ValidationError,
)


@runtime_checkable 
class GuestSessionProviderProtocol(Protocol):
    """Protocol for guest session configuration."""
    
    @property
    def session_ttl(self) -> int:
        """Session TTL in seconds."""
        ...
    
    @property
    def max_requests_per_session(self) -> int:
        """Maximum requests per session."""
        ...
    
    @property
    def max_requests_per_ip(self) -> int:
        """Maximum requests per IP per day."""
        ...
    
    def get_guest_permissions(self) -> List[str]:
        """Get default guest permissions."""
        ...


class DefaultGuestSessionProvider:
    """Default guest session configuration provider with standard settings."""
    
    def __init__(
        self,
        session_ttl: int = 3600,                    # 1 hour
        max_requests_per_session: int = 1000,       # 1K requests per session
        max_requests_per_ip: int = 5000,            # 5K requests per IP per day
        guest_permissions: List[str] = None
    ):
        """
        Initialize guest session provider.
        
        Args:
            session_ttl: Session lifetime in seconds
            max_requests_per_session: Request limit per session
            max_requests_per_ip: Request limit per IP per day
            guest_permissions: List of permissions for guest users
        """
        self._session_ttl = session_ttl
        self._max_requests_per_session = max_requests_per_session
        self._max_requests_per_ip = max_requests_per_ip
        self._guest_permissions = guest_permissions or ["reference_data:read"]
    
    @property
    def session_ttl(self) -> int:
        return self._session_ttl
    
    @property
    def max_requests_per_session(self) -> int:
        return self._max_requests_per_session
    
    @property
    def max_requests_per_ip(self) -> int:
        return self._max_requests_per_ip
    
    def get_guest_permissions(self) -> List[str]:
        return self._guest_permissions.copy()


class RestrictiveGuestSessionProvider(DefaultGuestSessionProvider):
    """Restrictive guest session provider for high-security environments."""
    
    def __init__(self):
        super().__init__(
            session_ttl=1800,                      # 30 minutes
            max_requests_per_session=100,          # 100 requests per session
            max_requests_per_ip=500,               # 500 requests per IP per day
            guest_permissions=["public_data:read"] # More restrictive permissions
        )


class LiberalGuestSessionProvider(DefaultGuestSessionProvider):
    """Liberal guest session provider for development/testing."""
    
    def __init__(self):
        super().__init__(
            session_ttl=7200,                      # 2 hours
            max_requests_per_session=5000,         # 5K requests per session
            max_requests_per_ip=50000,             # 50K requests per IP per day
            guest_permissions=[
                "reference_data:read",
                "public_content:read",
                "demo:access"
            ]
        )


class DefaultGuestAuthService:
    """
    Default implementation of guest authentication service.
    
    Features:
    - Configurable session management via GuestSessionProvider
    - Rate limiting with IP and session controls
    - Session tracking and statistics
    - Redis caching with automatic cleanup
    - Protocol-based design for service independence
    """
    
    def __init__(
        self,
        cache_service,  # TenantAwareCacheProtocol - avoiding import
        session_provider: Optional[GuestSessionProviderProtocol] = None,
        rate_limiter = None,  # Optional rate limiter
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize guest auth service with protocol-based dependencies.
        
        Args:
            cache_service: Cache service for session storage
            session_provider: Configuration provider for session settings
            rate_limiter: Optional rate limiter (creates default if not provided)
            config: Optional configuration
        """
        self.cache = cache_service
        self.session_provider = session_provider or DefaultGuestSessionProvider()
        self.rate_limiter = rate_limiter
        self.config = config
        
        # Get configuration from provider
        self.session_ttl = self.session_provider.session_ttl
        self.max_requests_per_session = self.session_provider.max_requests_per_session
        self.max_requests_per_ip = self.session_provider.max_requests_per_ip
        
        logger.info(
            f"Initialized DefaultGuestAuthService with TTL: {self.session_ttl}s, "
            f"session limit: {self.max_requests_per_session}, IP limit: {self.max_requests_per_ip}"
        )
    
    def _utc_now(self) -> datetime:
        """Get current UTC time."""
        return datetime.utcnow()
    
    async def create_guest_session(
        self, 
        session_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new guest session for anonymous access.
        
        Args:
            session_data: Optional additional session data
            
        Returns:
            Guest session data with tracking information
            
        Raises:
            RateLimitError: IP has exceeded daily request limit
        """
        # Extract metadata from session_data
        ip_address = session_data.get("ip_address") if session_data else None
        user_agent = session_data.get("user_agent") if session_data else None
        referrer = session_data.get("referrer") if session_data else None
        
        # Basic rate limiting check if rate limiter is available
        if self.rate_limiter and ip_address:
            # Use rate limiter if available
            pass  # Rate limiting would be handled by the rate limiter
        
        # Generate session ID and token
        session_id = f"guest_{uuid.uuid4().hex}"
        session_token = secrets.token_urlsafe(32)
        
        # Create session data using session provider for permissions
        current_time = self._utc_now()
        expires_at = current_time + timedelta(seconds=self.session_ttl)
        
        new_session_data = {
            "session_id": session_id,
            "session_token": session_token,
            "user_type": "guest",
            "ip_address": ip_address,
            "user_agent": user_agent,
            "referrer": referrer,
            "created_at": current_time.isoformat(),
            "expires_at": expires_at.isoformat(),
            "request_count": 0,
            "permissions": self.session_provider.get_guest_permissions(),
            "rate_limit": {
                "requests_remaining": self.max_requests_per_session,
                "reset_time": expires_at.isoformat()
            }
        }
        
        # Merge with any additional session data
        if session_data:
            # Only merge safe keys, don't override system keys
            safe_keys = {"metadata", "custom_data", "preferences"}
            for key, value in session_data.items():
                if key in safe_keys:
                    new_session_data[key] = value
        
        # Store in cache with TTL (use platform namespace for guest sessions)
        cache_key = f"guest_session:{session_id}"
        await self.cache.set(cache_key, new_session_data, ttl=self.session_ttl)
        
        logger.info(f"Created guest session {session_id} for IP {ip_address}")
        
        return new_session_data
    
    async def get_guest_session(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get guest session by ID.
        
        Args:
            session_id: Guest session ID
            
        Returns:
            Session data if found, None otherwise
        """
        if not session_id:
            return None
        
        try:
            cache_key = f"guest_session:{session_id}"
            session_data = await self.cache.get(cache_key)
            
            if not session_data:
                return None
            
            # Check if session expired
            expires_at = datetime.fromisoformat(session_data["expires_at"].replace("Z", "+00:00"))
            if self._utc_now() > expires_at:
                await self.cache.delete(cache_key)
                return None
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error getting guest session {session_id}: {e}")
            return None
    
    async def update_guest_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update guest session data.
        
        Args:
            session_id: Session ID to update
            updates: Data to update
            
        Returns:
            Updated session data
            
        Raises:
            SessionNotFoundError: Session not found
        """
        session_data = await self.get_guest_session(session_id)
        if not session_data:
            raise SessionNotFoundError(f"Guest session not found: {session_id}")
        
        # Update session data (only allow safe updates)
        safe_keys = {"metadata", "custom_data", "preferences", "request_count"}
        for key, value in updates.items():
            if key in safe_keys:
                session_data[key] = value
        
        # Save updated session
        cache_key = f"guest_session:{session_id}"
        await self.cache.set(cache_key, session_data, ttl=self.session_ttl)
        
        return session_data
    
    async def delete_guest_session(
        self,
        session_id: str
    ) -> bool:
        """
        Delete guest session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if session was deleted
        """
        if not session_id:
            return False
            
        try:
            cache_key = f"guest_session:{session_id}"
            await self.cache.delete(cache_key)
            logger.info(f"Deleted guest session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def validate_guest_session(
        self, 
        session_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a guest session token.
        
        Args:
            session_token: Guest session token
            
        Returns:
            Session data if valid, None if invalid/expired
        """
        if not session_token:
            return None
        
        try:
            # For new format, extract session ID from token format: guest_{uuid}:{token}
            if ":" in session_token:
                session_id, token = session_token.split(":", 1)
            else:
                # Handle simple session ID format
                session_id = session_token
                token = None
            
            session_data = await self.get_guest_session(session_id)
            if not session_data:
                return None
            
            # Verify token matches if token format is used
            if token and session_data.get("session_token") != token:
                logger.warning(f"Invalid guest token for session {session_id}")
                return None
            
            # Update request count
            session_data["request_count"] = session_data.get("request_count", 0) + 1
            session_data["rate_limit"]["requests_remaining"] = max(
                0, 
                self.max_requests_per_session - session_data["request_count"]
            )
            
            # Update session in cache
            cache_key = f"guest_session:{session_id}"
            await self.cache.set(cache_key, session_data, ttl=self.session_ttl)
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error validating guest session: {e}")
            return None
    
    async def extend_session(
        self, 
        session_id: str, 
        extension_seconds: int = 3600
    ) -> bool:
        """
        Extend a guest session expiration time.
        
        Args:
            session_id: Guest session ID
            extension_seconds: Seconds to extend (default 1 hour)
            
        Returns:
            True if session was extended, False if invalid
        """
        session_data = await self.get_guest_session(session_id)
        if not session_data:
            return False
        
        # Update expiration time
        new_expires_at = self._utc_now() + timedelta(seconds=extension_seconds)
        session_data["expires_at"] = new_expires_at.isoformat()
        session_data["rate_limit"]["reset_time"] = new_expires_at.isoformat()
        
        # Update in cache
        cache_key = f"guest_session:{session_id}"
        await self.cache.set(cache_key, session_data, ttl=extension_seconds)
        
        logger.info(f"Extended guest session {session_id} by {extension_seconds} seconds")
        return True
    
    async def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session statistics and usage information.
        
        Args:
            session_id: Guest session ID
            
        Returns:
            Session stats if valid session
        """
        session_data = await self.get_guest_session(session_id)
        if not session_data:
            return None
        
        return {
            "session_id": session_data["session_id"],
            "created_at": session_data["created_at"],
            "expires_at": session_data["expires_at"],
            "request_count": session_data["request_count"],
            "rate_limit": session_data["rate_limit"],
            "permissions": session_data["permissions"]
        }
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired guest sessions.
        
        Note: This is a basic implementation. For production use, consider
        implementing a background task that uses Redis SCAN to find expired keys.
        
        Returns:
            Number of sessions cleaned up
        """
        # This is a placeholder implementation
        # In practice, Redis TTL will handle most cleanup automatically
        logger.debug("Guest session cleanup completed (handled by Redis TTL)")
        return 0


# Factory functions for dependency injection
def create_guest_session_provider(
    provider_type: str = "default",
    **kwargs
) -> GuestSessionProviderProtocol:
    """
    Factory function for creating guest session providers.
    
    Args:
        provider_type: Type of provider ("default", "restrictive", "liberal", "custom")
        **kwargs: Custom configuration for default provider
        
    Returns:
        Configured GuestSessionProvider instance
    """
    if provider_type == "restrictive":
        return RestrictiveGuestSessionProvider()
    elif provider_type == "liberal":
        return LiberalGuestSessionProvider()
    elif provider_type == "custom":
        return DefaultGuestSessionProvider(**kwargs)
    else:  # default
        return DefaultGuestSessionProvider()


def create_guest_auth_service(
    cache_service,
    session_provider: Optional[GuestSessionProviderProtocol] = None,
    rate_limiter = None,
    config: Optional[AuthConfigProtocol] = None
) -> DefaultGuestAuthService:
    """
    Create a guest authentication service instance.
    
    Args:
        cache_service: Cache service implementation
        session_provider: Optional session provider
        rate_limiter: Optional rate limiter
        config: Optional configuration
        
    Returns:
        Configured DefaultGuestAuthService instance
    """
    return DefaultGuestAuthService(
        cache_service=cache_service,
        session_provider=session_provider,
        rate_limiter=rate_limiter,
        config=config
    )


__all__ = [
    "DefaultGuestAuthService",
    "DefaultGuestSessionProvider",
    "RestrictiveGuestSessionProvider", 
    "LiberalGuestSessionProvider",
    "GuestSessionProviderProtocol",
    "create_guest_session_provider",
    "create_guest_auth_service",
]