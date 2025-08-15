"""
Access control service for fine-grained authorization decisions.

Provides business logic for access control entries, resource-level permissions,
and complex authorization scenarios.
"""
from typing import List, Optional, Dict, Any
from loguru import logger

from ...domain.entities.access_control import AccessControlEntry, AccessLevel
from ...domain.value_objects.user_context import UserContext
from ...domain.value_objects.tenant_context import TenantContext
from ...domain.value_objects.permission_check import PermissionResult
from ...domain.protocols.repository_protocols import AccessControlRepositoryProtocol
from ...domain.protocols.cache_protocols import AuthCacheProtocol
from ...domain.protocols.service_protocols import AccessControlServiceProtocol
from .access_control_utils import AccessControlUtils


class AccessControlService(AccessControlServiceProtocol):
    """
    Service for fine-grained access control management.
    
    Handles resource-level permissions, access control entries,
    and complex authorization scenarios with caching.
    """

    def __init__(
        self,
        access_control_repository: AccessControlRepositoryProtocol,
        cache: AuthCacheProtocol
    ):
        self._repository = access_control_repository
        self._cache = cache
        self._utils = AccessControlUtils()

    async def check_resource_access(
        self,
        user_context: UserContext,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """Check if user has specific access level to a resource."""
        # Validate parameters
        if not self._utils.validate_resource_access_params(resource_type, resource_id, access_level):
            return PermissionResult(
                granted=False,
                permission=f"{resource_type}:{resource_id}:{access_level.value}",
                user_id=user_context.user_id,
                tenant_id=self._utils.get_tenant_context_id(tenant_context),
                from_cache=False,
                metadata={"error": "Invalid parameters"}
            )

        # Build cache key
        cache_key = self._utils.build_access_cache_key(
            user_context.user_id,
            resource_type,
            resource_id,
            access_level,
            self._utils.get_tenant_context_id(tenant_context)
        )
        
        # Try cache first
        cached_result = await self._cache.get_resource_access(cache_key)
        if cached_result is not None:
            return self._create_permission_result(
                cached_result, user_context, resource_type, resource_id, 
                access_level, tenant_context, from_cache=True
            )

        # Check access in database
        has_access = await self._repository.check_resource_access(
            user_id=user_context.user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            access_level=access_level,
            tenant_id=self._utils.get_tenant_context_id(tenant_context)
        )

        # Cache the result
        await self._cache.set_resource_access(cache_key, has_access, ttl=300)

        return self._create_permission_result(
            has_access, user_context, resource_type, resource_id,
            access_level, tenant_context, from_cache=False
        )

    async def grant_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        granted_by: UserContext,
        tenant_context: Optional[TenantContext] = None,
        expiry_date: Optional[str] = None
    ) -> AccessControlEntry:
        """Grant user access to a specific resource."""
        # Create access control entry
        ace = await self._repository.create_access_control_entry(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            access_level=access_level,
            granted_by_user_id=granted_by.user_id,
            tenant_id=self._utils.get_tenant_context_id(tenant_context),
            expiry_date=expiry_date
        )

        # Invalidate relevant cache entries
        await self._invalidate_user_resource_cache(
            user_id, resource_type, resource_id, tenant_context
        )

        logger.info(
            f"Resource access granted: {resource_type}:{resource_id} to user {user_id}",
            extra={
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "access_level": access_level.value,
                "granted_by": granted_by.user_id,
                "tenant_id": self._utils.get_tenant_context_id(tenant_context),
                "ace_id": ace.id
            }
        )

        return ace

    async def revoke_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: Optional[AccessLevel],
        revoked_by: UserContext,
        tenant_context: Optional[TenantContext] = None
    ) -> bool:
        """Revoke user access to a specific resource."""
        success = await self._repository.revoke_resource_access(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            access_level=access_level,
            revoked_by_user_id=revoked_by.user_id,
            tenant_id=self._utils.get_tenant_context_id(tenant_context)
        )

        if success:
            # Invalidate relevant cache entries
            await self._invalidate_user_resource_cache(
                user_id, resource_type, resource_id, tenant_context
            )

            logger.info(
                f"Resource access revoked: {resource_type}:{resource_id} from user {user_id}",
                extra={
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "access_level": access_level.value if access_level else "ALL",
                    "revoked_by": revoked_by.user_id,
                    "tenant_id": self._utils.get_tenant_context_id(tenant_context)
                }
            )

        return success

    async def get_user_resources(
        self,
        user_context: UserContext,
        resource_type: str,
        access_level: Optional[AccessLevel] = None,
        tenant_context: Optional[TenantContext] = None
    ) -> List[str]:
        """Get all resources a user has access to."""
        return await self._repository.get_user_resources(
            user_id=user_context.user_id,
            resource_type=resource_type,
            access_level=access_level,
            tenant_id=self._utils.get_tenant_context_id(tenant_context)
        )

    async def get_resource_users(
        self,
        resource_type: str,
        resource_id: str,
        access_level: Optional[AccessLevel] = None,
        tenant_context: Optional[TenantContext] = None
    ) -> List[Dict[str, Any]]:
        """Get all users who have access to a resource."""
        return await self._repository.get_resource_users(
            resource_type=resource_type,
            resource_id=resource_id,
            access_level=access_level,
            tenant_id=self._utils.get_tenant_context_id(tenant_context)
        )

    async def check_ownership(
        self,
        user_context: UserContext,
        resource_type: str,
        resource_id: str,
        tenant_context: Optional[TenantContext] = None
    ) -> bool:
        """Check if user owns a resource (has OWNER access level)."""
        result = await self.check_resource_access(
            user_context,
            resource_type,
            resource_id,
            AccessLevel.OWNER,
            tenant_context
        )
        return result.granted

    async def transfer_ownership(
        self,
        resource_type: str,
        resource_id: str,
        from_user_id: str,
        to_user_id: str,
        transferred_by: UserContext,
        tenant_context: Optional[TenantContext] = None
    ) -> bool:
        """Transfer ownership of a resource from one user to another."""
        # Verify that the transferrer has appropriate permissions
        if not self._utils.can_perform_admin_operations(transferred_by):
            logger.warning(
                f"Unauthorized ownership transfer attempt by {transferred_by.user_id}",
                extra={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "from_user_id": from_user_id,
                    "to_user_id": to_user_id,
                    "transferred_by": transferred_by.user_id
                }
            )
            return False

        success = await self._repository.transfer_ownership(
            resource_type=resource_type,
            resource_id=resource_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            transferred_by_user_id=transferred_by.user_id,
            tenant_id=self._utils.get_tenant_context_id(tenant_context)
        )

        if success:
            # Invalidate cache for both users
            await self._invalidate_user_resource_cache(
                from_user_id, resource_type, resource_id, tenant_context
            )
            await self._invalidate_user_resource_cache(
                to_user_id, resource_type, resource_id, tenant_context
            )

        return success

    def _create_permission_result(
        self,
        granted: bool,
        user_context: UserContext,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        tenant_context: Optional[TenantContext],
        from_cache: bool
    ) -> PermissionResult:
        """Create a standardized permission result."""
        return PermissionResult(
            granted=granted,
            permission=f"{resource_type}:{resource_id}:{access_level.value}",
            user_id=user_context.user_id,
            tenant_id=self._utils.get_tenant_context_id(tenant_context),
            from_cache=from_cache
        )

    async def _invalidate_user_resource_cache(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        tenant_context: Optional[TenantContext]
    ) -> None:
        """Invalidate all cache entries for a user-resource combination."""
        cache_patterns = self._utils.build_resource_cache_patterns(
            user_id,
            resource_type,
            resource_id,
            self._utils.get_tenant_context_id(tenant_context)
        )
        
        for pattern in cache_patterns:
            await self._cache.invalidate_resource_access(pattern)