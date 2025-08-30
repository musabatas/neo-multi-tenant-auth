"""Redis session repository for authentication platform."""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone, timedelta

from .....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import SessionId
from ...core.entities import AuthSession
from ...core.exceptions import SessionInvalid, AuthenticationFailed

logger = logging.getLogger(__name__)


class RedisSessionRepository:
    """Redis session repository following maximum separation principle.
    
    Handles ONLY Redis session storage operations for authentication platform.
    Does not handle session validation logic, user management, or token operations.
    """
    
    def __init__(self, redis_client, key_prefix: str = "auth_session"):
        """Initialize Redis session repository.
        
        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for session keys in Redis
        """
        if not redis_client:
            raise ValueError("Redis client is required")
        self.redis = redis_client
        self.key_prefix = key_prefix
    
    def _make_session_key(self, session_id: SessionId) -> str:
        """Create Redis key for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Redis key string
        """
        return f"{self.key_prefix}:{session_id.value}"
    
    def _make_user_sessions_key(self, user_id: UserId, tenant_id: Optional[TenantId] = None) -> str:
        """Create Redis key for user sessions set.
        
        Args:
            user_id: User identifier
            tenant_id: Optional tenant identifier for scoping
            
        Returns:
            Redis key string
        """
        if tenant_id:
            return f"{self.key_prefix}:user:{user_id.value}:tenant:{tenant_id.value}"
        else:
            return f"{self.key_prefix}:user:{user_id.value}:global"
    
    def _make_tenant_sessions_key(self, tenant_id: TenantId) -> str:
        """Create Redis key for tenant sessions set.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Redis key string
        """
        return f"{self.key_prefix}:tenant:{tenant_id.value}"
    
    def _serialize_session(self, session: AuthSession) -> str:
        """Serialize session to JSON string for Redis storage.
        
        Args:
            session: Auth session to serialize
            
        Returns:
            JSON string representation
        """
        try:
            session_data = {
                "session_id": str(session.session_id.value),
                "user_id": str(session.user_id.value),
                "tenant_id": str(session.tenant_id.value) if session.tenant_id else None,
                "realm_id": str(session.realm_id.value) if session.realm_id else None,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "device_info": session.device_info or {},
                "created_at": session.created_at.isoformat(),
                "last_activity_at": session.last_activity_at.isoformat(),
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "risk_score": session.risk_score,
                "mfa_verified": session.mfa_verified,
                "mfa_verified_at": session.mfa_verified_at.isoformat() if session.mfa_verified_at else None,
                "metadata": session.metadata or {},
                "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None
            }
            return json.dumps(session_data, default=str)
        except Exception as e:
            logger.error(f"Failed to serialize session {session.session_id.value}: {e}")
            raise SessionInvalid(
                "Session serialization failed",
                context={"session_id": str(session.session_id.value), "error": str(e)}
            )
    
    def _deserialize_session(self, session_data: str) -> AuthSession:
        """Deserialize session from JSON string.
        
        Args:
            session_data: JSON string representation
            
        Returns:
            Auth session object
        """
        try:
            data = json.loads(session_data)
            
            # Parse timestamps
            created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
            last_activity_at = datetime.fromisoformat(data["last_activity_at"].replace('Z', '+00:00'))
            expires_at = None
            if data.get("expires_at"):
                expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
            
            mfa_verified_at = None
            if data.get("mfa_verified_at"):
                mfa_verified_at = datetime.fromisoformat(data["mfa_verified_at"].replace('Z', '+00:00'))
            
            revoked_at = None
            if data.get("revoked_at"):
                revoked_at = datetime.fromisoformat(data["revoked_at"].replace('Z', '+00:00'))
            
            return AuthSession(
                session_id=SessionId(data["session_id"]),
                user_id=UserId(data["user_id"]),
                tenant_id=TenantId(data["tenant_id"]) if data.get("tenant_id") else None,
                realm_id=data.get("realm_id"),
                ip_address=data.get("ip_address"),
                user_agent=data.get("user_agent"),
                device_info=data.get("device_info", {}),
                created_at=created_at,
                last_activity_at=last_activity_at,
                expires_at=expires_at,
                risk_score=data.get("risk_score", 0.0),
                mfa_verified=data.get("mfa_verified", False),
                mfa_verified_at=mfa_verified_at,
                metadata=data.get("metadata", {}),
                revoked_at=revoked_at
            )
            
        except Exception as e:
            logger.error(f"Failed to deserialize session data: {e}")
            raise SessionInvalid(
                "Session deserialization failed",
                context={"error": str(e)}
            )
    
    async def store_session(
        self,
        session: AuthSession,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Store session in Redis.
        
        Args:
            session: Auth session to store
            ttl_seconds: Time to live in seconds (optional)
        """
        session_key = self._make_session_key(session.session_id)
        user_sessions_key = self._make_user_sessions_key(session.user_id, session.tenant_id)
        
        try:
            # Serialize session
            session_data = self._serialize_session(session)
            
            # Calculate TTL
            if ttl_seconds is None and session.expires_at:
                ttl_seconds = max(1, int((session.expires_at - datetime.now(timezone.utc)).total_seconds()))
            
            # Store session data with pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            if ttl_seconds and ttl_seconds > 0:
                pipe.setex(session_key, ttl_seconds, session_data)
                # Add to user sessions set with same TTL
                pipe.sadd(user_sessions_key, str(session.session_id.value))
                pipe.expire(user_sessions_key, ttl_seconds)
            else:
                pipe.set(session_key, session_data)
                pipe.sadd(user_sessions_key, str(session.session_id.value))
            
            # Add to tenant sessions if tenant_id exists
            if session.tenant_id:
                tenant_sessions_key = self._make_tenant_sessions_key(session.tenant_id)
                pipe.sadd(tenant_sessions_key, str(session.session_id.value))
                if ttl_seconds and ttl_seconds > 0:
                    pipe.expire(tenant_sessions_key, ttl_seconds)
            
            await pipe.execute()
            
            logger.debug(f"Stored session {session.session_id.value} with TTL {ttl_seconds}")
            
        except Exception as e:
            logger.error(f"Failed to store session {session.session_id.value}: {e}")
            raise SessionInvalid(
                "Session storage failed",
                context={"session_id": str(session.session_id.value), "error": str(e)}
            )
    
    async def get_session(self, session_id: SessionId) -> Optional[AuthSession]:
        """Get session from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Auth session or None if not found
        """
        session_key = self._make_session_key(session_id)
        
        try:
            session_data = await self.redis.get(session_key)
            if not session_data:
                return None
            
            return self._deserialize_session(session_data)
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id.value}: {e}")
            return None
    
    async def update_session(
        self,
        session: AuthSession,
        preserve_ttl: bool = True
    ) -> None:
        """Update existing session in Redis.
        
        Args:
            session: Updated auth session
            preserve_ttl: Whether to preserve existing TTL
        """
        session_key = self._make_session_key(session.session_id)
        
        try:
            # Get current TTL if preserving
            current_ttl = None
            if preserve_ttl:
                current_ttl = await self.redis.ttl(session_key)
                if current_ttl == -1:  # No expiration
                    current_ttl = None
                elif current_ttl == -2:  # Key doesn't exist
                    raise SessionInvalid(
                        "Session not found for update",
                        context={"session_id": str(session.session_id.value)}
                    )
            
            # Serialize and store updated session
            session_data = self._serialize_session(session)
            
            if current_ttl and current_ttl > 0:
                await self.redis.setex(session_key, current_ttl, session_data)
            else:
                await self.redis.set(session_key, session_data)
            
            logger.debug(f"Updated session {session.session_id.value}")
            
        except SessionInvalid:
            # Re-raise session invalid exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to update session {session.session_id.value}: {e}")
            raise SessionInvalid(
                "Session update failed",
                context={"session_id": str(session.session_id.value), "error": str(e)}
            )
    
    async def delete_session(self, session_id: SessionId) -> bool:
        """Delete session from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was deleted, False if not found
        """
        try:
            # First get session to determine user and tenant
            session = await self.get_session(session_id)
            if not session:
                return False
            
            # Delete from all relevant sets
            session_key = self._make_session_key(session_id)
            user_sessions_key = self._make_user_sessions_key(session.user_id, session.tenant_id)
            
            pipe = self.redis.pipeline()
            pipe.delete(session_key)
            pipe.srem(user_sessions_key, str(session_id.value))
            
            if session.tenant_id:
                tenant_sessions_key = self._make_tenant_sessions_key(session.tenant_id)
                pipe.srem(tenant_sessions_key, str(session_id.value))
            
            results = await pipe.execute()
            deleted = results[0] > 0
            
            if deleted:
                logger.debug(f"Deleted session {session_id.value}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id.value}: {e}")
            return False
    
    async def get_user_sessions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        active_only: bool = True
    ) -> List[AuthSession]:
        """Get all sessions for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Optional tenant identifier for scoping
            active_only: Whether to return only active sessions
            
        Returns:
            List of user sessions
        """
        user_sessions_key = self._make_user_sessions_key(user_id, tenant_id)
        
        try:
            # Get session IDs from set
            session_ids = await self.redis.smembers(user_sessions_key)
            
            if not session_ids:
                return []
            
            # Get all sessions in parallel
            session_keys = [self._make_session_key(SessionId(sid.decode())) for sid in session_ids]
            session_data_list = await self.redis.mget(*session_keys)
            
            sessions = []
            current_time = datetime.now(timezone.utc)
            
            for i, session_data in enumerate(session_data_list):
                if not session_data:
                    continue
                
                try:
                    session = self._deserialize_session(session_data)
                    
                    # Filter expired sessions if active_only
                    if active_only:
                        if session.is_expired or session.revoked_at:
                            continue
                        if session.expires_at and session.expires_at <= current_time:
                            continue
                    
                    sessions.append(session)
                    
                except Exception as e:
                    logger.warning(f"Failed to deserialize session data for user {user_id.value}: {e}")
                    continue
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id.value}: {e}")
            return []
    
    async def cleanup_expired_sessions(self, batch_size: int = 100) -> int:
        """Clean up expired sessions from Redis.
        
        Args:
            batch_size: Number of sessions to process per batch
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            # Get all session keys
            pattern = f"{self.key_prefix}:*"
            session_keys = []
            
            async for key in self.redis.scan_iter(match=pattern, count=batch_size):
                if key.decode().count(':') == 2:  # session keys have format prefix:session_id
                    session_keys.append(key.decode())
            
            if not session_keys:
                return 0
            
            cleaned_count = 0
            current_time = datetime.now(timezone.utc)
            
            for i in range(0, len(session_keys), batch_size):
                batch_keys = session_keys[i:i + batch_size]
                
                # Get session data for batch
                session_data_list = await self.redis.mget(*batch_keys)
                
                for j, session_data in enumerate(session_data_list):
                    if not session_data:
                        continue
                    
                    try:
                        session = self._deserialize_session(session_data)
                        
                        # Check if session is expired
                        if session.expires_at and session.expires_at <= current_time:
                            await self.delete_session(session.session_id)
                            cleaned_count += 1
                            
                    except Exception as e:
                        logger.warning(f"Failed to process session during cleanup: {e}")
                        continue
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_session_count(
        self,
        user_id: Optional[UserId] = None,
        tenant_id: Optional[TenantId] = None
    ) -> int:
        """Get count of sessions.
        
        Args:
            user_id: Optional user ID to filter by
            tenant_id: Optional tenant ID to filter by
            
        Returns:
            Number of sessions
        """
        try:
            if user_id:
                user_sessions_key = self._make_user_sessions_key(user_id, tenant_id)
                return await self.redis.scard(user_sessions_key)
            elif tenant_id:
                tenant_sessions_key = self._make_tenant_sessions_key(tenant_id)
                return await self.redis.scard(tenant_sessions_key)
            else:
                # Count all session keys
                pattern = f"{self.key_prefix}:*"
                count = 0
                async for _ in self.redis.scan_iter(match=pattern):
                    count += 1
                return count
                
        except Exception as e:
            logger.error(f"Failed to get session count: {e}")
            return 0