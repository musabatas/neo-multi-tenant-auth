"""Token management service for handling JWT operations."""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from ....core.exceptions.auth import InvalidTokenError, TokenExpiredError
from ....core.value_objects.identifiers import RealmId, TokenId, UserId
from ....utils.uuid import generate_uuid_v7
from ..entities.auth_context import AuthContext
from ..entities.jwt_token import JWTToken
from ..entities.protocols import (
    JWTValidatorProtocol,
    KeycloakClientProtocol,
    TokenCacheProtocol,
)

logger = logging.getLogger(__name__)


class TokenService:
    """Service for token lifecycle management."""
    
    def __init__(
        self,
        keycloak_client: KeycloakClientProtocol,
        jwt_validator: JWTValidatorProtocol,
        token_cache: Optional[TokenCacheProtocol] = None,
    ):
        """Initialize token service."""
        self.keycloak_client = keycloak_client
        self.jwt_validator = jwt_validator
        self.token_cache = token_cache
    
    async def validate_and_cache_token(
        self, 
        access_token: str, 
        realm_id: RealmId,
    ) -> AuthContext:
        """Validate token and cache the auth context."""
        logger.debug(f"Validating and caching token for realm {realm_id.value}")
        
        # Generate token ID for caching
        token_id = TokenId(generate_uuid_v7())
        
        # Check cache first
        if self.token_cache:
            cached_context = await self.token_cache.get_cached_token(token_id)
            if cached_context:
                logger.debug("Using cached auth context")
                return cached_context
        
        # Validate token
        auth_context = await self.jwt_validator.validate_token(access_token, realm_id)
        
        # Cache the validated context
        if self.token_cache and auth_context.expires_at:
            ttl = int((auth_context.expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl > 0:
                await self.token_cache.cache_token(token_id, auth_context, ttl)
                logger.debug(f"Cached auth context for {ttl} seconds")
        
        return auth_context
    
    async def refresh_token_with_context(
        self, 
        refresh_token: str, 
        realm_id: RealmId,
    ) -> tuple[JWTToken, AuthContext]:
        """Refresh token and return new token with auth context."""
        logger.info(f"Refreshing token for realm {realm_id.value}")
        
        # Refresh the token
        new_token = await self.keycloak_client.refresh_token(refresh_token, realm_id)
        
        # Validate the new token and create context
        auth_context = await self.jwt_validator.validate_token(
            new_token.access_token, realm_id
        )
        
        # Invalidate old cached tokens for this user
        if self.token_cache:
            await self.token_cache.invalidate_user_tokens(auth_context.user_id)
        
        logger.info(f"Successfully refreshed token for user {auth_context.user_id.value}")
        return new_token, auth_context
    
    async def revoke_token(
        self, 
        refresh_token: str, 
        realm_id: RealmId,
        user_id: Optional[UserId] = None,
    ) -> None:
        """Revoke token and clear cache."""
        logger.info(f"Revoking token for realm {realm_id.value}")
        
        try:
            # Logout in Keycloak (this revokes the token)
            await self.keycloak_client.logout(refresh_token, realm_id)
            
            # Clear cached tokens
            if self.token_cache and user_id:
                await self.token_cache.invalidate_user_tokens(user_id)
            
            logger.info("Successfully revoked token")
        
        except Exception as e:
            logger.warning(f"Token revocation completed with warning: {e}")
            # Still clear cache even if Keycloak logout fails
            if self.token_cache and user_id:
                await self.token_cache.invalidate_user_tokens(user_id)
    
    async def introspect_token_with_cache(
        self, 
        token: str, 
        realm_id: RealmId,
    ) -> Dict:
        """Introspect token with caching for repeated calls."""
        logger.debug(f"Introspecting token for realm {realm_id.value}")
        
        # For now, directly call Keycloak (could add caching later)
        introspection = await self.keycloak_client.introspect_token(token, realm_id)
        
        return introspection
    
    async def validate_token_freshness(
        self, 
        access_token: str,
        max_age_seconds: int = 300,  # 5 minutes
    ) -> bool:
        """Check if token is fresh enough for sensitive operations."""
        logger.debug("Checking token freshness")
        
        try:
            # Extract token claims without full validation
            claims = await self.jwt_validator.extract_claims(access_token)
            
            # Check issued at time
            iat = claims.get("iat")
            if not iat:
                logger.warning("Token missing 'iat' claim")
                return False
            
            issued_at = datetime.fromtimestamp(iat, timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - issued_at).total_seconds()
            
            is_fresh = age_seconds <= max_age_seconds
            logger.debug(f"Token age: {age_seconds}s, fresh: {is_fresh}")
            
            return is_fresh
        
        except Exception as e:
            logger.warning(f"Failed to check token freshness: {e}")
            return False
    
    async def extract_user_info_from_token(self, access_token: str) -> Dict:
        """Extract user information from token without full validation."""
        logger.debug("Extracting user info from token")
        
        try:
            claims = await self.jwt_validator.extract_claims(access_token)
            
            # Extract common user fields
            user_info = {
                "sub": claims.get("sub"),
                "email": claims.get("email"),
                "email_verified": claims.get("email_verified"),
                "preferred_username": claims.get("preferred_username"),
                "given_name": claims.get("given_name"),
                "family_name": claims.get("family_name"),
                "name": claims.get("name"),
                "locale": claims.get("locale"),
                "zoneinfo": claims.get("zoneinfo"),
            }
            
            # Remove None values
            user_info = {k: v for k, v in user_info.items() if v is not None}
            
            return user_info
        
        except Exception as e:
            logger.error(f"Failed to extract user info from token: {e}")
            raise InvalidTokenError(f"Cannot extract user info: {e}") from e
    
    async def is_token_valid_and_active(
        self, 
        access_token: str, 
        realm_id: RealmId,
    ) -> bool:
        """Quick check if token is valid and active."""
        logger.debug("Checking if token is valid and active")
        
        try:
            # First check if token is expired (quick local check)
            if await self.jwt_validator.is_token_expired(access_token):
                logger.debug("Token is expired")
                return False
            
            # For more thorough check, introspect with Keycloak
            introspection = await self.introspect_token_with_cache(access_token, realm_id)
            
            is_active = introspection.get("active", False)
            logger.debug(f"Token active status: {is_active}")
            
            return is_active
        
        except Exception as e:
            logger.warning(f"Token validation check failed: {e}")
            return False
    
    async def get_token_metadata(self, access_token: str) -> Dict:
        """Get token metadata without validation."""
        logger.debug("Getting token metadata")
        
        try:
            claims = await self.jwt_validator.extract_claims(access_token)
            
            metadata = {
                "issued_at": claims.get("iat"),
                "expires_at": claims.get("exp"),
                "not_before": claims.get("nbf"),
                "issuer": claims.get("iss"),
                "audience": claims.get("aud"),
                "subject": claims.get("sub"),
                "session_id": claims.get("session_state"),
                "client_id": claims.get("azp", claims.get("client_id")),
                "scope": claims.get("scope"),
                "token_type": claims.get("typ"),
            }
            
            # Calculate time until expiry
            if metadata["expires_at"]:
                exp_time = datetime.fromtimestamp(metadata["expires_at"], timezone.utc)
                time_until_expiry = (exp_time - datetime.now(timezone.utc)).total_seconds()
                metadata["time_until_expiry"] = max(0, int(time_until_expiry))
            
            return metadata
        
        except Exception as e:
            logger.error(f"Failed to get token metadata: {e}")
            raise InvalidTokenError(f"Cannot get token metadata: {e}") from e
    
    async def invalidate_user_sessions(self, user_id: UserId) -> None:
        """Invalidate all cached sessions for a user."""
        logger.info(f"Invalidating all sessions for user {user_id.value}")
        
        if self.token_cache:
            await self.token_cache.invalidate_user_tokens(user_id)
            logger.info(f"Invalidated cached tokens for user {user_id.value}")
        else:
            logger.debug("No token cache configured")
    
    async def cleanup_expired_tokens(self) -> int:
        """Cleanup expired tokens from cache."""
        logger.info("Starting expired token cleanup")
        
        # This would depend on the cache implementation
        # For now, return 0 as placeholder
        logger.info("Expired token cleanup completed")
        return 0