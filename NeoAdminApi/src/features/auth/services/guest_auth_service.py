"""
Guest authentication service for public endpoints.

Provides session tracking and basic authentication for unauthenticated users
accessing public reference data.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
from loguru import logger

from src.common.cache.client import get_cache
from src.common.utils.datetime import utc_now
from src.common.exceptions.base import ValidationError, RateLimitError


class GuestAuthService:
    """Service for managing guest authentication and session tracking."""
    
    def __init__(self):
        self.cache = get_cache()
        self.session_ttl = 3600  # 1 hour session
        self.max_requests_per_session = 1000  # Rate limiting
        self.max_requests_per_ip = 5000  # Daily IP limit
    
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
        # Check IP rate limits first
        await self._check_ip_rate_limit(ip_address)
        
        # Generate session ID and token
        session_id = f"guest_{uuid.uuid4().hex}"
        session_token = secrets.token_urlsafe(32)
        
        # Create session data
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
            "permissions": ["reference_data:read"],  # Guest permissions
            "rate_limit": {
                "requests_remaining": self.max_requests_per_session,
                "reset_time": (utc_now() + timedelta(seconds=self.session_ttl)).isoformat()
            }
        }
        
        # Store in cache with TTL
        cache_key = f"guest_session:{session_id}"
        await self.cache.set(cache_key, session_data, ttl=self.session_ttl)
        
        # Track IP usage
        await self._track_ip_usage(ip_address)
        
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
            
            # Get session from cache
            session_data = await self.cache.get(cache_key)
            if not session_data:
                return None
            
            # Verify token matches
            if session_data.get("session_token") != token:
                logger.warning(f"Invalid guest token for session {session_id}")
                return None
            
            # Check if session expired
            expires_at = datetime.fromisoformat(session_data["expires_at"].replace("Z", "+00:00"))
            if utc_now() > expires_at:
                await self.cache.delete(cache_key)
                return None
            
            # Update request count and check rate limit
            session_data["request_count"] += 1
            session_data["rate_limit"]["requests_remaining"] -= 1
            
            if session_data["rate_limit"]["requests_remaining"] <= 0:
                logger.warning(f"Rate limit exceeded for guest session {session_id}")
                raise RateLimitError("Session rate limit exceeded")
            
            # Update session in cache
            await self.cache.set(cache_key, session_data, ttl=self.session_ttl)
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error validating guest session: {e}")
            return None
    
    async def get_or_create_guest_session(
        self, 
        session_token: Optional[str],
        ip_address: str,
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
        return await self.create_guest_session(ip_address, user_agent, referrer)
    
    async def _check_ip_rate_limit(self, ip_address: str) -> None:
        """Check if IP address has exceeded daily limits."""
        ip_key = f"guest_ip_limit:{ip_address}"
        ip_data = await self.cache.get(ip_key)
        
        if not ip_data:
            # First request from this IP today
            ip_data = {
                "requests": 1,
                "first_request": utc_now().isoformat(),
                "reset_time": (utc_now() + timedelta(days=1)).isoformat()
            }
            await self.cache.set(ip_key, ip_data, ttl=86400)  # 24 hours
            return
        
        if ip_data["requests"] >= self.max_requests_per_ip:
            reset_time = datetime.fromisoformat(ip_data["reset_time"].replace("Z", "+00:00"))
            logger.warning(f"IP {ip_address} exceeded daily rate limit")
            raise RateLimitError(
                f"Daily request limit exceeded. Resets at {reset_time.isoformat()}"
            )
    
    async def _track_ip_usage(self, ip_address: str) -> None:
        """Track IP address usage for rate limiting."""
        ip_key = f"guest_ip_limit:{ip_address}"
        ip_data = await self.cache.get(ip_key)
        
        if ip_data:
            ip_data["requests"] += 1
            await self.cache.set(ip_key, ip_data, ttl=86400)
    
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
        await self.cache.set(cache_key, session_data, ttl=extension_seconds)
        
        logger.info(f"Extended guest session {session_id} by {extension_seconds} seconds")
        return True


def get_guest_auth_service() -> GuestAuthService:
    """Get guest authentication service instance."""
    return GuestAuthService()