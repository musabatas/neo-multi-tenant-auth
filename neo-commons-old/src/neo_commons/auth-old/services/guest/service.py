"""
Default Guest Authentication Service

Neo-commons implementation of guest authentication with session management,
rate limiting, and configurable business rules.
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger

from ...protocols import GuestAuthServiceProtocol
from ....cache.protocols import TenantAwareCacheProtocol
from ...exceptions import RateLimitError
from ...rate_limiting import AuthRateLimitManager, RateLimitType
from ....utils.datetime import utc_now
from .provider import GuestSessionProvider, DefaultGuestSessionProvider


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
        cache_service: TenantAwareCacheProtocol,
        session_provider: Optional[GuestSessionProvider] = None,
        rate_limiter: Optional[AuthRateLimitManager] = None
    ):
        """
        Initialize guest auth service with protocol-based dependencies.
        
        Args:
            cache_service: Cache service for session storage
            session_provider: Configuration provider for session settings
            rate_limiter: Optional rate limiter (creates default if not provided)
        """
        self.cache = cache_service
        self.session_provider = session_provider or DefaultGuestSessionProvider()
        self.rate_limiter = rate_limiter or AuthRateLimitManager(cache_service)
        
        # Get configuration from provider
        self.session_ttl = self.session_provider.session_ttl
        self.max_requests_per_session = self.session_provider.max_requests_per_session
        self.max_requests_per_ip = self.session_provider.max_requests_per_ip
    
    async def create_guest_session(
        self, 
        ip_address: str,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new guest session for anonymous access.
        
        Args:
            ip_address: Client IP address
            user_agent: Optional browser user agent
            referrer: Optional HTTP referrer
            
        Returns:
            Guest session data with tracking information
            
        Raises:
            RateLimitError: IP has exceeded daily request limit
        """
        # Check IP rate limits first using standardized rate limiter
        await self.rate_limiter.enforce_ip_limit(ip_address)
        
        # Generate session ID and token
        session_id = f"guest_{uuid.uuid4().hex}"
        session_token = secrets.token_urlsafe(32)
        
        # Create session data using session provider for permissions
        session_data = {
            "session_id": session_id,
            "session_token": session_token,
            "user_type": "guest",
            "ip_address": ip_address,
            "user_agent": user_agent,
            "referrer": referrer,
            "created_at": utc_now().isoformat(),
            "expires_at": (utc_now() + timedelta(seconds=self.session_ttl)).isoformat(),
            "request_count": 0,
            "permissions": self.session_provider.get_guest_permissions(),
            "rate_limit": {
                "requests_remaining": self.rate_limiter.get_limit_config(RateLimitType.SESSION).limit,
                "reset_time": (utc_now() + timedelta(seconds=self.session_ttl)).isoformat()
            }
        }
        
        # Store in cache with TTL (use platform namespace for guest sessions)
        cache_key = f"guest_session:{session_id}"
        await self.cache.set(cache_key, session_data, ttl=self.session_ttl, tenant_id=None)
        
        # IP tracking is now handled by AuthRateLimitManager.enforce_ip_limit() above
        
        logger.info(f"Created guest session {session_id} for IP {ip_address}")
        
        return session_data
    
    async def validate_guest_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a guest session token.
        
        Args:
            session_token: Guest session token
            
        Returns:
            Session data if valid, None if invalid/expired
        """
        if not session_token or not session_token.startswith("guest_"):
            return None
        
        try:
            # Extract session ID from token format: guest_{uuid}:{token}
            if ":" not in session_token:
                return None
                
            session_id, token = session_token.split(":", 1)
            cache_key = f"guest_session:{session_id}"
            
            # Get session from cache (platform namespace)
            session_data = await self.cache.get(cache_key, tenant_id=None)
            if not session_data:
                return None
            
            # Verify token matches
            if session_data.get("session_token") != token:
                logger.warning(f"Invalid guest token for session {session_id}")
                return None
            
            # Check if session expired
            expires_at = datetime.fromisoformat(session_data["expires_at"].replace("Z", "+00:00"))
            if utc_now() > expires_at:
                await self.cache.delete(cache_key, tenant_id=None)
                return None
            
            # Use standardized rate limiter for session
            rate_state = await self.rate_limiter.enforce_session_limit(session_id)
            
            # Update session data with new rate limit info
            session_data["request_count"] += 1
            session_data["rate_limit"]["requests_remaining"] = rate_state.requests_remaining
            
            # Update session in cache
            await self.cache.set(cache_key, session_data, ttl=self.session_ttl, tenant_id=None)
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error validating guest session: {e}")
            return None
    
    async def get_or_create_guest_session(
        self, 
        session_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing guest session or create new one.
        
        Args:
            session_token: Existing session token (if any)
            ip_address: Client IP address
            user_agent: Optional browser user agent
            referrer: Optional HTTP referrer
            
        Returns:
            Guest session data
        """
        # Try to validate existing session first
        if session_token:
            session_data = await self.validate_guest_session(session_token)
            if session_data:
                return session_data
        
        # Create new session if none exists or invalid
        if not ip_address:
            raise ValueError("IP address is required to create guest session")
            
        return await self.create_guest_session(ip_address, user_agent, referrer)
    
    async def get_session_stats(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get session statistics and usage information.
        
        Args:
            session_token: Guest session token
            
        Returns:
            Session stats if valid session
        """
        session_data = await self.validate_guest_session(session_token)
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
    
    async def extend_session(self, session_token: str, extension_seconds: int = 3600) -> bool:
        """
        Extend a guest session expiration time.
        
        Args:
            session_token: Guest session token
            extension_seconds: Seconds to extend (default 1 hour)
            
        Returns:
            True if session was extended, False if invalid
        """
        session_data = await self.validate_guest_session(session_token)
        if not session_data:
            return False
        
        # Update expiration time
        new_expires_at = utc_now() + timedelta(seconds=extension_seconds)
        session_data["expires_at"] = new_expires_at.isoformat()
        session_data["rate_limit"]["reset_time"] = new_expires_at.isoformat()
        
        # Update in cache
        session_id = session_data["session_id"]
        cache_key = f"guest_session:{session_id}"
        await self.cache.set(cache_key, session_data, ttl=extension_seconds, tenant_id=None)
        
        logger.info(f"Extended guest session {session_id} by {extension_seconds} seconds")
        return True
    
    async def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate a guest session.
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            True if session was invalidated
        """
        if not session_token or ":" not in session_token:
            return False
            
        try:
            session_id, _ = session_token.split(":", 1)
            cache_key = f"guest_session:{session_id}"
            await self.cache.delete(cache_key, tenant_id=None)
            logger.info(f"Invalidated guest session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate session {session_token}: {e}")
            return False
    
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
    
    async def get_active_session_count(self) -> int:
        """
        Get count of active guest sessions.
        
        Note: This requires scanning Redis keys and may be expensive.
        Consider implementing this with Redis data structures for better performance.
        
        Returns:
            Number of active sessions (approximate)
        """
        # This is a placeholder implementation
        # For production, consider using Redis sets or sorted sets to track active sessions
        logger.debug("Active session count requested (not implemented)")
        return 0
    
    # Note: IP rate limiting is now handled by standardized AuthRateLimitManager
    # Removed legacy _check_ip_rate_limit and _track_ip_usage methods