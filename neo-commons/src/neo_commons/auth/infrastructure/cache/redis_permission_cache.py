"""
Redis cache implementation for permission and authorization data.

Provides high-performance caching with tenant isolation and automatic invalidation.
"""
import json
from typing import Optional, List, Dict, Any
import redis.asyncio as redis
from loguru import logger

from ...domain.entities.permission import Permission
from ...domain.entities.role import Role
from ...domain.protocols.cache_protocols import PermissionCacheProtocol


class RedisPermissionCache(PermissionCacheProtocol):
    """
    Redis implementation of permission cache for sub-millisecond performance.
    
    Features:
    - Tenant isolation with key prefixing
    - Automatic TTL management
    - JSON serialization for complex objects
    - Batch operations for efficiency
    """

    def __init__(self, redis_client: redis.Redis, key_prefix: str = "neo_auth"):
        self._redis = redis_client
        self._key_prefix = key_prefix

    async def get_permission_check(self, cache_key: str) -> Optional[bool]:
        """Get cached permission check result."""
        try:
            full_key = f"{self._key_prefix}:perm_check:{cache_key}"
            result = await self._redis.get(full_key)
            if result is not None:
                return result.decode() == "true"
            return None
        except Exception as e:
            logger.warning(f"Failed to get permission check from cache: {e}")
            return None

    async def set_permission_check(
        self,
        cache_key: str,
        result: bool,
        ttl: int = 300
    ) -> None:
        """Cache permission check result."""
        try:
            full_key = f"{self._key_prefix}:perm_check:{cache_key}"
            await self._redis.setex(full_key, ttl, "true" if result else "false")
        except Exception as e:
            logger.warning(f"Failed to cache permission check: {e}")

    async def invalidate_permission_check(self, cache_key: str) -> None:
        """Invalidate cached permission check."""
        try:
            full_key = f"{self._key_prefix}:perm_check:{cache_key}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate permission check: {e}")

    async def get_user_permissions(self, cache_key: str) -> Optional[List[str]]:
        """Get cached user permissions."""
        try:
            full_key = f"{self._key_prefix}:user_perms:{cache_key}"
            result = await self._redis.get(full_key)
            if result is not None:
                return json.loads(result.decode())
            return None
        except Exception as e:
            logger.warning(f"Failed to get user permissions from cache: {e}")
            return None

    async def set_user_permissions(
        self,
        cache_key: str,
        permissions: List[str],
        ttl: int = 300
    ) -> None:
        """Cache user permissions."""
        try:
            full_key = f"{self._key_prefix}:user_perms:{cache_key}"
            data = json.dumps(permissions)
            await self._redis.setex(full_key, ttl, data)
        except Exception as e:
            logger.warning(f"Failed to cache user permissions: {e}")

    async def invalidate_user_permissions(self, cache_key: str) -> None:
        """Invalidate cached user permissions."""
        try:
            full_key = f"{self._key_prefix}:user_perms:{cache_key}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate user permissions: {e}")

    async def get_user_roles(self, cache_key: str) -> Optional[List[Role]]:
        """Get cached user roles."""
        try:
            full_key = f"{self._key_prefix}:user_roles:{cache_key}"
            result = await self._redis.get(full_key)
            if result is not None:
                data = json.loads(result.decode())
                return [self._deserialize_role(role_data) for role_data in data]
            return None
        except Exception as e:
            logger.warning(f"Failed to get user roles from cache: {e}")
            return None

    async def set_user_roles(
        self,
        cache_key: str,
        roles: List[Role],
        ttl: int = 300
    ) -> None:
        """Cache user roles."""
        try:
            full_key = f"{self._key_prefix}:user_roles:{cache_key}"
            data = json.dumps([self._serialize_role(role) for role in roles])
            await self._redis.setex(full_key, ttl, data)
        except Exception as e:
            logger.warning(f"Failed to cache user roles: {e}")

    async def invalidate_user_roles(self, cache_key: str) -> None:
        """Invalidate cached user roles."""
        try:
            full_key = f"{self._key_prefix}:user_roles:{cache_key}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate user roles: {e}")

    async def get_resource_access(self, cache_key: str) -> Optional[bool]:
        """Get cached resource access result."""
        try:
            full_key = f"{self._key_prefix}:resource_access:{cache_key}"
            result = await self._redis.get(full_key)
            if result is not None:
                return result.decode() == "true"
            return None
        except Exception as e:
            logger.warning(f"Failed to get resource access from cache: {e}")
            return None

    async def set_resource_access(
        self,
        cache_key: str,
        has_access: bool,
        ttl: int = 300
    ) -> None:
        """Cache resource access result."""
        try:
            full_key = f"{self._key_prefix}:resource_access:{cache_key}"
            await self._redis.setex(full_key, ttl, "true" if has_access else "false")
        except Exception as e:
            logger.warning(f"Failed to cache resource access: {e}")

    async def invalidate_resource_access(self, cache_key: str) -> None:
        """Invalidate cached resource access."""
        try:
            full_key = f"{self._key_prefix}:resource_access:{cache_key}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate resource access: {e}")

    async def invalidate_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """Invalidate all cache entries for a user."""
        try:
            tenant_part = f"{tenant_id}:" if tenant_id else "platform:"
            pattern = f"{self._key_prefix}:*:{tenant_part}{user_id}*"
            
            # Find and delete matching keys
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self._redis.delete(*keys)
                logger.debug(
                    f"Invalidated {len(keys)} cache entries for user {user_id}",
                    extra={
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "invalidated_count": len(keys)
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to invalidate user cache: {e}")

    async def invalidate_tenant_cache(self, tenant_id: str) -> None:
        """Invalidate all cache entries for a tenant."""
        try:
            pattern = f"{self._key_prefix}:*:{tenant_id}:*"
            
            # Find and delete matching keys
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self._redis.delete(*keys)
                logger.info(
                    f"Invalidated {len(keys)} cache entries for tenant {tenant_id}",
                    extra={
                        "tenant_id": tenant_id,
                        "invalidated_count": len(keys)
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to invalidate tenant cache: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = await self._redis.info("memory")
            
            # Count keys by type
            patterns = {
                "permission_checks": f"{self._key_prefix}:perm_check:*",
                "user_permissions": f"{self._key_prefix}:user_perms:*",
                "user_roles": f"{self._key_prefix}:user_roles:*",
                "resource_access": f"{self._key_prefix}:resource_access:*"
            }
            
            key_counts = {}
            for cache_type, pattern in patterns.items():
                count = 0
                async for _ in self._redis.scan_iter(match=pattern):
                    count += 1
                key_counts[cache_type] = count
            
            return {
                "memory_usage": info.get("used_memory_human", "Unknown"),
                "memory_peak": info.get("used_memory_peak_human", "Unknown"),
                "key_counts": key_counts,
                "total_keys": sum(key_counts.values())
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"error": str(e)}

    def _serialize_role(self, role: Role) -> Dict[str, Any]:
        """Serialize role to JSON-compatible format."""
        return {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "role_level": role.role_level.value,
            "tenant_id": role.tenant_id,
            "permissions": [
                {
                    "id": perm.id,
                    "code": perm.code,
                    "resource": perm.resource,
                    "action": perm.action,
                    "scope_level": perm.scope_level.value
                }
                for perm in (role.permissions or [])
            ]
        }

    def _deserialize_role(self, data: Dict[str, Any]) -> Role:
        """Deserialize role from JSON format."""
        from ...domain.entities.role import RoleLevel
        from ...domain.entities.permission import PermissionScope
        
        permissions = []
        for perm_data in data.get("permissions", []):
            permission = Permission(
                id=perm_data["id"],
                code=perm_data["code"],
                resource=perm_data["resource"],
                action=perm_data["action"],
                scope_level=PermissionScope(perm_data["scope_level"])
            )
            permissions.append(permission)
        
        return Role(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            description=data["description"],
            role_level=RoleLevel(data["role_level"]),
            tenant_id=data["tenant_id"],
            permissions=permissions
        )