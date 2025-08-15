"""
Token validation service for Keycloak JWT token processing.

Handles JWT token validation, user context extraction,
and session management without authentication (Keycloak handles that).
"""
from typing import Optional, Dict, Any, List
from loguru import logger

from ...domain.entities.session import Session, SessionContext, SessionStatus
from ...domain.value_objects.user_context import UserContext, UserType
from ...domain.value_objects.tenant_context import TenantContext
from ...domain.protocols.repository_protocols import SessionRepositoryProtocol
from ...domain.protocols.cache_protocols import AuthCacheProtocol
from ...domain.protocols.service_protocols import TokenValidationServiceProtocol
from ...infrastructure.external.keycloak_token_validator import KeycloakTokenValidator


class TokenValidationService(TokenValidationServiceProtocol):
    """
    Service for validating Keycloak JWT tokens and extracting user context.
    
    Focuses on token validation and user context extraction only.
    Authentication is fully handled by Keycloak.
    """

    def __init__(
        self,
        session_repository: SessionRepositoryProtocol,
        cache: AuthCacheProtocol,
        keycloak_validator: KeycloakTokenValidator
    ):
        self._session_repository = session_repository
        self._cache = cache
        self._keycloak_validator = keycloak_validator

    async def extract_user_context(
        self,
        token: str,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserContext:
        """
        Extract user context from validated Keycloak JWT token.
        
        Args:
            token: JWT token from Keycloak
            tenant_id: Optional tenant context
            ip_address: Client IP for security logging
            user_agent: Client User-Agent for security logging
            
        Returns:
            User context for authorization decisions
            
        Raises:
            ValueError: If token is invalid or expired
        """
        # Validate token with Keycloak
        token_claims = await self._keycloak_validator.validate_token(token, tenant_id)
        
        # Extract user information from token claims
        user_id = token_claims.get("sub")
        if not user_id:
            raise ValueError("Token missing subject (sub) claim")
        
        username = token_claims.get("preferred_username")
        email = token_claims.get("email")
        tenant_roles = token_claims.get("realm_access", {}).get("roles", [])
        
        # Determine user type based on roles
        user_type = UserType.AUTHENTICATED
        is_superadmin = "superadmin" in tenant_roles or "realm-admin" in tenant_roles
        
        # Create session context
        session_id = token_claims.get("sid") or token_claims.get("jti")
        session_context = SessionContext(
            session_id=session_id,
            user_id=user_id,
            user_type=user_type
        )
        
        # Create user context
        user_context = UserContext(
            user_id=user_id,
            username=username,
            email=email,
            user_type=user_type,
            tenant_id=tenant_id,
            session_context=session_context,
            is_superadmin=is_superadmin,
            metadata={
                "iss": token_claims.get("iss"),
                "aud": token_claims.get("aud"),
                "realm_roles": tenant_roles,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
        
        # Store/update session information
        await self._store_session_info(
            session_id,
            user_context,
            token_claims,
            ip_address,
            user_agent
        )
        
        logger.debug(
            f"User context extracted from token for user {user_id}",
            extra={
                "user_id": user_id,
                "username": username,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "is_superadmin": is_superadmin,
                "ip_address": ip_address
            }
        )
        
        return user_context

    async def validate_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Validate if a session is still active and valid.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            tenant_id: Optional tenant context
            
        Returns:
            True if session is valid and active
        """
        # Check cache first
        cache_key = f"session_valid:{session_id}:{user_id}"
        cached_result = await self._cache.get_session_validity(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Check database
        session = await self._session_repository.get_session(session_id, user_id)
        is_valid = session is not None and session.status == SessionStatus.ACTIVE
        
        # Cache result for short time
        await self._cache.set_session_validity(cache_key, is_valid, ttl=60)
        
        return is_valid

    async def invalidate_session(
        self,
        session_id: str,
        user_id: str,
        invalidated_by: Optional[str] = None
    ) -> bool:
        """
        Invalidate a user session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            invalidated_by: User who invalidated the session
            
        Returns:
            True if session was invalidated
        """
        success = await self._session_repository.invalidate_session(
            session_id,
            user_id,
            invalidated_by
        )
        
        if success:
            # Clear cache
            cache_key = f"session_valid:{session_id}:{user_id}"
            await self._cache.invalidate_session_validity(cache_key)
            
            logger.info(
                f"Session invalidated: {session_id} for user {user_id}",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "invalidated_by": invalidated_by
                }
            )
        
        return success

    async def get_user_sessions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Session]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Optional tenant context
            active_only: Only return active sessions
            
        Returns:
            List of user sessions
        """
        return await self._session_repository.get_user_sessions(
            user_id,
            tenant_id,
            active_only
        )

    async def cleanup_expired_sessions(
        self,
        expiry_hours: int = 24
    ) -> int:
        """
        Clean up expired sessions.
        
        Args:
            expiry_hours: Hours after which sessions are considered expired
            
        Returns:
            Number of sessions cleaned up
        """
        count = await self._session_repository.cleanup_expired_sessions(expiry_hours)
        
        if count > 0:
            logger.info(
                f"Cleaned up {count} expired sessions",
                extra={"expired_count": count, "expiry_hours": expiry_hours}
            )
        
        return count

    async def _store_session_info(
        self,
        session_id: str,
        user_context: UserContext,
        token_claims: Dict[str, Any],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> None:
        """Store or update session information."""
        session = Session(
            id=session_id,
            user_id=user_context.user_id,
            tenant_id=user_context.tenant_id,
            status=SessionStatus.ACTIVE,
            created_at=token_claims.get("iat"),
            expires_at=token_claims.get("exp"),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "realm": token_claims.get("iss"),
                "audience": token_claims.get("aud"),
                "token_type": token_claims.get("typ", "Bearer")
            }
        )
        
        await self._session_repository.store_session(session)

    async def refresh_session(
        self,
        session_id: str,
        user_id: str,
        new_token_claims: Dict[str, Any]
    ) -> bool:
        """
        Refresh session information with new token data.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            new_token_claims: Updated token claims
            
        Returns:
            True if session was refreshed
        """
        success = await self._session_repository.refresh_session(
            session_id,
            user_id,
            new_token_claims.get("exp"),
            new_token_claims
        )
        
        if success:
            # Clear cache to force refresh
            cache_key = f"session_valid:{session_id}:{user_id}"
            await self._cache.invalidate_session_validity(cache_key)
            
            logger.debug(
                f"Session refreshed: {session_id} for user {user_id}",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "new_expiry": new_token_claims.get("exp")
                }
            )
        
        return success