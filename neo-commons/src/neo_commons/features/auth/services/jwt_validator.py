"""JWT token validation service."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

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
        database_service=None,
    ):
        """Initialize JWT validator."""
        self.realm_manager = realm_manager
        self.user_mapper = user_mapper
        self.public_key_cache = public_key_cache
        self.database_service = database_service
    
    async def validate_token(self, token: str, realm_id: RealmId) -> AuthContext:
        """Validate JWT token and return auth context."""
        logger.debug(f"Validating token for realm {realm_id.value}")
        
        # Get realm configuration and realm object (supports both custom and database-stored realms)
        try:
            config = await self.realm_manager.get_realm_config_by_id(realm_id)
            realm = await self.realm_manager.get_realm_by_id(realm_id)
        except Exception as e:
            raise TokenValidationError(f"Realm configuration not found: {realm_id.value}") from e
        
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
            # For platform admin (no tenant), use None for tenant_id
            platform_user_id = await self.user_mapper.map_keycloak_to_platform(
                keycloak_user_id,
                realm.tenant_id,  # This can be None for platform admin
            )
            
            # Load roles and permissions from database ONLY
            logger.info(f"Database service availability: {self.database_service is not None}")
            if self.database_service:
                # Load from database (ONLY source for roles and permissions)
                logger.info(f"Loading database permissions for user {platform_user_id.value}, tenant: {realm.tenant_id}")
                try:
                    roles, permissions, permission_metadata = await self._load_database_permissions(platform_user_id, realm.tenant_id)
                    logger.info(f"Database loading result: {len(roles)} roles, {len(permissions)} permissions")
                except Exception as e:
                    logger.error(f"Database permission loading failed: {e}")
                    # No fallback - empty roles and permissions if database fails
                    roles, permissions, permission_metadata = set(), set(), []
            else:
                # No database service - no roles or permissions
                logger.warning("No database service available - user will have no roles or permissions")
                roles, permissions, permission_metadata = set(), set(), []
            
            # Create auth context with permission metadata
            auth_context = AuthContext.from_token_claims(
                claims=claims,
                user_id=platform_user_id,
                keycloak_user_id=keycloak_user_id,
                tenant_id=realm.tenant_id,
                realm_id=realm_id,
                roles=roles,
                permissions=permissions,
            )
            
            # Store rich permission metadata in auth context metadata
            if permission_metadata:
                auth_context.metadata['rich_permissions'] = permission_metadata
            
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
            cached_key = await self.public_key_cache.get_public_key(realm_id)
            if cached_key:
                logger.debug(f"Using cached public key for realm {realm_id.value}")
                return cached_key
        
        # Get realm configuration
        try:
            config = await self.realm_manager.get_realm_config_by_id(realm_id)
        except Exception as e:
            raise PublicKeyError(f"Realm configuration not found: {realm_id.value}") from e
        
        try:
            # Get public key from Keycloak
            from ..adapters.keycloak_admin import KeycloakAdminAdapter
            
            # This is a simplified approach - in production, you might want to
            # use a dedicated service or the OpenID adapter
            admin_adapter = KeycloakAdminAdapter(
                server_url=config.server_url,
                username="admin",  # This would come from configuration
                password="admin",  # This would come from configuration
            )
            
            async with admin_adapter:
                jwks = await admin_adapter.get_realm_jwks(config.realm_name)
                
                # Extract the RSA public key
                for key in jwks.get("keys", []):
                    if key.get("kty") == "RSA" and key.get("use") == "sig":
                        public_key = self._jwk_to_pem(key)
                        
                        # Cache the public key
                        if self.public_key_cache:
                            await self.public_key_cache.cache_public_key(
                                realm_id,
                                public_key,
                                config.public_key_ttl,
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
    

    async def _load_database_permissions(
        self, 
        user_id: UserId, 
        tenant_id: Optional[TenantId]
    ) -> tuple[Set[RoleCode], Set[PermissionCode], List[Dict]]:
        """Load roles and permissions from database using injected database service."""
        try:
            from ...users.services.user_permission_service import UserPermissionService
            
            permission_service = UserPermissionService(self.database_service)
            
            # Get user auth context from database
            user_auth_context = await permission_service.get_user_auth_context(
                user_id, tenant_id
            )
            
            # Convert database results to AuthContext format
            db_roles = {RoleCode(role_code) for role_code in user_auth_context['roles']['codes']}
            
            # Extract permission codes for AuthContext checking functionality
            db_permission_codes = {PermissionCode(perm['code']) for perm in user_auth_context['permissions']}
            
            # Store full permission details in metadata for response
            permission_metadata = user_auth_context['permissions']
            
            logger.debug(f"Loaded {len(db_roles)} roles and {len(db_permission_codes)} permissions from database")
            return db_roles, db_permission_codes, permission_metadata
            
        except Exception as e:
            logger.error(f"Failed to load database permissions for user {user_id.value}: {e}")
            # Fallback to empty sets if database loading fails
            return set(), set(), []