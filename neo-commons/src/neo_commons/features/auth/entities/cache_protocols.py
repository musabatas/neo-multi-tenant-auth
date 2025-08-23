"""Cache protocol interfaces for auth services."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Protocol, runtime_checkable

from ....core.value_objects.identifiers import RealmId, TenantId, UserId
from .auth_context import AuthContext


@runtime_checkable
class PublicKeyCacheProtocol(Protocol):
    """Protocol for caching JWT public keys."""
    
    async def get_public_key(self, realm_id: RealmId) -> Optional[str]:
        """Get cached public key for realm."""
        ...
    
    async def cache_public_key(self, realm_id: RealmId, public_key: str, ttl: int = 3600) -> None:
        """Cache public key for realm."""
        ...
    
    async def invalidate_public_key(self, realm_id: RealmId) -> None:
        """Invalidate cached public key."""
        ...


@runtime_checkable  
class TokenCacheProtocol(Protocol):
    """Protocol for caching validated tokens and auth contexts."""
    
    async def get_cached_token(self, token_id: str) -> Optional[AuthContext]:
        """Get cached auth context for token."""
        ...
    
    async def cache_token(self, token_id: str, auth_context: AuthContext, ttl: int) -> None:
        """Cache validated token and auth context."""
        ...
    
    async def invalidate_token(self, token_id: str) -> None:
        """Invalidate specific cached token."""
        ...
    
    async def invalidate_user_tokens(self, user_id: UserId) -> None:
        """Invalidate all cached tokens for user."""
        ...


@runtime_checkable
class UserMappingCacheProtocol(Protocol):
    """Protocol for caching user ID mappings."""
    
    async def get_user_mapping(
        self, 
        keycloak_user_id: str, 
        tenant_id: TenantId,
    ) -> Optional[Dict]:
        """Get cached user mapping."""
        ...
    
    async def cache_user_mapping(
        self,
        keycloak_user_id: str,
        tenant_id: TenantId, 
        mapping_data: Dict,
        ttl: int = 1800,
    ) -> None:
        """Cache user mapping data."""
        ...
    
    async def invalidate_user_mapping(
        self, 
        keycloak_user_id: str, 
        tenant_id: TenantId,
    ) -> None:
        """Invalidate specific user mapping."""
        ...
    
    async def invalidate_tenant_mappings(self, tenant_id: TenantId) -> None:
        """Invalidate all user mappings for tenant."""
        ...


@runtime_checkable
class RealmConfigCacheProtocol(Protocol):
    """Protocol for caching realm configurations."""
    
    async def get_realm_config(self, tenant_id: TenantId) -> Optional[Dict]:
        """Get cached realm configuration."""
        ...
    
    async def cache_realm_config(
        self,
        tenant_id: TenantId,
        config_data: Dict,
        ttl: int = 3600,
    ) -> None:
        """Cache realm configuration."""
        ...
    
    async def invalidate_realm_config(self, tenant_id: TenantId) -> None:
        """Invalidate cached realm configuration."""
        ...
    
    async def invalidate_all_realm_configs(self) -> None:
        """Invalidate all cached realm configurations."""
        ...


@runtime_checkable
class AuthCacheManagerProtocol(Protocol):
    """Protocol for unified auth cache management."""
    
    # Public key operations
    async def get_public_key(self, realm_id: RealmId) -> Optional[str]:
        """Get cached public key."""
        ...
    
    async def cache_public_key(self, realm_id: RealmId, public_key: str, ttl: int = 3600) -> None:
        """Cache public key."""
        ...
    
    # Token operations
    async def get_cached_token(self, token_id: str) -> Optional[AuthContext]:
        """Get cached auth context."""
        ...
    
    async def cache_token(self, token_id: str, auth_context: AuthContext, ttl: int) -> None:
        """Cache auth context."""
        ...
    
    # User mapping operations
    async def get_user_mapping(self, keycloak_user_id: str, tenant_id: TenantId) -> Optional[Dict]:
        """Get cached user mapping."""
        ...
    
    async def cache_user_mapping(
        self,
        keycloak_user_id: str,
        tenant_id: TenantId,
        mapping_data: Dict,
        ttl: int = 1800,
    ) -> None:
        """Cache user mapping."""
        ...
    
    # Realm config operations
    async def get_realm_config(self, tenant_id: TenantId) -> Optional[Dict]:
        """Get cached realm config."""
        ...
    
    async def cache_realm_config(
        self,
        tenant_id: TenantId,
        config_data: Dict,
        ttl: int = 3600,
    ) -> None:
        """Cache realm config."""
        ...
    
    # Invalidation operations
    async def invalidate_user_tokens(self, user_id: UserId) -> None:
        """Invalidate all tokens for user."""
        ...
    
    async def invalidate_tenant_data(self, tenant_id: TenantId) -> None:
        """Invalidate all cached data for tenant."""
        ...
    
    async def invalidate_realm_data(self, realm_id: RealmId) -> None:
        """Invalidate all cached data for realm."""
        ...
    
    async def health_check(self) -> Dict[str, bool]:
        """Check cache connectivity and health."""
        ...


# Abstract base classes for concrete implementations

class BaseAuthCache(ABC):
    """Base class for auth cache implementations."""
    
    @abstractmethod
    async def _get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        pass
    
    @abstractmethod 
    async def _set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def _delete(self, key: str) -> None:
        """Delete key from cache.""" 
        pass
    
    @abstractmethod
    async def _delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        pass
    
    @abstractmethod
    async def _exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    def _make_public_key_key(self, realm_id: RealmId) -> str:
        """Generate cache key for public key."""
        return f"auth:public_key:{realm_id.value}"
    
    def _make_token_key(self, token_id: str) -> str:
        """Generate cache key for token."""
        return f"auth:token:{token_id}"
    
    def _make_user_mapping_key(self, keycloak_user_id: str, tenant_id: TenantId) -> str:
        """Generate cache key for user mapping."""
        return f"auth:user_mapping:{tenant_id.value}:{keycloak_user_id}"
    
    def _make_realm_config_key(self, tenant_id: TenantId) -> str:
        """Generate cache key for realm config."""
        return f"auth:realm_config:{tenant_id.value}"
    
    def _make_user_tokens_pattern(self, user_id: UserId) -> str:
        """Generate pattern for user tokens."""
        return f"auth:token:*:user:{user_id.value}"
    
    def _make_tenant_pattern(self, tenant_id: TenantId) -> str:
        """Generate pattern for tenant data."""
        return f"auth:*:{tenant_id.value}:*"