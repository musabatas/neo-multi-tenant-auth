"""
Permission service - Core permission checking business logic.

Handles sub-millisecond permission checks with intelligent caching.
"""
from typing import List, Optional, Dict, Any
from loguru import logger

from ...domain.entities.permission import Permission
from ...domain.value_objects.permission_check import PermissionCheck, PermissionResult, CheckType
from ...domain.value_objects.user_context import UserContext
from ...domain.value_objects.tenant_context import TenantContext
from ...domain.protocols.repository_protocols import PermissionRepositoryProtocol
from ...domain.protocols.cache_protocols import PermissionCacheProtocol
from ...domain.protocols.service_protocols import PermissionServiceProtocol


class PermissionService:
    """
    Permission service implementing sub-millisecond permission checks.
    
    Features:
    - Redis caching with tenant isolation
    - Batch permission checking
    - Wildcard permission resolution
    - Cache warming and invalidation
    """
    
    def __init__(
        self,
        permission_repository: PermissionRepositoryProtocol,
        cache: PermissionCacheProtocol
    ):
        self.repository = permission_repository
        self.cache = cache
        self.default_ttl = 300  # 5 minutes
    
    async def check_permission(
        self,
        user_context: UserContext,
        permission: str,
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """
        Check if user has a specific permission with caching.
        
        Target: <1ms from cache, <50ms from database.
        """
        check = PermissionCheck.single(
            user_id=user_context.user_id,
            permission=permission,
            tenant_id=tenant_context.tenant_id if tenant_context else None
        )
        
        # Try cache first
        cached_result = await self.cache.get_cached_permission_check(
            user_context.user_id,
            permission,
            tenant_context.tenant_id if tenant_context else None
        )
        
        if cached_result is not None:
            return PermissionResult(
                check=check,
                granted=cached_result,
                from_cache=True,
                decision_reason="Cached permission check result"
            )
        
        # Check database
        has_permission = await self.repository.check_permission(
            user_context.user_id,
            permission,
            tenant_context.tenant_id if tenant_context else None
        )
        
        # Cache result
        await self.cache.cache_permission_check_result(
            user_context.user_id,
            permission,
            has_permission,
            tenant_context.tenant_id if tenant_context else None,
            self.default_ttl
        )
        
        result = PermissionResult.granted(
            check=check,
            decision_reason="Database permission check"
        ) if has_permission else PermissionResult.denied(
            check=check,
            reason="Permission not found in database"
        )
        
        return result
    
    async def check_permissions_batch(
        self,
        checks: List[PermissionCheck]
    ) -> List[PermissionResult]:
        """
        Check multiple permissions in batch for performance.
        
        Optimizes by grouping cache lookups and database queries.
        """
        results = []
        uncached_checks = []
        
        # First pass: check cache
        for check in checks:
            cached_result = await self.cache.get_cached_permission_check(
                check.user_id,
                check.primary_permission,
                check.tenant_id
            )
            
            if cached_result is not None:
                results.append(PermissionResult(
                    check=check,
                    granted=cached_result,
                    from_cache=True,
                    decision_reason="Cached batch permission check"
                ))
            else:
                uncached_checks.append(check)
                results.append(None)  # Placeholder
        
        # Second pass: batch database checks
        if uncached_checks:
            db_results = await self._batch_database_checks(uncached_checks)
            
            # Merge results and cache
            uncached_index = 0
            for i, result in enumerate(results):
                if result is None:  # Placeholder for uncached
                    check = checks[i]
                    db_result = db_results[uncached_index]
                    
                    # Cache result
                    await self.cache.cache_permission_check_result(
                        check.user_id,
                        check.primary_permission,
                        db_result,
                        check.tenant_id,
                        self.default_ttl
                    )
                    
                    results[i] = PermissionResult.granted(
                        check=check,
                        decision_reason="Batch database permission check"
                    ) if db_result else PermissionResult.denied(
                        check=check,
                        reason="Permission not found in batch database check"
                    )
                    
                    uncached_index += 1
        
        return results
    
    async def has_any_permission(
        self,
        user_context: UserContext,
        permissions: List[str],
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """Check if user has any of the specified permissions."""
        check = PermissionCheck.any_of(
            user_id=user_context.user_id,
            permissions=permissions,
            tenant_id=tenant_context.tenant_id if tenant_context else None
        )
        
        # Check each permission until one is found
        for permission in permissions:
            result = await self.check_permission(user_context, permission, tenant_context)
            if result.granted:
                return PermissionResult.granted(
                    check=check,
                    matched_permissions=[permission],
                    decision_reason=f"User has permission: {permission}"
                )
        
        return PermissionResult.denied(
            check=check,
            reason="User has none of the specified permissions"
        )
    
    async def has_all_permissions(
        self,
        user_context: UserContext,
        permissions: List[str],
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """Check if user has all of the specified permissions."""
        check = PermissionCheck.all_of(
            user_id=user_context.user_id,
            permissions=permissions,
            tenant_id=tenant_context.tenant_id if tenant_context else None
        )
        
        matched_permissions = []
        
        # Check all permissions
        for permission in permissions:
            result = await self.check_permission(user_context, permission, tenant_context)
            if result.granted:
                matched_permissions.append(permission)
            else:
                return PermissionResult.denied(
                    check=check,
                    reason=f"User missing permission: {permission}"
                )
        
        return PermissionResult.granted(
            check=check,
            matched_permissions=matched_permissions,
            decision_reason="User has all specified permissions"
        )
    
    async def get_user_permissions(
        self,
        user_context: UserContext,
        tenant_context: Optional[TenantContext] = None,
        use_cache: bool = True
    ) -> List[Permission]:
        """Get all permissions for a user with caching."""
        if use_cache:
            cached_permissions = await self.cache.get_cached_user_permissions(
                user_context.user_id,
                tenant_context.tenant_id if tenant_context else None
            )
            if cached_permissions is not None:
                return cached_permissions
        
        # Load from database
        permissions = await self.repository.get_user_permissions(
            user_context.user_id,
            tenant_context.tenant_id if tenant_context else None
        )
        
        # Cache result
        if use_cache:
            await self.cache.cache_user_permissions(
                user_context.user_id,
                permissions,
                tenant_context.tenant_id if tenant_context else None,
                self.default_ttl
            )
        
        return permissions
    
    async def get_effective_permissions(
        self,
        user_context: UserContext,
        resource: str,
        tenant_context: Optional[TenantContext] = None
    ) -> List[Permission]:
        """Get effective permissions for a user on a specific resource."""
        all_permissions = await self.get_user_permissions(user_context, tenant_context)
        
        # Filter to resource-specific permissions
        effective_permissions = []
        for permission in all_permissions:
            if permission.resource == resource or permission.is_wildcard:
                effective_permissions.append(permission)
        
        return effective_permissions
    
    async def invalidate_user_permission_cache(
        self, 
        user_id: str, 
        tenant_id: Optional[str] = None
    ) -> None:
        """Invalidate cached permissions for a user."""
        await self.cache.invalidate_user_cache(user_id, tenant_id)
        logger.info(f"Invalidated permission cache for user {user_id}")
    
    async def warm_user_cache(
        self,
        user_context: UserContext,
        tenant_context: Optional[TenantContext] = None
    ) -> None:
        """Pre-warm cache with user's permissions for faster access."""
        await self.cache.warm_user_cache(
            user_context.user_id,
            tenant_context.tenant_id if tenant_context else None
        )
        logger.info(f"Warmed permission cache for user {user_context.user_id}")
    
    async def _batch_database_checks(self, checks: List[PermissionCheck]) -> List[bool]:
        """Perform batch database permission checks."""
        results = []
        
        # Group checks by user and tenant for optimization
        for check in checks:
            has_permission = await self.repository.check_permission(
                check.user_id,
                check.primary_permission,
                check.tenant_id
            )
            results.append(has_permission)
        
        return results