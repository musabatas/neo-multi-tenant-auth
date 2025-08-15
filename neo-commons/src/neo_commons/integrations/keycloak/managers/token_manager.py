"""
Streamlined token management for Keycloak integration.

Focused implementation with core token validation and caching functionality.
"""
import logging
import hashlib
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import os

from ..protocols.token_protocols import TokenConfigProtocol, CacheManagerProtocol, KeycloakClientProtocol

logger = logging.getLogger(__name__)

try:
    from jose import jwt, JWTError
except ImportError:
    import jwt as pyjwt
    from jwt.exceptions import PyJWTError as JWTError
    jwt = pyjwt


class ValidationStrategy(Enum):
    """Token validation strategies."""
    LOCAL_ONLY = "local_only"
    INTROSPECT_ONLY = "introspect_only" 
    SMART_FALLBACK = "smart_fallback"


class TokenValidationException(Exception):
    """Base exception for token validation errors."""
    pass


class DefaultTokenConfig(TokenConfigProtocol):
    """Default token configuration with environment variable support."""
    
    def __init__(self, **overrides):
        self._overrides = overrides
    
    def _get_value(self, key: str, env_key: str, default: Any = None) -> Any:
        return self._overrides.get(key) or os.getenv(env_key, default)
    
    @property
    def keycloak_admin_realm(self) -> str:
        return self._get_value("keycloak_admin_realm", "KEYCLOAK_ADMIN_REALM", "master")
    
    @property
    def keycloak_url(self) -> str:
        return self._get_value("keycloak_url", "KEYCLOAK_URL", "").rstrip('/')
    
    @property
    def jwt_algorithm(self) -> str:
        return self._get_value("jwt_algorithm", "JWT_ALGORITHM", "RS256")
    
    @property
    def jwt_verify_audience(self) -> bool:
        return str(self._get_value("jwt_verify_audience", "JWT_VERIFY_AUDIENCE", "true")).lower() == "true"
    
    @property
    def jwt_verify_issuer(self) -> bool:
        return str(self._get_value("jwt_verify_issuer", "JWT_VERIFY_ISSUER", "true")).lower() == "true"
    
    @property
    def jwt_audience(self) -> Optional[str]:
        return self._get_value("jwt_audience", "JWT_AUDIENCE", None)
    
    @property
    def jwt_issuer(self) -> Optional[str]:
        return self._get_value("jwt_issuer", "JWT_ISSUER", None)
    
    @property
    def token_cache_ttl(self) -> int:
        return int(self._get_value("token_cache_ttl", "TOKEN_CACHE_TTL", "300"))
    
    @property
    def public_key_cache_ttl(self) -> int:
        return int(self._get_value("public_key_cache_ttl", "PUBLIC_KEY_CACHE_TTL", "3600"))
    
    @property
    def local_validation_enabled(self) -> bool:
        return str(self._get_value("local_validation_enabled", "LOCAL_VALIDATION_ENABLED", "true")).lower() == "true"
    
    @property
    def introspection_enabled(self) -> bool:
        return str(self._get_value("introspection_enabled", "INTROSPECTION_ENABLED", "true")).lower() == "true"
    
    @property
    def dual_validation_threshold(self) -> float:
        return float(self._get_value("dual_validation_threshold", "DUAL_VALIDATION_THRESHOLD", "0.1"))


class EnhancedTokenManager:
    """Streamlined token manager with validation and caching."""
    
    def __init__(
        self,
        config: Optional[TokenConfigProtocol] = None,
        cache_manager: Optional[CacheManagerProtocol] = None,
        keycloak_client: Optional[KeycloakClientProtocol] = None,
        validation_strategy: ValidationStrategy = ValidationStrategy.SMART_FALLBACK
    ):
        self.config = config or DefaultTokenConfig()
        self.cache_manager = cache_manager
        self.keycloak_client = keycloak_client
        self.validation_strategy = validation_strategy
        
        # Internal cache fallback
        self._token_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        
        logger.info(f"EnhancedTokenManager initialized with strategy: {validation_strategy.value}")
    
    def _hash_token(self, token: str) -> str:
        """Create hash of token for caching."""
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self.cache_manager:
            return await self.cache_manager.get(key)
        
        # Fallback to internal cache
        if key in self._token_cache:
            data, timestamp = self._token_cache[key]
            if datetime.now() < timestamp + timedelta(seconds=self.config.token_cache_ttl):
                return data
            else:
                del self._token_cache[key]
        
        return None
    
    async def _set_in_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        if self.cache_manager:
            await self.cache_manager.set(key, value, ttl)
        else:
            self._token_cache[key] = (value, datetime.now())
    
    async def _get_public_key(self, realm: str) -> Optional[str]:
        """Get realm public key with caching."""
        cache_key = f"public_key:{realm}"
        
        cached_key = await self._get_from_cache(cache_key)
        if cached_key:
            return cached_key
        
        if self.keycloak_client:
            try:
                public_key = await self.keycloak_client.get_realm_public_key(realm)
                if public_key:
                    await self._set_in_cache(cache_key, public_key, self.config.public_key_cache_ttl)
                    return public_key
            except Exception as e:
                logger.warning(f"Failed to get public key for realm {realm}: {e}")
        
        return None
    
    async def validate_token_local(
        self,
        token: str,
        realm: str,
        audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate token locally using public key."""
        try:
            public_key = await self._get_public_key(realm)
            if not public_key:
                raise TokenValidationException("Unable to get public key for validation")
            
            options = {
                "verify_signature": True,
                "verify_aud": self.config.jwt_verify_audience,
                "verify_iss": self.config.jwt_verify_issuer,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True
            }
            
            expected_audience = audience or self.config.jwt_audience
            expected_issuer = self.config.jwt_issuer or f"{self.config.keycloak_url}/realms/{realm}"
            
            if hasattr(jwt, 'decode'):
                decoded_token = jwt.decode(
                    token,
                    public_key,
                    algorithms=[self.config.jwt_algorithm],
                    audience=expected_audience if options["verify_aud"] else None,
                    issuer=expected_issuer if options["verify_iss"] else None,
                    options=options
                )
            else:
                decoded_token = jwt.decode(
                    token,
                    public_key,
                    algorithms=[self.config.jwt_algorithm],
                    audience=expected_audience if options["verify_aud"] else None,
                    issuer=expected_issuer if options["verify_iss"] else None,
                    options=options
                )
            
            decoded_token.update({
                "validation_method": "local",
                "realm": realm,
                "validated_at": datetime.now().isoformat()
            })
            
            return decoded_token
            
        except JWTError as e:
            logger.debug(f"Local token validation failed: {e}")
            raise TokenValidationException(f"Token validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in local validation: {e}")
            raise TokenValidationException(f"Token validation error: {str(e)}")
    
    async def validate_token_introspect(
        self,
        token: str,
        realm: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """Validate token via Keycloak introspection."""
        if not self.keycloak_client:
            raise TokenValidationException("Keycloak client not configured for introspection")
        
        try:
            token_hash = self._hash_token(token)
            cache_key = f"token:{realm}:introspect:{token_hash}"
            
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
            
            introspection_result = await self.keycloak_client.introspect_token(
                token=token,
                realm=realm,
                client_id=client_id,
                client_secret=client_secret
            )
            
            if not introspection_result.get("active", False):
                raise TokenValidationException("Token is not active")
            
            introspection_result.update({
                "validation_method": "introspection",
                "realm": realm,
                "validated_at": datetime.now().isoformat()
            })
            
            await self._set_in_cache(cache_key, introspection_result, self.config.token_cache_ttl)
            
            return introspection_result
            
        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            raise TokenValidationException(f"Token introspection failed: {str(e)}")
    
    async def validate_token(
        self,
        token: str,
        realm: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate token using configured strategy."""
        if self.validation_strategy == ValidationStrategy.LOCAL_ONLY:
            return await self.validate_token_local(token, realm, audience)
        
        elif self.validation_strategy == ValidationStrategy.INTROSPECT_ONLY:
            if not client_id or not client_secret:
                raise TokenValidationException("Client credentials required for introspection")
            return await self.validate_token_introspect(token, realm, client_id, client_secret)
        
        elif self.validation_strategy == ValidationStrategy.SMART_FALLBACK:
            try:
                return await self.validate_token_local(token, realm, audience)
            except Exception as local_error:
                logger.debug(f"Local validation failed, trying introspection: {local_error}")
                if client_id and client_secret:
                    return await self.validate_token_introspect(token, realm, client_id, client_secret)
                else:
                    raise TokenValidationException("Token validation failed and no introspection credentials available")
        
        else:
            raise ValueError(f"Unsupported validation strategy: {self.validation_strategy}")
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.keycloak_client:
            raise TokenValidationException("Keycloak client not configured")
        
        try:
            return await self.keycloak_client.refresh_token(
                refresh_token=refresh_token,
                realm=realm,
                client_id=client_id,
                client_secret=client_secret
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise TokenValidationException(f"Token refresh failed: {str(e)}")
    
    async def logout_user(
        self,
        refresh_token: str,
        realm: str,
        client_id: str,
        client_secret: str
    ) -> bool:
        """Logout user by revoking tokens."""
        if not self.keycloak_client:
            return False
        
        try:
            return await self.keycloak_client.logout(
                refresh_token=refresh_token,
                realm=realm,
                client_id=client_id,
                client_secret=client_secret
            )
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def clear_token_cache(self, realm: Optional[str] = None) -> int:
        """Clear token cache."""
        if self.cache_manager:
            pattern = f"token:{realm}:*" if realm else "token:*"
            return await self.cache_manager.clear_pattern(pattern)
        else:
            keys_to_remove = [
                key for key in self._token_cache.keys()
                if not realm or f":{realm}:" in key
            ]
            for key in keys_to_remove:
                del self._token_cache[key]
            return len(keys_to_remove)