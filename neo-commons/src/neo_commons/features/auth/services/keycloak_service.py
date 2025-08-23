"""Main Keycloak service orchestrating authentication operations."""

import logging
from typing import Dict, Optional

from ....core.exceptions.auth import RealmNotFoundError, UserMappingError
from ....core.value_objects.identifiers import RealmId, TenantId, UserId
from ..adapters.keycloak_openid import KeycloakOpenIDAdapter
from ..entities.auth_context import AuthContext
from ..entities.jwt_token import JWTToken
from ..entities.keycloak_config import KeycloakConfig
from ..entities.protocols import (
    JWTValidatorProtocol,
    KeycloakClientProtocol,
    RealmManagerProtocol,
    UserMapperProtocol,
)

logger = logging.getLogger(__name__)


class KeycloakService(KeycloakClientProtocol):
    """Main Keycloak service for authentication operations."""
    
    def __init__(
        self,
        realm_manager: RealmManagerProtocol,
        jwt_validator: JWTValidatorProtocol,
        user_mapper: UserMapperProtocol,
    ):
        """Initialize Keycloak service."""
        self.realm_manager = realm_manager
        self.jwt_validator = jwt_validator
        self.user_mapper = user_mapper
        self._adapters: Dict[str, KeycloakOpenIDAdapter] = {}
    
    async def _get_adapter(self, realm_id: RealmId) -> KeycloakOpenIDAdapter:
        """Get or create Keycloak adapter for realm."""
        realm_key = realm_id.value
        
        if realm_key not in self._adapters:
            # Get realm configuration
            realm = await self.realm_manager.get_realm_by_id(realm_id)
            if not realm or not realm.config:
                raise RealmNotFoundError(f"Realm configuration not found: {realm_id.value}")
            
            # Create and cache adapter
            adapter = KeycloakOpenIDAdapter(realm.config)
            self._adapters[realm_key] = adapter
        
        return self._adapters[realm_key]
    
    async def authenticate(self, username: str, password: str, realm_id: RealmId) -> JWTToken:
        """Authenticate user with username/password."""
        logger.info(f"Authenticating user {username} in realm {realm_id.value}")
        
        adapter = await self._get_adapter(realm_id)
        
        async with adapter:
            token = await adapter.authenticate(username, password)
        
        logger.info(f"Successfully authenticated user {username}")
        return token
    
    async def authenticate_and_create_context(
        self,
        username: str,
        password: str,
        tenant_id: TenantId,
    ) -> tuple[JWTToken, AuthContext]:
        """Authenticate user and create full auth context."""
        logger.info(f"Authenticating user {username} for tenant {tenant_id.value}")
        
        # Get realm for tenant
        realm = await self.realm_manager.get_realm_by_tenant(tenant_id)
        if not realm:
            raise RealmNotFoundError(f"No realm found for tenant: {tenant_id.value}")
        
        # Authenticate
        token = await self.authenticate(username, password, realm.realm_id)
        
        # Create auth context
        auth_context = await self.jwt_validator.validate_token(
            token.access_token, 
            realm.realm_id
        )
        
        logger.info(f"Created auth context for user {auth_context.user_id.value}")
        return token, auth_context
    
    async def refresh_token(self, refresh_token: str, realm_id: RealmId) -> JWTToken:
        """Refresh an access token."""
        logger.debug(f"Refreshing token in realm {realm_id.value}")
        
        adapter = await self._get_adapter(realm_id)
        
        async with adapter:
            token = await adapter.refresh_token(refresh_token)
        
        logger.info("Successfully refreshed token")
        return token
    
    async def logout(self, refresh_token: str, realm_id: RealmId) -> None:
        """Logout user and invalidate tokens."""
        logger.info(f"Logging out user in realm {realm_id.value}")
        
        adapter = await self._get_adapter(realm_id)
        
        async with adapter:
            await adapter.logout(refresh_token)
        
        logger.info("Successfully logged out user")
    
    async def get_user_info(self, access_token: str, realm_id: RealmId) -> Dict:
        """Get user information from access token."""
        logger.debug(f"Getting user info from realm {realm_id.value}")
        
        adapter = await self._get_adapter(realm_id)
        
        async with adapter:
            user_info = await adapter.get_user_info(access_token)
        
        return user_info
    
    async def introspect_token(self, token: str, realm_id: RealmId) -> Dict:
        """Introspect token to get metadata."""
        logger.debug(f"Introspecting token in realm {realm_id.value}")
        
        adapter = await self._get_adapter(realm_id)
        
        async with adapter:
            introspection = await adapter.introspect_token(token)
        
        return introspection
    
    async def get_realm_public_key(self, realm_id: RealmId) -> str:
        """Get realm's public key for token validation."""
        logger.debug(f"Getting public key for realm {realm_id.value}")
        
        adapter = await self._get_adapter(realm_id)
        
        async with adapter:
            public_key = await adapter.get_public_key()
        
        return public_key
    
    async def validate_token_and_create_context(
        self, 
        access_token: str, 
        realm_id: RealmId
    ) -> AuthContext:
        """Validate token and create auth context."""
        logger.debug(f"Validating token and creating context for realm {realm_id.value}")
        
        # Validate token and get auth context
        auth_context = await self.jwt_validator.validate_token(access_token, realm_id)
        
        logger.debug(f"Created auth context for user {auth_context.user_id.value}")
        return auth_context
    
    async def exchange_token(
        self,
        token: str,
        realm_id: RealmId,
        audience: str,
    ) -> JWTToken:
        """Exchange token for another token (cross-realm or audience)."""
        logger.info(f"Exchanging token in realm {realm_id.value} for audience {audience}")
        
        adapter = await self._get_adapter(realm_id)
        
        async with adapter:
            # exchange_token needs client_id, audience, and optionally subject
            # Using the realm's configured client_id as the target client
            realm = await self.realm_manager.get_realm_by_id(realm_id)
            client_id = realm.config.client_id if realm and realm.config else "account"
            new_token = await adapter.exchange_token(token, client_id, audience, None)
        
        logger.info("Successfully exchanged token")
        return new_token
    
    async def create_user_session(
        self,
        username: str,
        password: str,
        tenant_id: TenantId,
    ) -> tuple[JWTToken, AuthContext]:
        """Create complete user session with token and context."""
        logger.info(f"Creating user session for {username} in tenant {tenant_id.value}")
        
        # Authenticate and create context
        token, auth_context = await self.authenticate_and_create_context(
            username, password, tenant_id
        )
        
        # Ensure user mapping exists
        try:
            mapped_user_id = await self.user_mapper.map_keycloak_to_platform(
                auth_context.keycloak_user_id,
                tenant_id,
            )
            
            # Update auth context with mapped user ID if different
            if mapped_user_id != auth_context.user_id:
                # Create new auth context with correct user ID
                auth_context = AuthContext(
                    user_id=mapped_user_id,
                    keycloak_user_id=auth_context.keycloak_user_id,
                    tenant_id=auth_context.tenant_id,
                    realm_id=auth_context.realm_id,
                    email=auth_context.email,
                    username=auth_context.username,
                    first_name=auth_context.first_name,
                    last_name=auth_context.last_name,
                    display_name=auth_context.display_name,
                    authenticated_at=auth_context.authenticated_at,
                    expires_at=auth_context.expires_at,
                    session_id=auth_context.session_id,
                    roles=auth_context.roles,
                    permissions=auth_context.permissions,
                    scopes=auth_context.scopes,
                    token_claims=auth_context.token_claims,
                    metadata=auth_context.metadata,
                )
        
        except UserMappingError as e:
            logger.error(f"Failed to create user mapping: {e}")
            # Continue with original auth context - mapping will be created later
        
        logger.info(f"Created complete user session for {auth_context.user_id.value}")
        return token, auth_context
    
    async def cleanup_realm_adapters(self, realm_id: RealmId) -> None:
        """Cleanup cached adapters for realm (useful when realm config changes)."""
        realm_key = realm_id.value
        if realm_key in self._adapters:
            del self._adapters[realm_key]
            logger.info(f"Cleaned up adapter cache for realm {realm_key}")
    
    async def close_all_adapters(self) -> None:
        """Close all cached adapters."""
        for adapter in self._adapters.values():
            try:
                async with adapter:
                    pass  # Context manager will handle cleanup
            except Exception as e:
                logger.warning(f"Error closing adapter: {e}")
        
        self._adapters.clear()
        logger.info("Closed all Keycloak adapters")