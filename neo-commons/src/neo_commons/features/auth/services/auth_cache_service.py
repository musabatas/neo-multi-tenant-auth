"""Auth-specific cache service for caching user permissions, roles, and auth data."""

import logging
import json
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone

from ....features.cache.services.cache_service import CacheService
from ....core.value_objects.identifiers import UserId, TenantId, RoleCode, PermissionCode
from ....core.exceptions import CacheError
from ..entities.auth_context import AuthContext

logger = logging.getLogger(__name__)


class AuthCacheService:
    """Service for caching authentication and authorization data."""
    
    def __init__(self, cache_service: CacheService):
        """Initialize auth cache service.
        
        Args:
            cache_service: The underlying cache service to use
        """
        self.cache_service = cache_service
        self._default_ttl = 3600  # 1 hour default
        self._permissions_ttl = 1800  # 30 minutes for permissions
        self._roles_ttl = 3600  # 1 hour for roles
        self._user_data_ttl = 600  # 10 minutes for user data
    
    def configure_ttl(self, 
                     default_ttl: Optional[int] = None,
                     permissions_ttl: Optional[int] = None,
                     roles_ttl: Optional[int] = None,
                     user_data_ttl: Optional[int] = None) -> None:
        """Configure TTL values for different cache types.
        
        Args:
            default_ttl: Default TTL in seconds
            permissions_ttl: TTL for permissions cache
            roles_ttl: TTL for roles cache
            user_data_ttl: TTL for user data cache
        """
        if default_ttl is not None:
            self._default_ttl = default_ttl
        if permissions_ttl is not None:
            self._permissions_ttl = permissions_ttl
        if roles_ttl is not None:
            self._roles_ttl = roles_ttl
        if user_data_ttl is not None:
            self._user_data_ttl = user_data_ttl
    
    # ========== User Permissions Cache ==========
    
    async def get_user_permissions(self, 
                                  user_id: UserId, 
                                  tenant_id: TenantId) -> Optional[Set[PermissionCode]]:
        """Get cached user permissions.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            Set of permission codes if cached, None otherwise
        """
        key = self._build_permissions_key(user_id, tenant_id)
        cached_data = await self.cache_service.get(key)
        
        if cached_data:
            try:
                # Deserialize from JSON list to set of PermissionCode
                permission_list = json.loads(cached_data)
                return {PermissionCode(perm) for perm in permission_list}
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to deserialize permissions cache: {e}")
                await self.cache_service.delete(key)
        
        return None
    
    async def set_user_permissions(self,
                                  user_id: UserId,
                                  tenant_id: TenantId,
                                  permissions: Set[PermissionCode],
                                  ttl: Optional[int] = None) -> None:
        """Cache user permissions.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            permissions: Set of permission codes
            ttl: Optional TTL override in seconds
        """
        key = self._build_permissions_key(user_id, tenant_id)
        ttl = ttl or self._permissions_ttl
        
        # Serialize to JSON list
        permission_list = [perm.value for perm in permissions]
        cached_data = json.dumps(permission_list)
        
        await self.cache_service.set(key, cached_data, ttl)
        tenant_display = tenant_id.value if tenant_id else "platform"
        logger.debug(f"Cached {len(permissions)} permissions for user {user_id.value} in tenant {tenant_display}")
    
    # ========== User Roles Cache ==========
    
    async def get_user_roles(self,
                            user_id: UserId,
                            tenant_id: TenantId) -> Optional[Set[RoleCode]]:
        """Get cached user roles.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            Set of role codes if cached, None otherwise
        """
        key = self._build_roles_key(user_id, tenant_id)
        cached_data = await self.cache_service.get(key)
        
        if cached_data:
            try:
                # Deserialize from JSON list to set of RoleCode
                role_list = json.loads(cached_data)
                return {RoleCode(role) for role in role_list}
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to deserialize roles cache: {e}")
                await self.cache_service.delete(key)
        
        return None
    
    async def set_user_roles(self,
                            user_id: UserId,
                            tenant_id: TenantId,
                            roles: Set[RoleCode],
                            ttl: Optional[int] = None) -> None:
        """Cache user roles.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            roles: Set of role codes
            ttl: Optional TTL override in seconds
        """
        key = self._build_roles_key(user_id, tenant_id)
        ttl = ttl or self._roles_ttl
        
        # Serialize to JSON list
        role_list = [role.value for role in roles]
        cached_data = json.dumps(role_list)
        
        await self.cache_service.set(key, cached_data, ttl)
        tenant_display = tenant_id.value if tenant_id else "platform"
        logger.debug(f"Cached {len(roles)} roles for user {user_id.value} in tenant {tenant_display}")
    
    # ========== Complete User Data Cache ==========
    
    async def get_user_data(self,
                           user_id: UserId,
                           tenant_id: TenantId) -> Optional[Dict[str, Any]]:
        """Get complete cached user data.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            User data dictionary if cached, None otherwise
        """
        key = self._build_user_data_key(user_id, tenant_id)
        cached_data = await self.cache_service.get(key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to deserialize user data cache: {e}")
                await self.cache_service.delete(key)
        
        return None
    
    async def set_user_data(self,
                           user_id: UserId,
                           tenant_id: TenantId,
                           user_data: Dict[str, Any],
                           ttl: Optional[int] = None) -> None:
        """Cache complete user data.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            user_data: User data dictionary
            ttl: Optional TTL override in seconds
        """
        key = self._build_user_data_key(user_id, tenant_id)
        ttl = ttl or self._user_data_ttl
        
        cached_data = json.dumps(user_data)
        await self.cache_service.set(key, cached_data, ttl)
        tenant_display = tenant_id.value if tenant_id else "platform"
        logger.debug(f"Cached user data for user {user_id.value} in tenant {tenant_display}")
    
    # ========== Auth Context Cache ==========
    
    async def get_auth_context(self,
                              user_id: UserId,
                              tenant_id: TenantId) -> Optional[AuthContext]:
        """Get cached auth context.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            AuthContext if cached and valid, None otherwise
        """
        key = self._build_auth_context_key(user_id, tenant_id)
        cached_data = await self.cache_service.get(key)
        
        if cached_data:
            try:
                data = json.loads(cached_data)
                # Reconstruct AuthContext from cached data
                from neo_commons.core.value_objects.identifiers import KeycloakUserId, RealmId
                
                auth_context = AuthContext(
                    user_id=UserId(data['user_id']),
                    keycloak_user_id=KeycloakUserId(data['keycloak_user_id']),
                    tenant_id=TenantId(data['tenant_id']) if data.get('tenant_id') else None,
                    realm_id=RealmId(data['realm_id']),
                    email=data.get('email'),
                    username=data.get('username'),
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    display_name=data.get('display_name'),
                    authenticated_at=datetime.fromisoformat(data['authenticated_at']) if data.get('authenticated_at') else None,
                    expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
                    session_id=data.get('session_id'),
                    roles={RoleCode(r) for r in data.get('roles', [])},
                    permissions={PermissionCode(p) for p in data.get('permissions', [])},
                    scopes=set(data.get('scopes', [])),
                    token_claims=data.get('token_claims', {}),
                    metadata=data.get('metadata', {})
                )
                
                # Check if context is still valid
                if auth_context.expires_at and auth_context.expires_at > datetime.now(timezone.utc):
                    return auth_context
                else:
                    # Context expired, remove from cache
                    await self.cache_service.delete(key)
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to deserialize auth context cache: {e}")
                await self.cache_service.delete(key)
        
        return None
    
    async def set_auth_context(self,
                              auth_context: AuthContext,
                              ttl: Optional[int] = None) -> None:
        """Cache auth context.
        
        Args:
            auth_context: The auth context to cache
            ttl: Optional TTL override in seconds
        """
        if not auth_context.tenant_id:
            # Don't cache auth contexts without tenant (e.g., admin users)
            return
            
        key = self._build_auth_context_key(auth_context.user_id, auth_context.tenant_id)
        
        # Calculate TTL based on token expiration if not provided
        if ttl is None and auth_context.expires_at:
            remaining_seconds = int((auth_context.expires_at - datetime.now(timezone.utc)).total_seconds())
            ttl = min(remaining_seconds, self._default_ttl) if remaining_seconds > 0 else self._default_ttl
        else:
            ttl = ttl or self._default_ttl
        
        # Serialize auth context to cacheable format
        data = {
            'user_id': auth_context.user_id.value,
            'keycloak_user_id': auth_context.keycloak_user_id.value,
            'tenant_id': auth_context.tenant_id.value if auth_context.tenant_id else None,
            'realm_id': auth_context.realm_id.value,
            'email': auth_context.email,
            'username': auth_context.username,
            'first_name': auth_context.first_name,
            'last_name': auth_context.last_name,
            'display_name': auth_context.display_name,
            'authenticated_at': auth_context.authenticated_at.isoformat() if auth_context.authenticated_at else None,
            'expires_at': auth_context.expires_at.isoformat() if auth_context.expires_at else None,
            'session_id': auth_context.session_id,
            'roles': [r.value for r in auth_context.roles],
            'permissions': [p.value for p in auth_context.permissions],
            'scopes': list(auth_context.scopes),
            'token_claims': auth_context.token_claims,
            'metadata': auth_context.metadata
        }
        
        cached_data = json.dumps(data)
        await self.cache_service.set(key, cached_data, ttl)
        logger.debug(f"Cached auth context for user {auth_context.user_id.value}")
    
    # ========== Cache Invalidation ==========
    
    async def invalidate_user(self,
                             user_id: UserId,
                             tenant_id: TenantId) -> int:
        """Invalidate all cached data for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            Number of keys invalidated
        """
        keys = [
            self._build_permissions_key(user_id, tenant_id),
            self._build_roles_key(user_id, tenant_id),
            self._build_user_data_key(user_id, tenant_id),
            self._build_auth_context_key(user_id, tenant_id),
        ]
        
        count = 0
        for key in keys:
            if await self.cache_service.delete(key):
                count += 1
        
        tenant_display = tenant_id.value if tenant_id else "platform"
        logger.info(f"Invalidated {count} cache entries for user {user_id.value} in tenant {tenant_display}")
        return count
    
    async def invalidate_user_permissions(self,
                                         user_id: UserId,
                                         tenant_id: TenantId) -> bool:
        """Invalidate cached permissions for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            True if cache was invalidated
        """
        key = self._build_permissions_key(user_id, tenant_id)
        result = await self.cache_service.delete(key)
        
        if result:
            logger.debug(f"Invalidated permissions cache for user {user_id.value}")
        
        return result
    
    async def invalidate_user_roles(self,
                                   user_id: UserId,
                                   tenant_id: TenantId) -> bool:
        """Invalidate cached roles for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            True if cache was invalidated
        """
        key = self._build_roles_key(user_id, tenant_id)
        result = await self.cache_service.delete(key)
        
        if result:
            logger.debug(f"Invalidated roles cache for user {user_id.value}")
        
        return result
    
    async def invalidate_tenant_auth_data(self, tenant_id: TenantId) -> int:
        """Invalidate all auth cache for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Number of keys invalidated
        """
        patterns = [
            f"auth:permissions:*:{tenant_id.value}",
            f"auth:roles:*:{tenant_id.value}",
            f"auth:user_data:*:{tenant_id.value}",
            f"auth:context:*:{tenant_id.value}",
        ]
        
        total_count = 0
        for pattern in patterns:
            count = await self.cache_service.delete_pattern(pattern)
            total_count += count
        
        logger.info(f"Invalidated {total_count} auth cache entries for tenant {tenant_id.value}")
        return total_count
    
    # ========== Helper Methods ==========
    
    def _build_permissions_key(self, user_id: UserId, tenant_id: TenantId) -> str:
        """Build cache key for user permissions."""
        tenant_value = tenant_id.value if tenant_id else "platform"
        return f"auth:permissions:{user_id.value}:{tenant_value}"
    
    def _build_roles_key(self, user_id: UserId, tenant_id: TenantId) -> str:
        """Build cache key for user roles."""
        tenant_value = tenant_id.value if tenant_id else "platform"
        return f"auth:roles:{user_id.value}:{tenant_value}"
    
    def _build_user_data_key(self, user_id: UserId, tenant_id: TenantId) -> str:
        """Build cache key for user data."""
        tenant_value = tenant_id.value if tenant_id else "platform"
        return f"auth:user_data:{user_id.value}:{tenant_value}"
    
    def _build_auth_context_key(self, user_id: UserId, tenant_id: TenantId) -> str:
        """Build cache key for auth context."""
        tenant_value = tenant_id.value if tenant_id else "platform"
        return f"auth:context:{user_id.value}:{tenant_value}"
    
    # ========== Health and Monitoring ==========
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get auth cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = await self.cache_service.stats()
        
        # Add auth-specific stats
        stats['auth_cache'] = {
            'default_ttl': self._default_ttl,
            'permissions_ttl': self._permissions_ttl,
            'roles_ttl': self._roles_ttl,
            'user_data_ttl': self._user_data_ttl
        }
        
        return stats