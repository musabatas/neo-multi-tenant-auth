"""
Session-Specific Caching for Neo-Commons

Provides specialized caching strategies for session management including
guest sessions, authenticated sessions, and session metadata with 
intelligent TTL management and tenant isolation.
"""
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from datetime import datetime, timedelta
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    CacheError,
    SessionError,
)


@runtime_checkable
class SessionCacheProtocol(Protocol):
    """Protocol for session-specific caching operations."""
    
    async def get_session(
        self, 
        session_id: str, 
        session_type: str = "guest"
    ) -> Optional[Dict[str, Any]]:
        """Get session data by ID and type."""
        ...
    
    async def set_session(
        self, 
        session_id: str, 
        session_data: Dict[str, Any], 
        ttl: Optional[int] = None,
        session_type: str = "guest"
    ) -> None:
        """Store session data with TTL."""
        ...
    
    async def delete_session(
        self, 
        session_id: str, 
        session_type: str = "guest"
    ) -> None:
        """Delete session data."""
        ...
    
    async def extend_session_ttl(
        self, 
        session_id: str, 
        extension_seconds: int,
        session_type: str = "guest"
    ) -> bool:
        """Extend session TTL."""
        ...
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session cache statistics."""
        ...


class DefaultSessionCache:
    """
    Default implementation of session-specific caching.
    
    Features:
    - Session type-based key management
    - Intelligent TTL strategies
    - Bulk session operations
    - Session metadata tracking
    - Tenant isolation support
    - Performance metrics
    """
    
    def __init__(
        self,
        cache_service,  # TenantAwareCacheProtocol - avoiding import
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize session cache.
        
        Args:
            cache_service: Underlying cache service
            config: Optional configuration
        """
        self.cache = cache_service
        self.config = config
        
        # Configuration with defaults
        self.default_guest_ttl = 3600  # 1 hour
        self.default_auth_ttl = 28800  # 8 hours
        self.default_admin_ttl = 14400  # 4 hours
        self.session_prefix = "session"
        
        # Load from config if available
        if config:
            self.default_guest_ttl = getattr(config, 'GUEST_SESSION_TTL', 3600)
            self.default_auth_ttl = getattr(config, 'AUTH_SESSION_TTL', 28800)
            self.default_admin_ttl = getattr(config, 'ADMIN_SESSION_TTL', 14400)
            self.session_prefix = getattr(config, 'SESSION_CACHE_PREFIX', 'session')
        
        # Performance tracking
        self.stats = {
            'gets': 0,
            'sets': 0,
            'deletes': 0,
            'hits': 0,
            'misses': 0,
            'extensions': 0
        }
        
        logger.info(
            f"Initialized DefaultSessionCache with TTLs - "
            f"guest: {self.default_guest_ttl}s, auth: {self.default_auth_ttl}s, "
            f"admin: {self.default_admin_ttl}s"
        )
    
    def _build_cache_key(self, session_id: str, session_type: str = "guest") -> str:
        """Build cache key for session."""
        return f"{self.session_prefix}:{session_type}:{session_id}"
    
    def _get_default_ttl(self, session_type: str) -> int:
        """Get default TTL based on session type."""
        ttl_map = {
            "guest": self.default_guest_ttl,
            "authenticated": self.default_auth_ttl,
            "admin": self.default_admin_ttl,
            "user": self.default_auth_ttl
        }
        return ttl_map.get(session_type, self.default_guest_ttl)
    
    async def get_session(
        self, 
        session_id: str, 
        session_type: str = "guest"
    ) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID and type.
        
        Args:
            session_id: Session identifier
            session_type: Type of session (guest, authenticated, admin)
            
        Returns:
            Session data if found, None otherwise
        """
        if not session_id:
            return None
        
        cache_key = self._build_cache_key(session_id, session_type)
        self.stats['gets'] += 1
        
        try:
            session_data = await self.cache.get(cache_key)
            
            if session_data:
                self.stats['hits'] += 1
                logger.debug(f"Cache hit for session {session_id} ({session_type})")
                
                # Check if session has expired based on internal expiry
                if 'expires_at' in session_data:
                    expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
                    if datetime.utcnow() > expires_at:
                        # Session expired, clean it up
                        await self.delete_session(session_id, session_type)
                        self.stats['misses'] += 1
                        return None
                
                return session_data
            else:
                self.stats['misses'] += 1
                logger.debug(f"Cache miss for session {session_id} ({session_type})")
                return None
                
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            self.stats['misses'] += 1
            return None
    
    async def set_session(
        self, 
        session_id: str, 
        session_data: Dict[str, Any], 
        ttl: Optional[int] = None,
        session_type: str = "guest"
    ) -> None:
        """
        Store session data with TTL.
        
        Args:
            session_id: Session identifier
            session_data: Session data to store
            ttl: Time to live in seconds (uses default if None)
            session_type: Type of session
        """
        if not session_id:
            raise ValueError("Session ID is required")
        
        cache_key = self._build_cache_key(session_id, session_type)
        cache_ttl = ttl or self._get_default_ttl(session_type)
        self.stats['sets'] += 1
        
        try:
            # Add metadata to session data
            enriched_data = session_data.copy()
            enriched_data.update({
                'session_id': session_id,
                'session_type': session_type,
                'cached_at': datetime.utcnow().isoformat(),
                'cache_ttl': cache_ttl
            })
            
            # Ensure expires_at is set if not present
            if 'expires_at' not in enriched_data:
                expires_at = datetime.utcnow() + timedelta(seconds=cache_ttl)
                enriched_data['expires_at'] = expires_at.isoformat()
            
            await self.cache.set(cache_key, enriched_data, ttl=cache_ttl)
            
            logger.debug(
                f"Cached session {session_id} ({session_type}) with TTL {cache_ttl}s"
            )
            
        except Exception as e:
            logger.error(f"Error setting session {session_id}: {e}")
            raise CacheError(f"Failed to cache session: {e}")
    
    async def delete_session(
        self, 
        session_id: str, 
        session_type: str = "guest"
    ) -> None:
        """
        Delete session data.
        
        Args:
            session_id: Session identifier
            session_type: Type of session
        """
        if not session_id:
            return
        
        cache_key = self._build_cache_key(session_id, session_type)
        self.stats['deletes'] += 1
        
        try:
            await self.cache.delete(cache_key)
            logger.debug(f"Deleted session {session_id} ({session_type})")
        except Exception as e:
            logger.warning(f"Error deleting session {session_id}: {e}")
    
    async def extend_session_ttl(
        self, 
        session_id: str, 
        extension_seconds: int,
        session_type: str = "guest"
    ) -> bool:
        """
        Extend session TTL.
        
        Args:
            session_id: Session identifier
            extension_seconds: Seconds to extend
            session_type: Type of session
            
        Returns:
            True if extended successfully
        """
        session_data = await self.get_session(session_id, session_type)
        if not session_data:
            return False
        
        self.stats['extensions'] += 1
        
        try:
            # Update expiration time
            new_expires_at = datetime.utcnow() + timedelta(seconds=extension_seconds)
            session_data['expires_at'] = new_expires_at.isoformat()
            session_data['cache_ttl'] = extension_seconds
            
            # Re-cache with new TTL
            await self.set_session(session_id, session_data, extension_seconds, session_type)
            
            logger.debug(
                f"Extended session {session_id} ({session_type}) by {extension_seconds}s"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error extending session {session_id}: {e}")
            return False
    
    async def get_sessions_by_type(self, session_type: str) -> List[Dict[str, Any]]:
        """
        Get all sessions of a specific type.
        
        Note: This is an expensive operation that requires scanning.
        Use sparingly in production.
        
        Args:
            session_type: Type of session to retrieve
            
        Returns:
            List of session data
        """
        # This would require implementing key scanning in the cache service
        # For now, return empty list as this is an expensive operation
        logger.warning(
            f"get_sessions_by_type({session_type}) called - "
            "this is an expensive operation not implemented"
        )
        return []
    
    async def bulk_delete_sessions(
        self, 
        session_ids: List[str], 
        session_type: str = "guest"
    ) -> int:
        """
        Delete multiple sessions in bulk.
        
        Args:
            session_ids: List of session IDs to delete
            session_type: Type of sessions
            
        Returns:
            Number of sessions successfully deleted
        """
        if not session_ids:
            return 0
        
        deleted_count = 0
        for session_id in session_ids:
            try:
                await self.delete_session(session_id, session_type)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete session {session_id}: {e}")
        
        logger.info(
            f"Bulk deleted {deleted_count}/{len(session_ids)} sessions ({session_type})"
        )
        return deleted_count
    
    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        session_type: str = "guest"
    ) -> bool:
        """
        Update session metadata without affecting core session data.
        
        Args:
            session_id: Session identifier
            metadata: Metadata to update
            session_type: Type of session
            
        Returns:
            True if updated successfully
        """
        session_data = await self.get_session(session_id, session_type)
        if not session_data:
            return False
        
        try:
            # Update metadata (safe keys only)
            safe_metadata_keys = {
                'last_activity', 'ip_address', 'user_agent', 'request_count',
                'preferences', 'custom_data', 'tags'
            }
            
            for key, value in metadata.items():
                if key in safe_metadata_keys:
                    session_data[key] = value
            
            session_data['updated_at'] = datetime.utcnow().isoformat()
            
            # Re-cache with existing TTL
            existing_ttl = session_data.get('cache_ttl', self._get_default_ttl(session_type))
            await self.set_session(session_id, session_data, existing_ttl, session_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session metadata {session_id}: {e}")
            return False
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session cache statistics.
        
        Returns:
            Dictionary with cache performance stats
        """
        total_operations = self.stats['gets'] + self.stats['sets'] + self.stats['deletes']
        hit_rate = (self.stats['hits'] / self.stats['gets']) * 100 if self.stats['gets'] > 0 else 0
        
        return {
            'total_operations': total_operations,
            'gets': self.stats['gets'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'extensions': self.stats['extensions'],
            'hit_rate_percent': round(hit_rate, 2),
            'default_ttls': {
                'guest': self.default_guest_ttl,
                'authenticated': self.default_auth_ttl,
                'admin': self.default_admin_ttl
            }
        }
    
    async def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.stats = {
            'gets': 0,
            'sets': 0,
            'deletes': 0,
            'hits': 0,
            'misses': 0,
            'extensions': 0
        }
        logger.info("Reset session cache statistics")
    
    async def cleanup_expired_sessions(self, session_type: Optional[str] = None) -> int:
        """
        Clean up expired sessions for a specific type or all types.
        
        Note: This is a placeholder implementation. In practice, Redis TTL
        handles most cleanup automatically.
        
        Args:
            session_type: Optional session type to clean (cleans all if None)
            
        Returns:
            Number of sessions cleaned up
        """
        # This would require implementing key scanning and expiry checking
        # For now, log the operation as Redis handles TTL automatically
        if session_type:
            logger.debug(f"Cleanup requested for {session_type} sessions (handled by Redis TTL)")
        else:
            logger.debug("Cleanup requested for all sessions (handled by Redis TTL)")
        return 0


# Factory function for dependency injection
def create_session_cache(
    cache_service,
    config: Optional[AuthConfigProtocol] = None
) -> DefaultSessionCache:
    """
    Create a session cache instance.
    
    Args:
        cache_service: Cache service implementation
        config: Optional configuration
        
    Returns:
        Configured DefaultSessionCache instance
    """
    return DefaultSessionCache(
        cache_service=cache_service,
        config=config
    )


__all__ = [
    "DefaultSessionCache",
    "SessionCacheProtocol",
    "create_session_cache",
]