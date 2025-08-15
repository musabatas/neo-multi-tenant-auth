"""
Keycloak token validator for JWT validation and user context extraction.

Handles JWT token validation using Keycloak public keys with caching.
"""
import jwt
import httpx
from typing import Dict, Any, Optional
from loguru import logger

from ...domain.protocols.cache_protocols import AuthCacheProtocol


class KeycloakTokenValidator:
    """
    Keycloak JWT token validator with public key caching.
    
    Validates JWT tokens using Keycloak's public keys and extracts
    user information for authorization decisions.
    """

    def __init__(
        self,
        keycloak_base_url: str,
        cache: AuthCacheProtocol,
        default_realm: str = "master"
    ):
        self._keycloak_base_url = keycloak_base_url.rstrip("/")
        self._cache = cache
        self._default_realm = default_realm
        self._http_client = httpx.AsyncClient(timeout=10.0)

    async def validate_token(
        self,
        token: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate JWT token and extract claims.
        
        Args:
            token: JWT token from Authorization header
            tenant_id: Optional tenant ID for multi-realm setup
            
        Returns:
            Token claims if valid
            
        Raises:
            ValueError: If token is invalid, expired, or malformed
        """
        try:
            # Decode token header to get key ID and algorithm
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get("kid")
            algorithm = unverified_header.get("alg", "RS256")
            
            if not key_id:
                raise ValueError("Token missing key ID (kid) in header")
            
            # Get realm name (tenant-specific or default)
            realm_name = f"tenant-{tenant_id}" if tenant_id else self._default_realm
            
            # Get public key for validation
            public_key = await self._get_public_key(realm_name, key_id)
            if not public_key:
                raise ValueError(f"Public key {key_id} not found for realm {realm_name}")
            
            # Validate and decode token
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": False,  # Audience validation is optional
                    "require": ["exp", "iat", "sub"]
                }
            )
            
            # Additional validation
            await self._validate_token_claims(claims, realm_name, tenant_id)
            
            logger.debug(
                f"Token validated for user {claims.get('sub')}",
                extra={
                    "user_id": claims.get("sub"),
                    "realm": realm_name,
                    "tenant_id": tenant_id,
                    "key_id": key_id
                }
            )
            
            return claims
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise ValueError(f"Token validation failed: {str(e)}")

    async def _get_public_key(self, realm_name: str, key_id: str) -> Optional[str]:
        """Get public key for token validation with caching."""
        # Try cache first
        cached_keys = await self._cache.get_realm_keys(realm_name)
        if cached_keys and key_id in cached_keys:
            return cached_keys[key_id]
        
        # Fetch from Keycloak
        try:
            url = f"{self._keycloak_base_url}/realms/{realm_name}/protocol/openid_connect/certs"
            response = await self._http_client.get(url)
            response.raise_for_status()
            
            jwks = response.json()
            keys = {}
            
            for key_data in jwks.get("keys", []):
                if key_data.get("use") == "sig" and key_data.get("kty") == "RSA":
                    kid = key_data.get("kid")
                    if kid:
                        # Convert JWK to PEM format
                        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                        pem_key = public_key.public_bytes(
                            encoding=jwt.algorithms.serialization.Encoding.PEM,
                            format=jwt.algorithms.serialization.PublicFormat.SubjectPublicKeyInfo
                        ).decode('utf-8')
                        keys[kid] = pem_key
            
            if keys:
                # Cache keys for 1 hour
                await self._cache.set_realm_keys(realm_name, keys, ttl=3600)
                logger.debug(
                    f"Cached {len(keys)} public keys for realm {realm_name}",
                    extra={"realm": realm_name, "key_count": len(keys)}
                )
            
            return keys.get(key_id)
            
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch Keycloak public keys: {e}")
            raise ValueError(f"Unable to fetch Keycloak public keys: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing Keycloak public keys: {e}")
            raise ValueError(f"Error processing public keys: {str(e)}")

    async def _validate_token_claims(
        self,
        claims: Dict[str, Any],
        realm_name: str,
        tenant_id: Optional[str]
    ) -> None:
        """Perform additional validation on token claims."""
        # Validate issuer
        expected_issuer = f"{self._keycloak_base_url}/realms/{realm_name}"
        actual_issuer = claims.get("iss")
        if actual_issuer != expected_issuer:
            raise ValueError(f"Invalid issuer: expected {expected_issuer}, got {actual_issuer}")
        
        # Validate token type
        token_type = claims.get("typ")
        if token_type and token_type.lower() not in ["bearer", "access_token"]:
            raise ValueError(f"Invalid token type: {token_type}")
        
        # Validate subject exists
        if not claims.get("sub"):
            raise ValueError("Token missing subject (sub) claim")
        
        # Additional tenant-specific validation
        if tenant_id:
            # Could validate tenant-specific claims here
            pass
        
        logger.debug(
            "Token claims validated successfully",
            extra={
                "issuer": actual_issuer,
                "subject": claims.get("sub"),
                "realm": realm_name,
                "tenant_id": tenant_id
            }
        )

    async def get_realm_info(self, realm_name: str) -> Dict[str, Any]:
        """Get realm information from Keycloak."""
        try:
            url = f"{self._keycloak_base_url}/realms/{realm_name}"
            response = await self._http_client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch realm info: {e}")
            raise ValueError(f"Unable to fetch realm info: {str(e)}")

    async def verify_realm_exists(self, realm_name: str) -> bool:
        """Verify if a realm exists in Keycloak."""
        try:
            await self.get_realm_info(realm_name)
            return True
        except ValueError:
            return False

    async def invalidate_realm_cache(self, realm_name: str) -> None:
        """Invalidate cached keys for a realm."""
        await self._cache.invalidate_realm_keys(realm_name)
        logger.info(f"Invalidated cache for realm {realm_name}")

    async def close(self) -> None:
        """Close HTTP client."""
        await self._http_client.aclose()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            import asyncio
            if hasattr(self, '_http_client'):
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._http_client.aclose())
        except Exception:
            pass  # Ignore cleanup errors