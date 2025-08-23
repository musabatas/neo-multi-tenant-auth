"""JWT token validation service."""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Set

import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidKeyError,
    InvalidSignatureError,
    InvalidTokenError as JWTInvalidTokenError,
)

from ....core.exceptions.auth import (
    InvalidTokenError,
    PublicKeyError,
    TokenExpiredError,
    TokenValidationError,
)
from ....core.value_objects.identifiers import (
    KeycloakUserId,
    PermissionCode,
    RealmId,
    RoleCode,
    TenantId,
    UserId,
)
from ..entities.auth_context import AuthContext
from ..entities.protocols import (
    JWTValidatorProtocol,
    PublicKeyCacheProtocol,
    RealmManagerProtocol,
    UserMapperProtocol,
)

logger = logging.getLogger(__name__)


class JWTValidator(JWTValidatorProtocol):
    """JWT token validation service with caching and realm support."""
    
    def __init__(
        self,
        realm_manager: RealmManagerProtocol,
        user_mapper: UserMapperProtocol,
        public_key_cache: Optional[PublicKeyCacheProtocol] = None,
    ):
        """Initialize JWT validator."""
        self.realm_manager = realm_manager
        self.user_mapper = user_mapper
        self.public_key_cache = public_key_cache
    
    async def validate_token(self, token: str, realm_id: RealmId) -> AuthContext:
        """Validate JWT token and return auth context."""
        logger.debug(f"Validating token for realm {realm_id.value}")
        
        # Get realm configuration
        realm = await self.realm_manager.get_realm_by_id(realm_id)
        if not realm or not realm.config:
            raise TokenValidationError(f"Realm configuration not found: {realm_id.value}")
        
        config = realm.config
        
        try:
            # Get public key for signature verification
            public_key = await self._get_public_key(realm_id)
            
            # Configure JWT decode options
            options = {
                "verify_signature": config.verify_signature,
                "verify_exp": config.verify_exp,
                "verify_nbf": config.verify_nbf,
                "verify_iat": config.verify_iat,
                "verify_aud": config.verify_audience,
            }
            
            # Decode and validate token
            claims = jwt.decode(
                token,
                key=public_key,
                algorithms=config.algorithms,
                audience=config.audience,
                issuer=config.issuer,
                options=options,
            )
            
            logger.debug("Token validation successful")
            
            # Extract user identifiers
            keycloak_user_id = KeycloakUserId(claims.get("sub"))
            if not keycloak_user_id.value:
                raise TokenValidationError("Token missing 'sub' claim")
            
            # Map Keycloak user to platform user
            platform_user_id = await self.user_mapper.map_keycloak_to_platform(
                keycloak_user_id,
                realm.tenant_id,
            )
            
            # Extract roles and permissions from token
            roles, permissions = await self._extract_authorization_data(claims, realm.tenant_id)
            
            # Create auth context
            auth_context = AuthContext.from_token_claims(
                claims=claims,
                user_id=platform_user_id,
                keycloak_user_id=keycloak_user_id,
                tenant_id=realm.tenant_id,
                realm_id=realm_id,
                roles=roles,
                permissions=permissions,
            )
            
            logger.info(f"Created auth context for user {platform_user_id.value}")
            return auth_context
        
        except ExpiredSignatureError as e:
            logger.warning(f"Token expired for realm {realm_id.value}")
            raise TokenExpiredError("Token has expired") from e
        
        except (InvalidSignatureError, InvalidKeyError) as e:
            logger.warning(f"Invalid token signature for realm {realm_id.value}")
            raise InvalidTokenError("Token signature is invalid") from e
        
        except InvalidAudienceError as e:
            logger.warning(f"Invalid token audience for realm {realm_id.value}")
            raise InvalidTokenError("Token audience is invalid") from e
        
        except (DecodeError, JWTInvalidTokenError) as e:
            logger.warning(f"Token decode error for realm {realm_id.value}: {e}")
            raise InvalidTokenError("Token format is invalid") from e
        
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            raise TokenValidationError(f"Token validation failed: {e}") from e
    
    async def verify_signature(self, token: str, public_key: str) -> bool:
        """Verify JWT token signature."""
        try:
            jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256", "ES256", "HS256"],
                options={"verify_exp": False, "verify_aud": False},
            )
            return True
        
        except (InvalidSignatureError, InvalidKeyError, DecodeError):
            return False
    
    async def extract_claims(self, token: str) -> Dict:
        """Extract claims from JWT token without validation."""
        try:
            claims = jwt.decode(
                token,
                options={"verify_signature": False},
            )
            return claims
        
        except DecodeError as e:
            raise InvalidTokenError("Cannot decode token") from e
    
    async def is_token_expired(self, token: str) -> bool:
        """Check if token is expired without full validation."""
        try:
            claims = await self.extract_claims(token)
            exp = claims.get("exp")
            
            if not exp:
                return False  # No expiry claim
            
            exp_datetime = datetime.fromtimestamp(exp, timezone.utc)
            return datetime.now(timezone.utc) >= exp_datetime
        
        except InvalidTokenError:
            return True  # Consider invalid tokens as expired
    
    async def _get_public_key(self, realm_id: RealmId) -> str:
        """Get public key for realm with caching."""
        # Try cache first
        if self.public_key_cache:
            cached_key = await self.public_key_cache.get_cached_public_key(realm_id)
            if cached_key:
                logger.debug(f"Using cached public key for realm {realm_id.value}")
                return cached_key
        
        # Get realm configuration
        realm = await self.realm_manager.get_realm_by_id(realm_id)
        if not realm or not realm.config:
            raise PublicKeyError(f"Realm not found: {realm_id.value}")
        
        try:
            # Get public key from Keycloak
            from ..adapters.keycloak_admin import KeycloakAdminAdapter
            
            # This is a simplified approach - in production, you might want to
            # use a dedicated service or the OpenID adapter
            admin_adapter = KeycloakAdminAdapter(
                server_url=realm.config.server_url,
                username="admin",  # This would come from configuration
                password="admin",  # This would come from configuration
            )
            
            async with admin_adapter:
                jwks = await admin_adapter.get_realm_jwks(realm.config.realm_name)
                
                # Extract the RSA public key
                for key in jwks.get("keys", []):
                    if key.get("kty") == "RSA" and key.get("use") == "sig":
                        public_key = self._jwk_to_pem(key)
                        
                        # Cache the public key
                        if self.public_key_cache:
                            await self.public_key_cache.cache_public_key(
                                realm_id,
                                public_key,
                                realm.config.public_key_ttl,
                            )
                        
                        logger.debug(f"Retrieved public key for realm {realm_id.value}")
                        return public_key
                
                raise PublicKeyError(f"No RSA signing key found for realm {realm_id.value}")
        
        except Exception as e:
            logger.error(f"Failed to get public key for realm {realm_id.value}: {e}")
            raise PublicKeyError(f"Cannot retrieve public key: {e}") from e
    
    def _jwk_to_pem(self, jwk: Dict) -> str:
        """Convert JWK to PEM format."""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
            import base64
            
            # Decode JWK components
            n = int.from_bytes(
                base64.urlsafe_b64decode(jwk["n"] + "=="),
                byteorder="big"
            )
            e = int.from_bytes(
                base64.urlsafe_b64decode(jwk["e"] + "=="),
                byteorder="big"
            )
            
            # Create RSA public key
            public_numbers = RSAPublicNumbers(e, n)
            public_key = public_numbers.public_key()
            
            # Convert to PEM format
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            
            return pem.decode("utf-8")
        
        except Exception as e:
            raise PublicKeyError(f"Cannot convert JWK to PEM: {e}") from e
    
    async def _extract_authorization_data(
        self, 
        claims: Dict,
        tenant_id: TenantId,
    ) -> tuple[Set[RoleCode], Set[PermissionCode]]:
        """Extract roles and permissions from token claims."""
        roles = set()
        permissions = set()
        
        # Extract realm roles
        realm_access = claims.get("realm_access", {})
        for role in realm_access.get("roles", []):
            try:
                roles.add(RoleCode(role))
            except ValueError:
                logger.warning(f"Invalid role code: {role}")
        
        # Extract client roles
        resource_access = claims.get("resource_access", {})
        for client_id, client_data in resource_access.items():
            for role in client_data.get("roles", []):
                try:
                    roles.add(RoleCode(f"{client_id}:{role}"))
                except ValueError:
                    logger.warning(f"Invalid client role code: {client_id}:{role}")
        
        # Extract custom permissions (if present in token)
        custom_permissions = claims.get("permissions", [])
        for perm in custom_permissions:
            try:
                permissions.add(PermissionCode(perm))
            except ValueError:
                logger.warning(f"Invalid permission code: {perm}")
        
        # TODO: Load additional permissions from database based on roles
        # This would involve querying the permissions service
        
        logger.debug(f"Extracted {len(roles)} roles and {len(permissions)} permissions")
        return roles, permissions