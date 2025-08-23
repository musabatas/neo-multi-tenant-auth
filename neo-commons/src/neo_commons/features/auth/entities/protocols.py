"""Protocol interfaces for auth feature."""

from abc import abstractmethod
from typing import Dict, List, Optional, Protocol, runtime_checkable

from ....core.value_objects.identifiers import KeycloakUserId, RealmId, TenantId, TokenId, UserId
from .auth_context import AuthContext
from .jwt_token import JWTToken
from .keycloak_config import KeycloakConfig
from .realm import Realm


@runtime_checkable
class KeycloakClientProtocol(Protocol):
    """Protocol for Keycloak client operations."""
    
    @abstractmethod
    async def authenticate(
        self, username: str, password: str, realm_id: RealmId
    ) -> JWTToken:
        """Authenticate user with username/password."""
        ...
    
    @abstractmethod
    async def refresh_token(
        self, refresh_token: str, realm_id: RealmId
    ) -> JWTToken:
        """Refresh an access token."""
        ...
    
    @abstractmethod
    async def logout(
        self, refresh_token: str, realm_id: RealmId
    ) -> None:
        """Logout user and invalidate tokens."""
        ...
    
    @abstractmethod
    async def get_user_info(
        self, access_token: str, realm_id: RealmId
    ) -> Dict:
        """Get user information from token."""
        ...
    
    @abstractmethod
    async def introspect_token(
        self, token: str, realm_id: RealmId
    ) -> Dict:
        """Introspect token to get metadata."""
        ...
    
    @abstractmethod
    async def get_realm_public_key(self, realm_id: RealmId) -> str:
        """Get realm's public key for token validation."""
        ...


@runtime_checkable
class JWTValidatorProtocol(Protocol):
    """Protocol for JWT token validation."""
    
    @abstractmethod
    async def validate_token(
        self, token: str, realm_id: RealmId
    ) -> AuthContext:
        """Validate JWT token and return auth context."""
        ...
    
    @abstractmethod
    async def verify_signature(
        self, token: str, public_key: str
    ) -> bool:
        """Verify JWT token signature."""
        ...
    
    @abstractmethod
    async def extract_claims(self, token: str) -> Dict:
        """Extract claims from JWT token without validation."""
        ...
    
    @abstractmethod
    async def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        ...


@runtime_checkable
class RealmManagerProtocol(Protocol):
    """Protocol for multi-realm management."""
    
    @abstractmethod
    async def get_realm_config(self, tenant_id: TenantId) -> KeycloakConfig:
        """Get realm configuration for tenant."""
        ...
    
    @abstractmethod
    async def create_realm(
        self, tenant_id: TenantId, config: KeycloakConfig
    ) -> Realm:
        """Create new realm for tenant."""
        ...
    
    @abstractmethod
    async def update_realm_settings(
        self, realm_id: RealmId, settings: Dict
    ) -> None:
        """Update realm settings."""
        ...
    
    @abstractmethod
    async def delete_realm(self, realm_id: RealmId) -> None:
        """Delete realm."""
        ...
    
    @abstractmethod
    async def list_realms(self) -> List[Realm]:
        """List all managed realms."""
        ...
    
    @abstractmethod
    async def get_realm_by_id(self, realm_id: RealmId) -> Optional[Realm]:
        """Get realm by ID."""
        ...
    
    @abstractmethod
    async def get_realm_by_tenant(self, tenant_id: TenantId) -> Optional[Realm]:
        """Get realm by tenant ID."""
        ...


@runtime_checkable
class UserMapperProtocol(Protocol):
    """Protocol for user ID mapping between Keycloak and platform."""
    
    @abstractmethod
    async def map_keycloak_to_platform(
        self, keycloak_user_id: KeycloakUserId, tenant_id: TenantId
    ) -> UserId:
        """Map Keycloak user ID to platform user ID."""
        ...
    
    @abstractmethod
    async def map_platform_to_keycloak(
        self, platform_user_id: UserId, tenant_id: TenantId
    ) -> Optional[KeycloakUserId]:
        """Map platform user ID to Keycloak user ID."""
        ...
    
    @abstractmethod
    async def create_user_mapping(
        self,
        keycloak_user_id: KeycloakUserId,
        platform_user_id: UserId,
        tenant_id: TenantId,
        user_info: Dict,
    ) -> None:
        """Create user mapping with profile sync."""
        ...
    
    @abstractmethod
    async def sync_user_profile(
        self, platform_user_id: UserId, user_info: Dict
    ) -> None:
        """Sync user profile from Keycloak to platform."""
        ...
    
    @abstractmethod
    async def delete_user_mapping(
        self, platform_user_id: UserId, tenant_id: TenantId
    ) -> None:
        """Delete user mapping."""
        ...


@runtime_checkable
class TokenCacheProtocol(Protocol):
    """Protocol for token caching operations."""
    
    @abstractmethod
    async def cache_token(
        self, token_id: TokenId, auth_context: AuthContext, ttl: int
    ) -> None:
        """Cache validated auth context."""
        ...
    
    @abstractmethod
    async def get_cached_token(self, token_id: TokenId) -> Optional[AuthContext]:
        """Get cached auth context."""
        ...
    
    @abstractmethod
    async def invalidate_token(self, token_id: TokenId) -> None:
        """Invalidate cached token."""
        ...
    
    @abstractmethod
    async def invalidate_user_tokens(self, user_id: UserId) -> None:
        """Invalidate all tokens for user."""
        ...


@runtime_checkable
class PublicKeyCacheProtocol(Protocol):
    """Protocol for public key caching operations."""
    
    @abstractmethod
    async def cache_public_key(
        self, realm_id: RealmId, public_key: str, ttl: int = 3600
    ) -> None:
        """Cache realm public key."""
        ...
    
    @abstractmethod
    async def get_cached_public_key(self, realm_id: RealmId) -> Optional[str]:
        """Get cached public key."""
        ...
    
    @abstractmethod
    async def invalidate_public_key(self, realm_id: RealmId) -> None:
        """Invalidate cached public key."""
        ...


@runtime_checkable
class TokenServiceProtocol(Protocol):
    """Protocol for token service operations."""
    
    @abstractmethod
    async def validate_and_cache_token(
        self, token: str, realm_id: RealmId
    ) -> AuthContext:
        """Validate token and cache auth context."""
        ...
    
    @abstractmethod
    async def invalidate_user_tokens(self, user_id: UserId) -> None:
        """Invalidate all tokens for user."""
        ...
    
    @abstractmethod
    async def refresh_token(
        self, refresh_token: str, realm_id: RealmId
    ) -> JWTToken:
        """Refresh access token."""
        ...


@runtime_checkable 
class AuthServiceProtocol(Protocol):
    """Protocol for auth service operations."""
    
    @abstractmethod
    async def authenticate(
        self, username: str, password: str, realm_id: RealmId
    ) -> AuthContext:
        """Authenticate user and return auth context."""
        ...
    
    @abstractmethod
    async def logout(
        self, refresh_token: str, user_id: UserId
    ) -> None:
        """Logout user and invalidate tokens."""
        ...
    
    @abstractmethod
    async def validate_token(
        self, token: str, realm_id: RealmId
    ) -> AuthContext:
        """Validate token and return auth context."""
        ...