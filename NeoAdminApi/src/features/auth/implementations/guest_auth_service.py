"""
GuestAuthService implementation for NeoAdminApi.

Protocol-compliant wrapper around existing guest auth services for neo-commons integration.
"""
from typing import Dict, Any, Optional, List
from loguru import logger

from neo_commons.auth.protocols import GuestAuthServiceProtocol
from src.features.auth.services.guest_auth_service import get_guest_auth_service


class NeoAdminGuestAuthService:
    """
    GuestAuthService implementation for NeoAdminApi.
    
    Wraps the existing guest auth service to provide protocol compliance.
    """
    
    def __init__(self):
        """Initialize guest auth service."""
        # Get the existing guest auth service instance
        self._guest_service = None
    
    async def _get_guest_service(self):
        """Get the guest service instance lazily."""
        if self._guest_service is None:
            self._guest_service = get_guest_auth_service()
        return self._guest_service
    
    async def create_guest_session(
        self,
        ip_address: str,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new guest session.
        
        Args:
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional session metadata
            
        Returns:
            Dictionary with guest session data
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Create session using existing service
            session_data = await guest_service.create_guest_session(
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=metadata.get("referrer") if metadata else None
            )
            
            # Return standardized dictionary format
            return {
                "session_id": session_data["session_id"],
                "session_token": session_data["session_token"],
                "user_type": "guest",
                "permissions": session_data.get("permissions", ["reference_data:read"]),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": session_data.get("created_at"),
                "expires_at": session_data.get("expires_at"),
                "request_count": session_data.get("request_count", 0),
                "rate_limit_remaining": session_data.get("rate_limit", {}).get("requests_remaining", 1000),
                "metadata": session_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to create guest session for IP {ip_address}: {e}")
            raise
    
    async def get_guest_session(
        self,
        session_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing guest session by token.
        
        Args:
            session_token: Session token
            
        Returns:
            Dictionary with guest session data if found, None otherwise
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Get session data using existing service
            session_data = await guest_service.get_session_data(session_token)
            
            if not session_data:
                return None
            
            # Return standardized dictionary format
            return {
                "session_id": session_data["session_id"],
                "session_token": session_data["session_token"],
                "user_type": "guest",
                "permissions": session_data.get("permissions", ["reference_data:read"]),
                "ip_address": session_data.get("ip_address"),
                "user_agent": session_data.get("user_agent"),
                "created_at": session_data.get("created_at"),
                "expires_at": session_data.get("expires_at"),
                "request_count": session_data.get("request_count", 0),
                "rate_limit_remaining": session_data.get("rate_limit", {}).get("requests_remaining", 1000),
                "metadata": session_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to get guest session for token {session_token}: {e}")
            return None
    
    async def get_or_create_guest_session(
        self,
        session_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing session or create new one.
        
        Args:
            session_token: Existing session token (optional)
            ip_address: Client IP address
            user_agent: Client user agent
            referrer: Request referrer
            
        Returns:
            Dictionary with guest session data
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Use existing service method
            session_data = await guest_service.get_or_create_guest_session(
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer
            )
            
            # Return standardized dictionary format
            return {
                "session_id": session_data["session_id"],
                "session_token": session_data["session_token"],
                "user_type": "guest",
                "permissions": session_data.get("permissions", ["reference_data:read"]),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": session_data.get("created_at"),
                "expires_at": session_data.get("expires_at"),
                "request_count": session_data.get("request_count", 0),
                "rate_limit_remaining": session_data.get("rate_limit", {}).get("requests_remaining", 1000),
                "metadata": session_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to get or create guest session for IP {ip_address}: {e}")
            raise
    
    async def update_guest_session(
        self,
        session_token: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update guest session metadata.
        
        Args:
            session_token: Session token
            metadata: Updated metadata
            
        Returns:
            True if successful
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Update session using existing service if available
            if hasattr(guest_service, 'update_session'):
                return await guest_service.update_session(session_token, metadata)
            else:
                logger.debug(f"Session update not supported for token {session_token}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update guest session {session_token}: {e}")
            return False
    
    async def invalidate_guest_session(
        self,
        session_token: str
    ) -> bool:
        """
        Invalidate guest session.
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            True if successful
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Invalidate session using existing service if available
            if hasattr(guest_service, 'invalidate_session'):
                return await guest_service.invalidate_session(session_token)
            else:
                logger.debug(f"Session invalidation not supported for token {session_token}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to invalidate guest session {session_token}: {e}")
            return False
    
    async def get_session_stats(
        self,
        session_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get session statistics.
        
        Args:
            session_token: Session token
            
        Returns:
            Session stats if available
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Get stats using existing service
            return await guest_service.get_session_stats(session_token)
            
        except Exception as e:
            logger.debug(f"Failed to get session stats for {session_token}: {e}")
            return None
    
    async def check_rate_limit(
        self,
        session_token: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Check rate limit for session/IP.
        
        Args:
            session_token: Session token
            ip_address: Client IP address
            
        Returns:
            Rate limit information
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Check rate limit using existing service if available
            if hasattr(guest_service, 'check_rate_limit'):
                return await guest_service.check_rate_limit(session_token, ip_address)
            else:
                # Default rate limit info
                return {
                    "allowed": True,
                    "requests_remaining": 1000,
                    "reset_time": None
                }
                
        except Exception as e:
            logger.error(f"Rate limit check failed for session {session_token}: {e}")
            return {
                "allowed": False,
                "requests_remaining": 0,
                "reset_time": None,
                "error": str(e)
            }
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired guest sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Cleanup using existing service if available
            if hasattr(guest_service, 'cleanup_expired_sessions'):
                return await guest_service.cleanup_expired_sessions()
            else:
                logger.debug("Session cleanup not supported")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_active_session_count(self) -> int:
        """
        Get count of active guest sessions.
        
        Returns:
            Number of active sessions
        """
        try:
            guest_service = await self._get_guest_service()
            
            # Get count using existing service if available
            if hasattr(guest_service, 'get_active_session_count'):
                return await guest_service.get_active_session_count()
            else:
                logger.debug("Active session count not supported")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to get active session count: {e}")
            return 0