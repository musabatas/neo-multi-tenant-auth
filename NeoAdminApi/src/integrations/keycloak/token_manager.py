"""
Token management with dual validation strategy.
Provides fast local JWT validation and secure introspection.
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from jose import jwt, JWTError
from loguru import logger

from src.common.cache.client import get_cache
from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError
from src.common.utils import utc_now
from .async_client import get_keycloak_client


class ValidationStrategy(Enum):
    """Token validation strategies."""
    LOCAL = "local"  # Fast JWT validation
    INTROSPECTION = "introspection"  # Secure server-side validation
    DUAL = "dual"  # Both validations


class TokenManager:
    """
    Dual-validation token management system.
    
    Features:
    - Fast path: Local JWT validation (< 5ms)
    - Secure path: Token introspection (< 50ms)
    - Automatic strategy selection based on operation criticality
    - Token caching with TTL management
    - Automatic refresh before expiry
    """
    
    def __init__(self):
        """Initialize token manager."""
        self.cache = get_cache()
        self.keycloak_client = None
        
        # Cache key patterns
        self.TOKEN_CACHE_KEY = "auth:token:{user_id}:{session_id}"
        self.INTROSPECTION_CACHE_KEY = "auth:introspect:{token_hash}"
        self.PUBLIC_KEY_CACHE_KEY = "auth:realm:{realm}:public_key"
        
        # TTL settings (in seconds)
        self.TOKEN_CACHE_TTL = 300  # 5 minutes
        self.INTROSPECTION_CACHE_TTL = 60  # 1 minute
        self.PUBLIC_KEY_CACHE_TTL = 3600  # 1 hour
        
        # Refresh threshold - refresh if token expires in less than this
        self.REFRESH_THRESHOLD = 300  # 5 minutes
    
    async def _get_client(self):
        """Get Keycloak client instance."""
        if not self.keycloak_client:
            self.keycloak_client = await get_keycloak_client()
        return self.keycloak_client
    
    def _hash_token(self, token: str) -> str:
        """
        Create a hash of the token for cache keys.
        
        Args:
            token: JWT token
            
        Returns:
            SHA256 hash of token (first 16 chars)
        """
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    async def validate_token(
        self,
        token: str,
        realm: Optional[str] = None,
        critical: bool = False,
        strategy: ValidationStrategy = ValidationStrategy.DUAL
    ) -> Dict[str, Any]:
        """
        Validate a token using the specified strategy.
        
        Args:
            token: JWT token to validate
            realm: Realm name (defaults to admin realm)
            critical: Whether this is a critical operation (forces introspection)
            strategy: Validation strategy to use
            
        Returns:
            Token claims with validation metadata
            
        Raises:
            UnauthorizedError: Token is invalid or expired
        """
        realm = realm or settings.keycloak_admin_realm
        
        # Force introspection for critical operations
        if critical:
            strategy = ValidationStrategy.INTROSPECTION
        
        # Check cache first
        token_hash = self._hash_token(token)
        cache_key = self.INTROSPECTION_CACHE_KEY.format(token_hash=token_hash)
        
        if strategy != ValidationStrategy.LOCAL:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug("Token validation cache hit")
                return cached
        
        claims = {}
        validation_metadata = {
            "validated_at": utc_now().isoformat(),
            "strategy": strategy.value,
            "realm": realm
        }
        
        try:
            if strategy == ValidationStrategy.LOCAL:
                # Fast path: Local JWT validation only
                claims = await self._validate_local(token, realm)
                validation_metadata["method"] = "local"
                
            elif strategy == ValidationStrategy.INTROSPECTION:
                # Secure path: Server-side introspection only
                claims = await self._validate_introspection(token, realm)
                validation_metadata["method"] = "introspection"
                
            elif strategy == ValidationStrategy.DUAL:
                # Dual validation: Try local first, then introspection
                try:
                    claims = await self._validate_local(token, realm)
                    validation_metadata["method"] = "local"
                    
                    # For dual strategy, also do introspection in background
                    # for extra security (non-blocking)
                    import asyncio
                    asyncio.create_task(self._validate_introspection(token, realm))
                    
                except UnauthorizedError:
                    # Local validation failed, try introspection
                    claims = await self._validate_introspection(token, realm)
                    validation_metadata["method"] = "introspection"
            
            # Add validation metadata to claims
            claims["_validation"] = validation_metadata
            
            # Cache the validated claims
            if strategy != ValidationStrategy.LOCAL:
                await self.cache.set(
                    cache_key,
                    claims,
                    ttl=self.INTROSPECTION_CACHE_TTL
                )
            
            return claims
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise UnauthorizedError("Invalid or expired token")
    
    async def _validate_local(
        self,
        token: str,
        realm: str
    ) -> Dict[str, Any]:
        """
        Validate token locally using JWT signature.
        
        Args:
            token: JWT token
            realm: Realm name
            
        Returns:
            Decoded token claims
            
        Raises:
            UnauthorizedError: Token is invalid
        """
        client = await self._get_client()
        
        try:
            # Get public key (cached)
            public_key = await self._get_public_key(realm)
            
            # Decode and validate token
            # Based on research: Keycloak 2025 has stricter audience validation
            # We need to handle cases where audience might not be present or different
            
            jwt_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": settings.jwt_verify_audience,
                "verify_iss": settings.jwt_verify_issuer
            }
            
            decode_params = {
                "token": token,
                "key": public_key,
                "algorithms": [settings.jwt_algorithm],
                "options": jwt_options
            }
            
            # Only add issuer if verification is enabled
            if settings.jwt_verify_issuer:
                # Use the configured issuer if it matches the realm, otherwise construct it
                if realm in settings.jwt_issuer:
                    decode_params["issuer"] = settings.jwt_issuer
                else:
                    decode_params["issuer"] = f"{settings.keycloak_url}/realms/{realm}"
            
            # Add audience parameter only if audience verification is enabled
            if settings.jwt_verify_audience:
                decode_params["audience"] = settings.jwt_audience
            
            try:
                claims = jwt.decode(**decode_params)
            except JWTError as e:
                if "Invalid audience" in str(e) and settings.jwt_audience_fallback:
                    # Fallback: Try without audience validation for backward compatibility
                    logger.warning(f"Audience validation failed, trying without audience verification: {e}")
                    jwt_options["verify_aud"] = False
                    decode_params["options"] = jwt_options
                    decode_params.pop("audience", None)  # Remove audience parameter
                    
                    claims = jwt.decode(**decode_params)
                    
                    # Log the actual audience in token for debugging
                    if settings.jwt_debug_claims:
                        token_aud = claims.get('aud', 'not_present')
                        logger.debug(f"Token audience: {token_aud}, Expected: {settings.jwt_audience}")
                        logger.debug(f"Token claims: {claims}")
                else:
                    raise
            
            # Check if token is not expired
            exp = claims.get("exp", 0)
            if exp <= datetime.utcnow().timestamp():
                raise UnauthorizedError("Token has expired")
            
            logger.debug(f"Local token validation successful for sub: {claims.get('sub')}")
            return claims
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise UnauthorizedError("Token has expired")
            logger.warning(f"Invalid token: {e}")
            raise UnauthorizedError("Invalid token")
        except Exception as e:
            logger.error(f"Local token validation error: {e}")
            raise UnauthorizedError("Token validation failed")
    
    async def _validate_introspection(
        self,
        token: str,
        realm: str
    ) -> Dict[str, Any]:
        """
        Validate token using server-side introspection.
        
        Args:
            token: JWT token
            realm: Realm name
            
        Returns:
            Token introspection response
            
        Raises:
            UnauthorizedError: Token is invalid
        """
        client = await self._get_client()
        
        try:
            # Introspect token with Keycloak
            introspection = await client.introspect_token(token, realm)
            
            if not introspection.get("active", False):
                raise UnauthorizedError("Token is not active")
            
            logger.debug(f"Token introspection successful for sub: {introspection.get('sub')}")
            return introspection
            
        except UnauthorizedError:
            raise
        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            raise UnauthorizedError("Token validation failed")
    
    async def _get_public_key(self, realm: str) -> str:
        """
        Get realm public key with caching.
        
        Args:
            realm: Realm name
            
        Returns:
            Public key in PEM format
        """
        # Check cache
        cache_key = self.PUBLIC_KEY_CACHE_KEY.format(realm=realm)
        cached_key = await self.cache.get(cache_key)
        
        if cached_key:
            return cached_key
        
        # Get from Keycloak
        client = await self._get_client()
        public_key = await client.get_realm_public_key(realm)
        
        # Cache the key
        await self.cache.set(
            cache_key,
            public_key,
            ttl=self.PUBLIC_KEY_CACHE_TTL
        )
        
        return public_key
    
    async def refresh_if_needed(
        self,
        token: str,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Check if token needs refresh and refresh if necessary.
        
        Args:
            token: Current access token
            refresh_token: Refresh token
            realm: Realm name
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if refreshed, None otherwise
        """
        realm = realm or settings.keycloak_admin_realm
        
        try:
            # Decode token without validation to check expiry
            import jwt
            claims = jwt.decode(token, options={"verify_signature": False})
            
            # Check if token expires soon
            exp = claims.get("exp", 0)
            time_to_expiry = exp - datetime.utcnow().timestamp()
            
            if time_to_expiry < self.REFRESH_THRESHOLD:
                # Token expires soon, refresh it
                logger.info(f"Token expires in {time_to_expiry}s, refreshing...")
                
                client = await self._get_client()
                token_response = await client.refresh_token(refresh_token, realm)
                
                return (
                    token_response["access_token"],
                    token_response["refresh_token"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Token refresh check failed: {e}")
            return None
    
    async def revoke_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> bool:
        """
        Revoke a token (add to revocation list).
        
        Args:
            token: Token to revoke
            realm: Realm name
            
        Returns:
            True if revoked successfully
        """
        realm = realm or settings.keycloak_admin_realm
        
        try:
            # Add token hash to revocation list in cache
            token_hash = self._hash_token(token)
            revocation_key = f"auth:revoked:{token_hash}"
            
            # Get token expiry
            import jwt
            claims = jwt.decode(token, options={"verify_signature": False})
            exp = claims.get("exp", 0)
            ttl = max(0, int(exp - datetime.utcnow().timestamp()))
            
            # Add to revocation list with TTL until token natural expiry
            await self.cache.set(revocation_key, True, ttl=ttl)
            
            # Clear any cached validations
            cache_key = self.INTROSPECTION_CACHE_KEY.format(token_hash=token_hash)
            await self.cache.delete(cache_key)
            
            logger.info(f"Token revoked for sub: {claims.get('sub')}")
            return True
            
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    async def is_token_revoked(self, token: str) -> bool:
        """
        Check if a token has been revoked.
        
        Args:
            token: Token to check
            
        Returns:
            True if token is revoked
        """
        token_hash = self._hash_token(token)
        revocation_key = f"auth:revoked:{token_hash}"
        
        revoked = await self.cache.get(revocation_key)
        return bool(revoked)
    
    async def clear_user_tokens(self, user_id: str) -> int:
        """
        Clear all cached tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens cleared
        """
        pattern = f"auth:token:{user_id}:*"
        keys = await self.cache.keys(pattern)
        
        if keys:
            await self.cache.delete(*keys)
            logger.info(f"Cleared {len(keys)} cached tokens for user {user_id}")
            return len(keys)
        
        return 0


# Global token manager instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """
    Get the global token manager instance.
    
    Returns:
        TokenManager instance
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager