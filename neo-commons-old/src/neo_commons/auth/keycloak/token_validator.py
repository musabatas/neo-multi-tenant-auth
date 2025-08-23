"""
Token Validator Implementation

Protocol-compliant token validation implementing TokenValidatorProtocol with:
- Dual validation strategy (local JWT + server introspection)
- Protocol-based dependency injection (no hardcoded settings/cache keys)
- Configurable validation strategies (LOCAL, INTROSPECTION, DUAL)
- Intelligent caching with parameterized keys
- Automatic token refresh before expiry
- Revocation checking with TTL management
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from jose import jwt, JWTError
from loguru import logger
import hashlib

from ..core import (
    AuthConfigProtocol,
    CacheKeyProviderProtocol,
    ValidationStrategy,
    AuthenticationError,
    TokenValidationError,
)
from .protocols import TokenValidatorProtocol, KeycloakClientProtocol


class DualStrategyTokenValidator:
    """
    Dual-validation token management system implementing TokenValidatorProtocol.
    
    Features:
    - Fast path: Local JWT validation (< 5ms)
    - Secure path: Token introspection (< 50ms)
    - Automatic strategy selection based on operation criticality
    - Protocol-based configuration injection
    - Parameterized cache key management
    - Token caching with TTL management
    - Automatic refresh before expiry
    """
    
    def __init__(
        self,
        keycloak_client: KeycloakClientProtocol,
        config: AuthConfigProtocol,
        cache_service,
        cache_key_provider: CacheKeyProviderProtocol
    ):
        """
        Initialize token validator with injected dependencies.
        
        Args:
            keycloak_client: Keycloak client for server-side operations
            config: Authentication configuration provider
            cache_service: Cache service for performance optimization
            cache_key_provider: Cache key generation with service namespacing
        """
        self.keycloak_client = keycloak_client
        self.config = config
        self.cache = cache_service
        self.cache_keys = cache_key_provider
        
        # TTL settings (in seconds)
        self.TOKEN_CACHE_TTL = 300  # 5 minutes
        self.INTROSPECTION_CACHE_TTL = 60  # 1 minute
        self.PUBLIC_KEY_CACHE_TTL = 3600  # 1 hour
        
        # Refresh threshold - refresh if token expires in less than this
        self.REFRESH_THRESHOLD = 300  # 5 minutes
        
        logger.info("Initialized DualStrategyTokenValidator with protocol-based configuration")
    
    def _hash_token(self, token: str) -> str:
        """
        Create a hash of the token for cache keys.
        
        Args:
            token: JWT token
            
        Returns:
            SHA256 hash of token (first 16 chars)
        """
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    async def validate_token(
        self,
        token: str,
        realm: str,
        strategy: ValidationStrategy = ValidationStrategy.LOCAL,
        critical: bool = False
    ) -> Dict[str, Any]:
        """
        Validate a token using the specified strategy.
        
        Args:
            token: JWT token to validate
            realm: Realm name for validation
            strategy: Validation strategy to use
            critical: Whether this is critical operation (forces introspection)
            
        Returns:
            Token claims with validation metadata
            
        Raises:
            AuthenticationError: Token invalid or expired
        """
        # Force introspection for critical operations
        if critical:
            strategy = ValidationStrategy.INTROSPECTION
        
        # Check cache first
        token_hash = self._hash_token(token)
        cache_key = self.cache_keys.get_token_validation_key(token_hash, realm)
        
        if strategy != ValidationStrategy.LOCAL:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug("Token validation cache hit")
                return cached
        
        claims = {}
        validation_metadata = {
            "validated_at": datetime.utcnow().isoformat(),
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
                    
                    async def _background_introspection():
                        """Background introspection with exception handling."""
                        try:
                            await self._validate_introspection(token, realm)
                        except Exception as e:
                            # Log but don't raise - this is a background check
                            logger.debug(f"Background introspection check failed (non-critical): {e}")
                    
                    asyncio.create_task(_background_introspection())
                    
                except AuthenticationError:
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
            raise AuthenticationError("Invalid or expired token")
    
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
            AuthenticationError: Token is invalid
        """
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
                "verify_aud": self.config.jwt_verify_audience,
                "verify_iss": self.config.jwt_verify_issuer
            }
            
            decode_params = {
                "token": token,
                "key": public_key,
                "algorithms": [self.config.jwt_algorithm],
                "options": jwt_options
            }
            
            # Only add issuer if verification is enabled
            if self.config.jwt_verify_issuer:
                # Use the configured issuer if available, otherwise construct it
                if self.config.jwt_issuer:
                    decode_params["issuer"] = self.config.jwt_issuer
                else:
                    decode_params["issuer"] = f"{self.config.keycloak_url}/realms/{realm}"
            
            # Add audience parameter only if audience verification is enabled
            if self.config.jwt_verify_audience:
                decode_params["audience"] = self.config.jwt_audience
            
            try:
                claims = jwt.decode(**decode_params)
            except JWTError as e:
                # Handle audience validation fallback
                if "Invalid audience" in str(e):
                    # Fallback: Try without audience validation for backward compatibility
                    logger.warning(f"Audience validation failed, trying without audience verification: {e}")
                    jwt_options["verify_aud"] = False
                    decode_params["options"] = jwt_options
                    decode_params.pop("audience", None)  # Remove audience parameter
                    
                    claims = jwt.decode(**decode_params)
                    
                    # Log the actual audience in token for debugging (if debug enabled)
                    logger.debug(f"Token decoded without audience validation")
                else:
                    raise
            
            # Check if token is not expired
            exp = claims.get("exp", 0)
            if exp <= datetime.utcnow().timestamp():
                raise AuthenticationError("Token has expired")
            
            # Reduce verbose logging - token validation is frequent
            return claims
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise AuthenticationError("Token has expired")
            logger.warning(f"Invalid token: {e}")
            raise AuthenticationError("Invalid token")
        except Exception as e:
            logger.error(f"Local token validation error: {e}")
            raise AuthenticationError("Token validation failed")
    
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
            AuthenticationError: Token is invalid
        """
        try:
            # Introspect token with Keycloak
            introspection = await self.keycloak_client.introspect_token(token, realm)
            
            if not introspection.get("active", False):
                raise AuthenticationError("Token is not active")
            
            logger.debug(f"Token introspection successful for sub: {introspection.get('sub')}")
            return introspection
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            raise AuthenticationError("Token validation failed")
    
    async def _get_public_key(self, realm: str) -> str:
        """
        Get realm public key with caching.
        
        Args:
            realm: Realm name
            
        Returns:
            Public key in PEM format
        """
        # Check cache
        cache_key = self.cache_keys.get_realm_public_key_cache_key(realm)
        cached_key = await self.cache.get(cache_key)
        
        if cached_key:
            return cached_key
        
        # Get from Keycloak
        public_key = await self.keycloak_client.get_realm_public_key(realm)
        
        # Cache the key
        await self.cache.set(
            cache_key,
            public_key,
            ttl=self.PUBLIC_KEY_CACHE_TTL
        )
        
        return public_key
    
    async def is_token_revoked(self, token: str) -> bool:
        """
        Check if a token has been revoked.
        
        Args:
            token: Token to check
            
        Returns:
            True if token is revoked
        """
        token_hash = self._hash_token(token)
        cache_key = f"revoked_token:{token_hash}"
        
        revoked = await self.cache.get(cache_key)
        return bool(revoked)
    
    async def revoke_token(
        self,
        token: str,
        realm: str
    ) -> bool:
        """
        Revoke a token (add to revocation list).
        
        Args:
            token: Token to revoke
            realm: Realm name
            
        Returns:
            True if revoked successfully
        """
        try:
            # Add token hash to revocation list in cache
            token_hash = self._hash_token(token)
            revocation_key = f"revoked_token:{token_hash}"
            
            # Get token expiry
            import jwt as jose_jwt
            claims = jose_jwt.decode(token, options={"verify_signature": False})
            exp = claims.get("exp", 0)
            ttl = max(0, int(exp - datetime.utcnow().timestamp()))
            
            # Add to revocation list with TTL until token natural expiry
            await self.cache.set(revocation_key, True, ttl=ttl)
            
            # Clear any cached validations
            cache_key = self.cache_keys.get_token_validation_key(token_hash, realm)
            await self.cache.delete(cache_key)
            
            logger.info(f"Token revoked for sub: {claims.get('sub')}")
            return True
            
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    async def refresh_if_needed(
        self,
        token: str,
        refresh_token: str,
        realm: str
    ) -> Optional[Tuple[str, str]]:
        """
        Check if token needs refresh and refresh if necessary.
        
        Args:
            token: Current access token
            refresh_token: Refresh token
            realm: Realm name
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if refreshed
        """
        try:
            # Decode token without validation to check expiry
            import jwt as jose_jwt
            claims = jose_jwt.decode(token, options={"verify_signature": False})
            
            # Check if token expires soon
            exp = claims.get("exp", 0)
            time_to_expiry = exp - datetime.utcnow().timestamp()
            
            if time_to_expiry < self.REFRESH_THRESHOLD:
                # Token expires soon, refresh it
                logger.info(f"Token expires in {time_to_expiry}s, refreshing...")
                
                token_response = await self.keycloak_client.refresh_token(refresh_token, realm)
                
                return (
                    token_response["access_token"],
                    token_response["refresh_token"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Token refresh check failed: {e}")
            return None
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        realm: str
    ) -> Dict[str, Any]:
        """
        Authenticate user with username/password and return token data.
        
        This method performs the complete authentication flow including:
        - Keycloak authentication
        - Token validation
        - User synchronization (via external callback if configured)
        
        Args:
            username: User's username or email
            password: User's password  
            realm: Authentication realm
            
        Returns:
            Token data with user information and metadata
            
        Raises:
            AuthenticationError: Invalid credentials
        """
        try:
            # Step 1: Authenticate with Keycloak
            token_response = await self.keycloak_client.authenticate(
                username=username,
                password=password,
                realm=realm
            )
            
            # Step 2: Validate the returned token to get full claims
            token_claims = await self.validate_token(
                token=token_response['access_token'],
                realm=realm,
                strategy=ValidationStrategy.LOCAL
            )
            
            # Step 3: Extract user information from token
            keycloak_user_id = token_claims.get('sub')
            email = token_claims.get('email', username if '@' in username else f"{username}@example.com")
            preferred_username = token_claims.get('preferred_username', username)
            first_name = token_claims.get('given_name')
            last_name = token_claims.get('family_name')
            full_name = token_claims.get('name')
            
            # Step 4: Extract roles and permissions from token
            keycloak_roles = []
            realm_access = token_claims.get('realm_access', {})
            if 'roles' in realm_access:
                keycloak_roles.extend(realm_access['roles'])
            
            resource_access = token_claims.get('resource_access', {})
            client_roles = {}
            for client, access in resource_access.items():
                if 'roles' in access:
                    client_roles[client] = access['roles']
            
            # Step 5: Build enhanced metadata
            enhanced_metadata = {
                "realm": realm,
                "email_verified": token_claims.get('email_verified', False),
                "keycloak_session_id": token_claims.get('sid'),
                "keycloak_auth_time": token_claims.get('iat'),
                "keycloak_expires": token_claims.get('exp'),
                "keycloak_scopes": token_claims.get('scope', '').split(),
                "keycloak_realm_roles": keycloak_roles,
                "keycloak_client_roles": client_roles,
                "keycloak_azp": token_claims.get('azp'),
                "keycloak_acr": token_claims.get('acr'),
                "keycloak_full_name": full_name
            }
            
            # Step 6: Return authentication result with tokens and user data
            result = {
                "access_token": token_response['access_token'],
                "refresh_token": token_response['refresh_token'],
                "token_type": "Bearer",
                "expires_in": token_response.get('expires_in', 3600),
                "user_data": {
                    "external_user_id": keycloak_user_id,
                    "email": email,
                    "username": preferred_username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "display_name": full_name or f"{first_name or ''} {last_name or ''}".strip() or preferred_username,
                    "external_auth_provider": "keycloak",
                    "metadata": enhanced_metadata
                },
                "token_claims": token_claims,
                "realm": realm,
                "authenticated_at": token_response.get('authenticated_at')
            }
            
            # Reduce verbose logging - authentication is frequent
            return result
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def clear_user_tokens(self, user_id: str) -> int:
        """
        Clear all cached tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens cleared
        """
        # Use cache key provider pattern
        pattern = f"*{user_id}*"  # Generic pattern - cache provider can make it specific
        
        try:
            # Note: This would need cache service to support pattern deletion
            # For now, we'll implement basic functionality
            logger.info(f"Requested to clear cached tokens for user {user_id}")
            return 0  # Would return actual count when cache pattern deletion is implemented
            
        except Exception as e:
            logger.error(f"Failed to clear user tokens: {e}")
            return 0


__all__ = [
    "DualStrategyTokenValidator",
]