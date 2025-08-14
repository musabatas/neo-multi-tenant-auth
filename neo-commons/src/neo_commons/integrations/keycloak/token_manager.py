"""
Enhanced token management with dual validation strategy and protocol-based dependency injection.
Provides fast local JWT validation, secure introspection, and advanced token lifecycle management.
"""
import logging
import hashlib
import time
from typing import Optional, Dict, Any, Tuple, List, Protocol, runtime_checkable, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
import os
import json

try:
    from jose import jwt, JWTError
except ImportError:
    # Fallback to PyJWT if python-jose is not available
    import jwt as pyjwt
    from jwt.exceptions import PyJWTError as JWTError
    jwt = pyjwt

# Protocol-based interfaces
@runtime_checkable
class CacheManagerProtocol(Protocol):
    """Protocol for cache operations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        ...
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        ...
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        ...


@runtime_checkable
class KeycloakClientProtocol(Protocol):
    """Protocol for Keycloak client operations."""
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Introspect a token to check if it's active."""
        ...
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refresh an access token."""
        ...
    
    async def get_realm_public_key(
        self,
        realm: Optional[str] = None,
        force_refresh: bool = False
    ) -> str:
        """Get the public key for a realm."""
        ...
    
    async def logout(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> bool:
        """Logout a user session."""
        ...


@runtime_checkable
class TokenConfigProtocol(Protocol):
    """Protocol for token configuration."""
    
    @property
    def keycloak_admin_realm(self) -> str:
        """Default Keycloak admin realm."""
        ...
    
    @property
    def keycloak_url(self) -> str:
        """Keycloak server URL."""
        ...
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT signing algorithm."""
        ...
    
    @property
    def jwt_verify_audience(self) -> bool:
        """Whether to verify JWT audience."""
        ...
    
    @property
    def jwt_verify_issuer(self) -> bool:
        """Whether to verify JWT issuer."""
        ...
    
    @property
    def jwt_audience(self) -> Optional[str]:
        """Expected JWT audience."""
        ...
    
    @property
    def jwt_issuer(self) -> Optional[str]:
        """Expected JWT issuer."""
        ...
    
    @property
    def token_cache_ttl(self) -> int:
        """Token cache TTL in seconds."""
        ...
    
    @property
    def introspection_cache_ttl(self) -> int:
        """Introspection cache TTL in seconds."""
        ...
    
    @property
    def public_key_cache_ttl(self) -> int:
        """Public key cache TTL in seconds."""
        ...
    
    @property
    def refresh_threshold(self) -> int:
        """Refresh threshold in seconds."""
        ...


# Default implementations
class DefaultTokenConfig:
    """Default token configuration with environment variable support."""
    
    def __init__(self):
        self._keycloak_admin_realm = None
        self._keycloak_url = None
        self._jwt_algorithm = None
        self._jwt_verify_audience = None
        self._jwt_verify_issuer = None
        self._jwt_audience = None
        self._jwt_issuer = None
        self._token_cache_ttl = None
        self._introspection_cache_ttl = None
        self._public_key_cache_ttl = None
        self._refresh_threshold = None
    
    @property
    def keycloak_admin_realm(self) -> str:
        """Default Keycloak admin realm."""
        if self._keycloak_admin_realm is None:
            self._keycloak_admin_realm = os.getenv(
                'KEYCLOAK_ADMIN_REALM',
                os.getenv('KEYCLOAK_REALM', 'master')
            )
        return self._keycloak_admin_realm
    
    @property
    def keycloak_url(self) -> str:
        """Keycloak server URL."""
        if self._keycloak_url is None:
            self._keycloak_url = os.getenv(
                'KEYCLOAK_URL',
                os.getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080')
            )
        return self._keycloak_url
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT signing algorithm."""
        if self._jwt_algorithm is None:
            self._jwt_algorithm = os.getenv(
                'JWT_ALGORITHM',
                os.getenv('KEYCLOAK_JWT_ALGORITHM', 'RS256')
            )
        return self._jwt_algorithm
    
    @property
    def jwt_verify_audience(self) -> bool:
        """Whether to verify JWT audience."""
        if self._jwt_verify_audience is None:
            self._jwt_verify_audience = os.getenv(
                'JWT_VERIFY_AUDIENCE',
                os.getenv('KEYCLOAK_JWT_VERIFY_AUDIENCE', 'false')
            ).lower() == 'true'
        return self._jwt_verify_audience
    
    @property
    def jwt_verify_issuer(self) -> bool:
        """Whether to verify JWT issuer."""
        if self._jwt_verify_issuer is None:
            self._jwt_verify_issuer = os.getenv(
                'JWT_VERIFY_ISSUER',
                os.getenv('KEYCLOAK_JWT_VERIFY_ISSUER', 'true')
            ).lower() == 'true'
        return self._jwt_verify_issuer
    
    @property
    def jwt_audience(self) -> Optional[str]:
        """Expected JWT audience."""
        if self._jwt_audience is None:
            self._jwt_audience = os.getenv(
                'JWT_AUDIENCE',
                os.getenv('KEYCLOAK_JWT_AUDIENCE')
            )
        return self._jwt_audience
    
    @property
    def jwt_issuer(self) -> Optional[str]:
        """Expected JWT issuer."""
        if self._jwt_issuer is None:
            self._jwt_issuer = os.getenv(
                'JWT_ISSUER',
                os.getenv('KEYCLOAK_JWT_ISSUER')
            )
        return self._jwt_issuer
    
    @property
    def token_cache_ttl(self) -> int:
        """Token cache TTL in seconds (5 minutes default)."""
        if self._token_cache_ttl is None:
            self._token_cache_ttl = int(os.getenv(
                'TOKEN_CACHE_TTL',
                os.getenv('JWT_CACHE_TTL', '300')
            ))
        return self._token_cache_ttl
    
    @property
    def introspection_cache_ttl(self) -> int:
        """Introspection cache TTL in seconds (1 minute default)."""
        if self._introspection_cache_ttl is None:
            self._introspection_cache_ttl = int(os.getenv(
                'INTROSPECTION_CACHE_TTL',
                os.getenv('JWT_INTROSPECTION_CACHE_TTL', '60')
            ))
        return self._introspection_cache_ttl
    
    @property
    def public_key_cache_ttl(self) -> int:
        """Public key cache TTL in seconds (1 hour default)."""
        if self._public_key_cache_ttl is None:
            self._public_key_cache_ttl = int(os.getenv(
                'PUBLIC_KEY_CACHE_TTL',
                os.getenv('JWT_PUBLIC_KEY_CACHE_TTL', '3600')
            ))
        return self._public_key_cache_ttl
    
    @property
    def refresh_threshold(self) -> int:
        """Refresh threshold in seconds (5 minutes default)."""
        if self._refresh_threshold is None:
            self._refresh_threshold = int(os.getenv(
                'TOKEN_REFRESH_THRESHOLD',
                os.getenv('JWT_REFRESH_THRESHOLD', '300')
            ))
        return self._refresh_threshold


class ValidationStrategy(Enum):
    """Token validation strategies with enhanced options."""
    LOCAL = "local"                    # Fast JWT validation only
    INTROSPECTION = "introspection"    # Secure server-side validation only
    DUAL = "dual"                     # Both validations (fallback)
    ADAPTIVE = "adaptive"             # Strategy selection based on context
    CACHED_INTROSPECTION = "cached_introspection"  # Cached introspection results


class TokenValidationException(Exception):
    """Base exception for token validation errors."""
    
    def __init__(self, message: str, token_hash: Optional[str] = None, realm: Optional[str] = None):
        super().__init__(message)
        self.token_hash = token_hash
        self.realm = realm
        self.timestamp = datetime.now(timezone.utc)


class UnauthorizedTokenException(TokenValidationException):
    """Exception raised when token is invalid or expired."""
    pass


class TokenRefreshException(TokenValidationException):
    """Exception raised when token refresh fails."""
    pass


class RevocationException(TokenValidationException):
    """Exception raised when token revocation fails."""
    pass


class EnhancedTokenManager:
    """
    Enhanced dual-validation token management system with protocol-based dependency injection.
    
    Features:
    - Protocol-based dependency injection for testability
    - Fast path: Local JWT validation (< 5ms)
    - Secure path: Token introspection (< 50ms)
    - Adaptive strategy selection based on operation criticality
    - Advanced token caching with hierarchical keys
    - Automatic token refresh before expiry
    - Token revocation management with TTL
    - Comprehensive audit logging and metrics
    - Multi-realm support with per-realm configuration
    - JWT library fallback (python-jose → PyJWT)
    - Environment-based configuration
    - Batch operations for multiple tokens
    - Security event tracking and reporting
    """
    
    def __init__(
        self,
        cache_manager: Optional[CacheManagerProtocol] = None,
        keycloak_client: Optional[KeycloakClientProtocol] = None,
        config: Optional[TokenConfigProtocol] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize enhanced token manager with dependency injection.
        
        Args:
            cache_manager: Cache operations interface
            keycloak_client: Keycloak client interface
            config: Token configuration
            logger: Logger instance
        """
        self.cache = cache_manager
        self.keycloak_client = keycloak_client
        self.config = config or DefaultTokenConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Hierarchical cache key patterns
        self.CACHE_PATTERNS = {
            'token': "auth:token:{user_id}:{session_id}",
            'introspection': "auth:introspect:{token_hash}",
            'public_key': "auth:realm:{realm}:public_key",
            'revoked': "auth:revoked:{token_hash}",
            'refresh_lock': "auth:refresh_lock:{user_id}",
            'validation_metrics': "auth:metrics:validation:{realm}:{date}",
            'user_tokens': "auth:token:{user_id}:*",
            'realm_keys': "auth:realm:{realm}:*",
            'all_tokens': "auth:token:*"
        }
        
        # Performance tracking
        self._validation_stats = {
            'local_success': 0,
            'local_failed': 0,
            'introspection_success': 0,
            'introspection_failed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        self.logger.info("EnhancedTokenManager initialized with protocol-based dependencies")
    
    def _validate_dependencies(self):
        """Validate that required dependencies are available."""
        if not self.cache:
            raise ValueError("Cache manager is required")
        if not self.keycloak_client:
            raise ValueError("Keycloak client is required")
    
    def _get_cache_key(self, pattern: str, **kwargs) -> str:
        """Get formatted cache key from pattern."""
        return self.CACHE_PATTERNS[pattern].format(**kwargs)
    
    def _utc_now(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)
    
    def _hash_token(self, token: str) -> str:
        """
        Create a secure hash of the token for cache keys.
        
        Args:
            token: JWT token
            
        Returns:
            SHA256 hash of token (first 16 chars for key length optimization)
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]
    
    def _extract_token_claims_unsafe(self, token: str) -> Dict[str, Any]:
        """
        Extract claims from token without validation (for metadata only).
        
        Args:
            token: JWT token
            
        Returns:
            Token claims (unvalidated)
        """
        try:
            if hasattr(jwt, 'decode'):
                # python-jose or PyJWT
                return jwt.decode(token, options={"verify_signature": False})
            else:
                # Fallback for other JWT libraries
                import base64
                import json
                header, payload, signature = token.split('.')
                # Add padding if needed
                payload += '=' * (4 - len(payload) % 4)
                decoded_payload = base64.urlsafe_b64decode(payload)
                return json.loads(decoded_payload)
        except Exception:
            return {}
    
    def _determine_validation_strategy(
        self,
        strategy: ValidationStrategy,
        critical: bool,
        token_age: Optional[int] = None,
        realm: Optional[str] = None
    ) -> ValidationStrategy:
        """
        Determine the optimal validation strategy based on context.
        
        Args:
            strategy: Requested validation strategy
            critical: Whether operation is critical
            token_age: Token age in seconds (if known)
            realm: Realm name
            
        Returns:
            Optimal validation strategy
        """
        # Force introspection for critical operations
        if critical:
            return ValidationStrategy.INTROSPECTION
        
        # Use adaptive strategy if requested
        if strategy == ValidationStrategy.ADAPTIVE:
            # Fresh tokens can use local validation
            if token_age and token_age < 300:  # Less than 5 minutes old
                return ValidationStrategy.LOCAL
            else:
                return ValidationStrategy.DUAL
        
        return strategy
    
    async def validate_token(
        self,
        token: str,
        realm: Optional[str] = None,
        critical: bool = False,
        strategy: ValidationStrategy = ValidationStrategy.DUAL,
        cache_result: bool = True,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a token using the specified strategy with enhanced features.
        
        Args:
            token: JWT token to validate
            realm: Realm name (defaults to admin realm)
            critical: Whether this is a critical operation (forces introspection)
            strategy: Validation strategy to use
            cache_result: Whether to cache validation results
            include_metrics: Whether to include performance metrics
            
        Returns:
            Token claims with validation metadata
            
        Raises:
            UnauthorizedTokenException: Token is invalid or expired
            TokenValidationException: Validation failed
        """
        self._validate_dependencies()
        
        realm = realm or self.config.keycloak_admin_realm
        token_hash = self._hash_token(token)
        start_time = time.time()
        
        # Check if token is revoked first
        if await self.is_token_revoked(token):
            self.logger.warning(f"Attempted to use revoked token: {token_hash}")
            raise UnauthorizedTokenException("Token has been revoked", token_hash=token_hash, realm=realm)
        
        # Extract token metadata for strategy optimization
        token_claims = self._extract_token_claims_unsafe(token)
        token_age = None
        if token_claims.get('iat'):
            token_age = int(time.time()) - token_claims['iat']
        
        # Determine optimal strategy
        optimal_strategy = self._determine_validation_strategy(strategy, critical, token_age, realm)
        
        # Check cache first (except for local-only validation)
        cache_key = self._get_cache_key('introspection', token_hash=token_hash)
        cached_result = None
        
        if optimal_strategy != ValidationStrategy.LOCAL and cache_result:
            try:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    self._validation_stats['cache_hits'] += 1
                    self.logger.debug(f"Token validation cache hit for {token_hash}")
                    
                    # Add performance metrics if requested
                    if include_metrics:
                        cached_result['_performance'] = {
                            'validation_time_ms': (time.time() - start_time) * 1000,
                            'cache_hit': True,
                            'strategy_used': 'cache'
                        }
                    
                    return cached_result
            except Exception as e:
                self.logger.warning(f"Cache read failed for token validation: {e}")
        
        self._validation_stats['cache_misses'] += 1
        
        # Perform validation based on strategy
        validation_result = None
        validation_error = None
        method_used = None
        
        try:
            if optimal_strategy == ValidationStrategy.LOCAL:
                validation_result = await self._validate_local(token, realm)
                method_used = "local"
                self._validation_stats['local_success'] += 1
                
            elif optimal_strategy == ValidationStrategy.INTROSPECTION:
                validation_result = await self._validate_introspection(token, realm)
                method_used = "introspection"
                self._validation_stats['introspection_success'] += 1
                
            elif optimal_strategy == ValidationStrategy.DUAL:
                try:
                    # Try local validation first
                    validation_result = await self._validate_local(token, realm)
                    method_used = "local"
                    self._validation_stats['local_success'] += 1
                    
                    # Background introspection for security (fire-and-forget)
                    if not critical:
                        import asyncio
                        asyncio.create_task(self._background_introspection(token, realm, token_hash))
                    
                except UnauthorizedTokenException as e:
                    # Local validation failed, try introspection
                    self.logger.debug(f"Local validation failed, trying introspection: {e}")
                    validation_result = await self._validate_introspection(token, realm)
                    method_used = "introspection_fallback"
                    self._validation_stats['introspection_success'] += 1
                    
            elif optimal_strategy == ValidationStrategy.CACHED_INTROSPECTION:
                # Always use introspection but cache aggressively
                validation_result = await self._validate_introspection(token, realm)
                method_used = "cached_introspection"
                self._validation_stats['introspection_success'] += 1
            
        except Exception as e:
            validation_error = e
            if method_used == "local":
                self._validation_stats['local_failed'] += 1
            else:
                self._validation_stats['introspection_failed'] += 1
            
            self.logger.error(f"Token validation failed using {method_used}: {e}")
            raise UnauthorizedTokenException("Token validation failed", token_hash=token_hash, realm=realm)
        
        # Add validation metadata
        validation_metadata = {
            "validated_at": self._utc_now().isoformat(),
            "strategy_requested": strategy.value,
            "strategy_used": optimal_strategy.value,
            "method": method_used,
            "realm": realm,
            "token_hash": token_hash,
            "critical_operation": critical
        }
        
        # Add performance metrics if requested
        if include_metrics:
            validation_time = (time.time() - start_time) * 1000
            validation_metadata["performance"] = {
                "validation_time_ms": validation_time,
                "cache_hit": False,
                "token_age_seconds": token_age
            }
            
            # Track performance metrics
            await self._track_validation_metrics(realm, method_used, validation_time)
        
        # Add metadata to validation result
        validation_result["_validation"] = validation_metadata
        
        # Cache the validated result
        if cache_result and optimal_strategy != ValidationStrategy.LOCAL:
            try:
                await self.cache.set(
                    cache_key,
                    validation_result,
                    ttl=self.config.introspection_cache_ttl
                )
                self.logger.debug(f"Cached token validation result for {token_hash}")
            except Exception as e:
                self.logger.warning(f"Failed to cache token validation result: {e}")
        
        self.logger.debug(
            f"Token validation successful using {method_used}",
            extra={
                "token_hash": token_hash,
                "realm": realm,
                "method": method_used,
                "critical": critical
            }
        )
        
        return validation_result
    
    async def _validate_local(self, token: str, realm: str) -> Dict[str, Any]:
        """
        Validate token locally using JWT signature with enhanced error handling.
        
        Args:
            token: JWT token
            realm: Realm name
            
        Returns:
            Decoded token claims
            
        Raises:
            UnauthorizedTokenException: Token is invalid
        """
        try:
            # Get public key (cached)
            public_key = await self._get_public_key(realm)
            
            # Build JWT decode options
            jwt_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": self.config.jwt_verify_audience,
                "verify_iss": self.config.jwt_verify_issuer
            }
            
            # Build decode parameters
            decode_params = {
                "token": token,
                "key": public_key,
                "algorithms": [self.config.jwt_algorithm],
                "options": jwt_options
            }
            
            # Add issuer if verification is enabled
            if self.config.jwt_verify_issuer and self.config.jwt_issuer:
                if realm in self.config.jwt_issuer:
                    decode_params["issuer"] = self.config.jwt_issuer
                else:
                    decode_params["issuer"] = f"{self.config.keycloak_url}/realms/{realm}"
            
            # Add audience if verification is enabled
            if self.config.jwt_verify_audience and self.config.jwt_audience:
                decode_params["audience"] = self.config.jwt_audience
            
            # Decode token with fallback handling
            try:
                claims = jwt.decode(**decode_params)
            except JWTError as jwt_error:
                # Handle specific JWT errors with fallbacks
                error_message = str(jwt_error).lower()
                
                if "invalid audience" in error_message:
                    self.logger.warning(f"Audience validation failed, trying without audience verification")
                    # Fallback: Try without audience validation
                    jwt_options["verify_aud"] = False
                    decode_params["options"] = jwt_options
                    decode_params.pop("audience", None)
                    claims = jwt.decode(**decode_params)
                elif "invalid issuer" in error_message:
                    self.logger.warning(f"Issuer validation failed, trying without issuer verification")
                    # Fallback: Try without issuer validation
                    jwt_options["verify_iss"] = False
                    decode_params["options"] = jwt_options
                    decode_params.pop("issuer", None)
                    claims = jwt.decode(**decode_params)
                else:
                    raise
            
            # Additional expiry check for extra safety
            exp = claims.get("exp", 0)
            current_time = datetime.now(timezone.utc).timestamp()
            if exp <= current_time:
                time_diff = current_time - exp
                self.logger.warning(f"Token expired {time_diff} seconds ago")
                raise UnauthorizedTokenException("Token has expired")
            
            # Extract user identification for logging
            sub = claims.get('sub', 'unknown')
            self.logger.debug(f"Local token validation successful for sub: {sub}")
            
            return claims
            
        except JWTError as e:
            error_message = str(e).lower()
            if "expired" in error_message:
                raise UnauthorizedTokenException("Token has expired")
            elif "signature" in error_message:
                raise UnauthorizedTokenException("Invalid token signature")
            else:
                raise UnauthorizedTokenException(f"Invalid token: {e}")
        except Exception as e:
            self.logger.error(f"Local token validation error: {e}")
            raise UnauthorizedTokenException("Token validation failed")
    
    async def _validate_introspection(self, token: str, realm: str) -> Dict[str, Any]:
        """
        Validate token using server-side introspection with enhanced error handling.
        
        Args:
            token: JWT token
            realm: Realm name
            
        Returns:
            Token introspection response
            
        Raises:
            UnauthorizedTokenException: Token is invalid
        """
        try:
            # Introspect token with Keycloak
            introspection = await self.keycloak_client.introspect_token(token, realm)
            
            if not introspection.get("active", False):
                self.logger.warning("Token introspection returned inactive status")
                raise UnauthorizedTokenException("Token is not active")
            
            # Extract user identification for logging
            sub = introspection.get('sub', 'unknown')
            self.logger.debug(f"Token introspection successful for sub: {sub}")
            
            return introspection
            
        except UnauthorizedTokenException:
            raise
        except Exception as e:
            self.logger.error(f"Token introspection failed: {e}")
            raise UnauthorizedTokenException("Token validation failed")
    
    async def _background_introspection(self, token: str, realm: str, token_hash: str):
        """
        Perform background introspection for additional security validation.
        
        Args:
            token: JWT token
            realm: Realm name
            token_hash: Token hash for logging
        """
        try:
            await self._validate_introspection(token, realm)
            self.logger.debug(f"Background introspection successful for {token_hash}")
        except Exception as e:
            # Log but don't raise - this is background validation
            self.logger.warning(f"Background introspection failed for {token_hash}: {e}")
    
    async def _get_public_key(self, realm: str) -> str:
        """
        Get realm public key with caching and error handling.
        
        Args:
            realm: Realm name
            
        Returns:
            Public key in PEM format
            
        Raises:
            TokenValidationException: Failed to get public key
        """
        # Check cache first
        cache_key = self._get_cache_key('public_key', realm=realm)
        
        try:
            cached_key = await self.cache.get(cache_key)
            if cached_key:
                self.logger.debug(f"Public key cache hit for realm {realm}")
                return cached_key
        except Exception as e:
            self.logger.warning(f"Public key cache read failed: {e}")
        
        # Get from Keycloak
        try:
            public_key = await self.keycloak_client.get_realm_public_key(realm)
            
            # Cache the key
            try:
                await self.cache.set(
                    cache_key,
                    public_key,
                    ttl=self.config.public_key_cache_ttl
                )
                self.logger.debug(f"Cached public key for realm {realm}")
            except Exception as e:
                self.logger.warning(f"Failed to cache public key: {e}")
            
            return public_key
            
        except Exception as e:
            self.logger.error(f"Failed to get public key for realm {realm}: {e}")
            raise TokenValidationException(f"Failed to get public key for realm {realm}")
    
    async def refresh_if_needed(
        self,
        token: str,
        refresh_token: str,
        realm: Optional[str] = None,
        force_refresh: bool = False,
        user_id: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Check if token needs refresh and refresh if necessary with locking to prevent concurrent refreshes.
        
        Args:
            token: Current access token
            refresh_token: Refresh token
            realm: Realm name
            force_refresh: Force refresh regardless of expiry
            user_id: User ID for locking (extracted from token if not provided)
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if refreshed, None otherwise
            
        Raises:
            TokenRefreshException: Refresh failed
        """
        self._validate_dependencies()
        
        realm = realm or self.config.keycloak_admin_realm
        
        try:
            # Extract token claims for expiry check and user ID
            claims = self._extract_token_claims_unsafe(token)
            if not user_id:
                user_id = claims.get('sub', 'unknown')
            
            # Check refresh lock to prevent concurrent refreshes
            lock_key = self._get_cache_key('refresh_lock', user_id=user_id)
            if await self.cache.get(lock_key):
                self.logger.debug(f"Refresh already in progress for user {user_id}")
                return None
            
            # Check if token needs refresh
            if not force_refresh:
                exp = claims.get("exp", 0)
                current_time = time.time()
                time_to_expiry = exp - current_time
                
                if time_to_expiry > self.config.refresh_threshold:
                    self.logger.debug(f"Token does not need refresh yet ({time_to_expiry}s remaining)")
                    return None
            
            # Set refresh lock
            await self.cache.set(lock_key, True, ttl=60)  # 1 minute lock
            
            try:
                self.logger.info(f"Refreshing token for user {user_id} (expires in {time_to_expiry}s)")
                
                # Refresh token via Keycloak
                token_response = await self.keycloak_client.refresh_token(refresh_token, realm)
                
                # Clear user's cached tokens since they're now invalid
                await self.clear_user_tokens(user_id)
                
                # Log successful refresh
                self.logger.info(f"Token refreshed successfully for user {user_id}")
                
                return (
                    token_response["access_token"],
                    token_response["refresh_token"]
                )
                
            finally:
                # Always clear the refresh lock
                await self.cache.delete(lock_key)
                
        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
            raise TokenRefreshException(f"Token refresh failed: {e}")
    
    async def revoke_token(
        self,
        token: str,
        realm: Optional[str] = None,
        logout_from_keycloak: bool = False,
        refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoke a token with comprehensive cleanup.
        
        Args:
            token: Token to revoke
            realm: Realm name
            logout_from_keycloak: Whether to logout from Keycloak as well
            refresh_token: Refresh token for Keycloak logout
            
        Returns:
            Revocation result information
            
        Raises:
            RevocationException: Revocation failed
        """
        self._validate_dependencies()
        
        realm = realm or self.config.keycloak_admin_realm
        token_hash = self._hash_token(token)
        
        try:
            # Extract token information
            claims = self._extract_token_claims_unsafe(token)
            user_id = claims.get('sub', 'unknown')
            exp = claims.get("exp", 0)
            
            revocation_result = {
                "token_hash": token_hash,
                "user_id": user_id,
                "realm": realm,
                "revoked_at": self._utc_now().isoformat(),
                "actions_performed": []
            }
            
            # Calculate TTL until token natural expiry
            current_time = time.time()
            ttl = max(0, int(exp - current_time))
            
            # Add token to revocation list
            revocation_key = self._get_cache_key('revoked', token_hash=token_hash)
            await self.cache.set(revocation_key, {
                "revoked_at": self._utc_now().isoformat(),
                "user_id": user_id,
                "realm": realm
            }, ttl=ttl)
            revocation_result["actions_performed"].append("added_to_revocation_list")
            
            # Clear cached validations for this token
            introspection_key = self._get_cache_key('introspection', token_hash=token_hash)
            if await self.cache.delete(introspection_key):
                revocation_result["actions_performed"].append("cleared_validation_cache")
            
            # Logout from Keycloak if requested
            if logout_from_keycloak and refresh_token:
                try:
                    await self.keycloak_client.logout(refresh_token, realm)
                    revocation_result["actions_performed"].append("keycloak_logout")
                except Exception as e:
                    self.logger.warning(f"Keycloak logout failed (non-critical): {e}")
                    revocation_result["actions_performed"].append("keycloak_logout_failed")
            
            self.logger.info(
                f"Token revoked successfully for user {user_id}",
                extra={
                    "user_id": user_id,
                    "token_hash": token_hash,
                    "realm": realm,
                    "actions": revocation_result["actions_performed"]
                }
            )
            
            return revocation_result
            
        except Exception as e:
            self.logger.error(f"Token revocation failed: {e}")
            raise RevocationException(f"Token revocation failed: {e}")
    
    async def is_token_revoked(self, token: str) -> bool:
        """
        Check if a token has been revoked with enhanced checking.
        
        Args:
            token: Token to check
            
        Returns:
            True if token is revoked
        """
        try:
            token_hash = self._hash_token(token)
            revocation_key = self._get_cache_key('revoked', token_hash=token_hash)
            
            revocation_info = await self.cache.get(revocation_key)
            return bool(revocation_info)
        except Exception as e:
            self.logger.warning(f"Token revocation check failed: {e}")
            # Fail safe - assume not revoked if check fails
            return False
    
    async def clear_user_tokens(
        self,
        user_id: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clear all cached tokens and related data for a user.
        
        Args:
            user_id: User ID
            realm: Realm name (optional for filtering)
            
        Returns:
            Cleanup result information
        """
        self._validate_dependencies()
        
        cleanup_result = {
            "user_id": user_id,
            "realm": realm,
            "cleared_at": self._utc_now().isoformat(),
            "items_cleared": 0,
            "types_cleared": []
        }
        
        try:
            # Clear user tokens
            token_pattern = self._get_cache_key('user_tokens', user_id=user_id)
            if hasattr(self.cache, 'clear_pattern'):
                tokens_cleared = await self.cache.clear_pattern(token_pattern)
                cleanup_result["items_cleared"] += tokens_cleared
                if tokens_cleared > 0:
                    cleanup_result["types_cleared"].append(f"tokens ({tokens_cleared})")
            
            # Clear refresh locks
            lock_key = self._get_cache_key('refresh_lock', user_id=user_id)
            if await self.cache.delete(lock_key):
                cleanup_result["items_cleared"] += 1
                cleanup_result["types_cleared"].append("refresh_lock")
            
            self.logger.info(
                f"Cleared {cleanup_result['items_cleared']} cached items for user {user_id}",
                extra=cleanup_result
            )
            
            return cleanup_result
            
        except Exception as e:
            self.logger.error(f"Failed to clear tokens for user {user_id}: {e}")
            cleanup_result["error"] = str(e)
            return cleanup_result
    
    async def batch_validate_tokens(
        self,
        tokens: List[str],
        realm: Optional[str] = None,
        strategy: ValidationStrategy = ValidationStrategy.ADAPTIVE,
        max_concurrent: int = 10
    ) -> Dict[str, Union[Dict[str, Any], Exception]]:
        """
        Validate multiple tokens concurrently with rate limiting.
        
        Args:
            tokens: List of tokens to validate
            realm: Realm name
            strategy: Validation strategy
            max_concurrent: Maximum concurrent validations
            
        Returns:
            Dictionary mapping token hash to validation result or exception
        """
        self._validate_dependencies()
        
        import asyncio
        from asyncio import Semaphore
        
        semaphore = Semaphore(max_concurrent)
        results = {}
        
        async def validate_single(token: str) -> Tuple[str, Union[Dict[str, Any], Exception]]:
            token_hash = self._hash_token(token)
            async with semaphore:
                try:
                    result = await self.validate_token(
                        token=token,
                        realm=realm,
                        strategy=strategy,
                        include_metrics=False
                    )
                    return token_hash, result
                except Exception as e:
                    return token_hash, e
        
        # Execute all validations concurrently
        tasks = [validate_single(token) for token in tokens]
        validation_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for result in validation_results:
            if isinstance(result, Exception):
                # Task itself failed
                results[f"task_error_{len(results)}"] = result
            else:
                token_hash, validation_result = result
                results[token_hash] = validation_result
        
        self.logger.info(f"Batch validated {len(tokens)} tokens with {max_concurrent} concurrency")
        return results
    
    async def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive validation statistics and performance metrics.
        
        Returns:
            Validation statistics and metrics
        """
        return {
            "validation_counts": self._validation_stats.copy(),
            "success_rates": {
                "local": self._validation_stats['local_success'] / max(1, 
                    self._validation_stats['local_success'] + self._validation_stats['local_failed']),
                "introspection": self._validation_stats['introspection_success'] / max(1,
                    self._validation_stats['introspection_success'] + self._validation_stats['introspection_failed'])
            },
            "cache_efficiency": {
                "hit_rate": self._validation_stats['cache_hits'] / max(1,
                    self._validation_stats['cache_hits'] + self._validation_stats['cache_misses'])
            },
            "collected_at": self._utc_now().isoformat()
        }
    
    async def _track_validation_metrics(self, realm: str, method: str, validation_time: float):
        """
        Track validation performance metrics by realm and method.
        
        Args:
            realm: Realm name
            method: Validation method used
            validation_time: Validation time in milliseconds
        """
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            metrics_key = self._get_cache_key('validation_metrics', realm=realm, date=date_str)
            
            # Get existing metrics
            metrics = await self.cache.get(metrics_key) or {
                "date": date_str,
                "realm": realm,
                "methods": {}
            }
            
            # Update method metrics
            if method not in metrics["methods"]:
                metrics["methods"][method] = {
                    "count": 0,
                    "total_time_ms": 0.0,
                    "avg_time_ms": 0.0,
                    "min_time_ms": validation_time,
                    "max_time_ms": validation_time
                }
            
            method_metrics = metrics["methods"][method]
            method_metrics["count"] += 1
            method_metrics["total_time_ms"] += validation_time
            method_metrics["avg_time_ms"] = method_metrics["total_time_ms"] / method_metrics["count"]
            method_metrics["min_time_ms"] = min(method_metrics["min_time_ms"], validation_time)
            method_metrics["max_time_ms"] = max(method_metrics["max_time_ms"], validation_time)
            
            # Cache updated metrics (24 hour TTL)
            await self.cache.set(metrics_key, metrics, ttl=86400)
            
        except Exception as e:
            self.logger.warning(f"Failed to track validation metrics: {e}")


# Factory functions for easy instantiation
def create_token_manager(
    cache_manager: Optional[CacheManagerProtocol] = None,
    keycloak_client: Optional[KeycloakClientProtocol] = None,
    config: Optional[TokenConfigProtocol] = None
) -> EnhancedTokenManager:
    """
    Factory function to create EnhancedTokenManager with dependency injection.
    
    Args:
        cache_manager: Cache operations interface
        keycloak_client: Keycloak client interface
        config: Token configuration
        
    Returns:
        Configured EnhancedTokenManager instance
    """
    return EnhancedTokenManager(
        cache_manager=cache_manager,
        keycloak_client=keycloak_client,
        config=config or DefaultTokenConfig()
    )


# Global token manager instance (singleton pattern)
_token_manager: Optional[EnhancedTokenManager] = None


def get_token_manager(
    cache_manager: Optional[CacheManagerProtocol] = None,
    keycloak_client: Optional[KeycloakClientProtocol] = None,
    config: Optional[TokenConfigProtocol] = None
) -> EnhancedTokenManager:
    """
    Get the global token manager instance with lazy initialization.
    
    Args:
        cache_manager: Cache operations interface (for initial setup)
        keycloak_client: Keycloak client interface (for initial setup)
        config: Token configuration (for initial setup)
        
    Returns:
        EnhancedTokenManager instance
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = create_token_manager(
            cache_manager=cache_manager,
            keycloak_client=keycloak_client,
            config=config
        )
    return _token_manager


# Convenience function for dependency injection setup
def setup_token_manager_dependencies(
    cache_manager: CacheManagerProtocol,
    keycloak_client: KeycloakClientProtocol,
    config: Optional[TokenConfigProtocol] = None
) -> EnhancedTokenManager:
    """
    Setup token manager with all required dependencies.
    
    Args:
        cache_manager: Cache operations interface
        keycloak_client: Keycloak client interface
        config: Optional token configuration
        
    Returns:
        Fully configured EnhancedTokenManager instance
    """
    return EnhancedTokenManager(
        cache_manager=cache_manager,
        keycloak_client=keycloak_client,
        config=config or DefaultTokenConfig(),
        logger=logging.getLogger("neo_commons.token_manager")
    )