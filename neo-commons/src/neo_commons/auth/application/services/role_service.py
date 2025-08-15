"""
Role service for managing user roles and role-based access control.

Provides business logic for role assignment, hierarchy management,
and role-based authorization decisions.
"""
from typing import List, Optional, Dict, Any
from loguru import logger

from ...domain.entities.role import Role, RoleLevel, RoleAssignment
from ...domain.value_objects.user_context import UserContext
from ...domain.value_objects.tenant_context import TenantContext
from ...domain.value_objects.permission_check import PermissionResult
from ...domain.protocols.repository_protocols import RoleRepositoryProtocol
from ...domain.protocols.cache_protocols import AuthCacheProtocol
from ...domain.protocols.service_protocols import RoleServiceProtocol


class RoleService(RoleServiceProtocol):
    """
    Service for role management and role-based authorization.
    
    Handles role assignment, hierarchy, and role-based access control
    with intelligent caching for sub-millisecond performance.
    """

    def __init__(
        self,
        role_repository: RoleRepositoryProtocol,
        cache: AuthCacheProtocol
    ):
        self._repository = role_repository
        self._cache = cache

    async def get_user_roles(
        self,
        user_context: UserContext,
        tenant_context: Optional[TenantContext] = None
    ) -> List[Role]:
        """
        Get all roles assigned to a user.
        
        Args:
            user_context: User requesting roles
            tenant_context: Tenant scope for role lookup
            
        Returns:
            List of roles assigned to the user
        """
        # Build cache key
        cache_key = self._build_role_cache_key(
            user_context.user_id,
            tenant_context.tenant_id if tenant_context else None
        )
        
        # Try cache first
        cached_roles = await self._cache.get_user_roles(cache_key)
        if cached_roles is not None:
            logger.debug(
                f"Retrieved user roles from cache for user {user_context.user_id}",
                extra={
                    "user_id": user_context.user_id,
                    "tenant_id": tenant_context.tenant_id if tenant_context else None,
                    "role_count": len(cached_roles),
                    "from_cache": True
                }
            )
            return cached_roles

        # Fetch from database
        roles = await self._repository.get_user_roles(
            user_context.user_id,
            tenant_context.tenant_id if tenant_context else None
        )

        # Cache the results
        await self._cache.set_user_roles(cache_key, roles, ttl=300)

        logger.debug(
            f"Retrieved user roles from database for user {user_context.user_id}",
            extra={
                "user_id": user_context.user_id,
                "tenant_id": tenant_context.tenant_id if tenant_context else None,
                "role_count": len(roles),
                "from_cache": False
            }
        )

        return roles

    async def assign_role(
        self,
        user_id: str,
        role_code: str,
        assigned_by: UserContext,
        tenant_context: Optional[TenantContext] = None,
        expiry_date: Optional[str] = None
    ) -> RoleAssignment:
        """
        Assign a role to a user.
        
        Args:
            user_id: User to assign role to
            role_code: Role code to assign
            assigned_by: User performing the assignment
            tenant_context: Tenant scope for assignment
            expiry_date: Optional expiry date for role
            
        Returns:
            Created role assignment
        """
        # Create role assignment
        assignment = await self._repository.assign_role(
            user_id=user_id,
            role_code=role_code,
            assigned_by_user_id=assigned_by.user_id,
            tenant_id=tenant_context.tenant_id if tenant_context else None,
            expiry_date=expiry_date
        )

        # Invalidate user role cache
        cache_key = self._build_role_cache_key(
            user_id,
            tenant_context.tenant_id if tenant_context else None
        )
        await self._cache.invalidate_user_roles(cache_key)

        logger.info(
            f"Role {role_code} assigned to user {user_id} by {assigned_by.user_id}",
            extra={
                "user_id": user_id,
                "role_code": role_code,
                "assigned_by": assigned_by.user_id,
                "tenant_id": tenant_context.tenant_id if tenant_context else None,
                "assignment_id": assignment.id
            }
        )

        return assignment

    async def revoke_role(
        self,
        user_id: str,
        role_code: str,
        revoked_by: UserContext,
        tenant_context: Optional[TenantContext] = None
    ) -> bool:
        """
        Revoke a role from a user.
        
        Args:
            user_id: User to revoke role from
            role_code: Role code to revoke
            revoked_by: User performing the revocation
            tenant_context: Tenant scope for revocation
            
        Returns:
            True if role was revoked, False if not found
        """
        success = await self._repository.revoke_role(
            user_id=user_id,
            role_code=role_code,
            revoked_by_user_id=revoked_by.user_id,
            tenant_id=tenant_context.tenant_id if tenant_context else None
        )

        if success:
            # Invalidate user role cache
            cache_key = self._build_role_cache_key(
                user_id,
                tenant_context.tenant_id if tenant_context else None
            )
            await self._cache.invalidate_user_roles(cache_key)

            logger.info(
                f"Role {role_code} revoked from user {user_id} by {revoked_by.user_id}",
                extra={
                    "user_id": user_id,
                    "role_code": role_code,
                    "revoked_by": revoked_by.user_id,
                    "tenant_id": tenant_context.tenant_id if tenant_context else None
                }
            )

        return success

    async def has_role(
        self,
        user_context: UserContext,
        role_code: str,
        tenant_context: Optional[TenantContext] = None
    ) -> PermissionResult:
        """
        Check if user has a specific role.
        
        Args:
            user_context: User to check
            role_code: Role code to check for
            tenant_context: Tenant scope for check
            
        Returns:
            Permission result with role check outcome
        """
        # Get user roles
        user_roles = await self.get_user_roles(user_context, tenant_context)
        
        # Check if user has the role
        has_role = any(role.code == role_code for role in user_roles)
        
        return PermissionResult(
            granted=has_role,
            permission=f"role:{role_code}",
            user_id=user_context.user_id,
            tenant_id=tenant_context.tenant_id if tenant_context else None,
            from_cache=False,  # Role check is computed, not cached directly
            metadata={
                "role_code": role_code,
                "user_roles": [role.code for role in user_roles]
            }
        )

    async def get_effective_permissions(
        self,
        user_context: UserContext,
        tenant_context: Optional[TenantContext] = None
    ) -> List[str]:
        """
        Get all effective permissions for a user based on their roles.
        
        Args:
            user_context: User to get permissions for
            tenant_context: Tenant scope for permissions
            
        Returns:
            List of permission codes user has through roles
        """
        # Get user roles
        user_roles = await self.get_user_roles(user_context, tenant_context)
        
        # Collect all permissions from all roles
        all_permissions = set()
        for role in user_roles:
            if role.permissions:
                for permission in role.permissions:
                    all_permissions.add(permission.code)
        
        return list(all_permissions)

    async def get_role_hierarchy(
        self,
        role_code: str,
        tenant_context: Optional[TenantContext] = None
    ) -> List[Role]:
        """
        Get role hierarchy (role and all parent roles).
        
        Args:
            role_code: Role code to get hierarchy for
            tenant_context: Tenant scope for role lookup
            
        Returns:
            List of roles in hierarchy (including the role itself)
        """
        return await self._repository.get_role_hierarchy(
            role_code,
            tenant_context.tenant_id if tenant_context else None
        )

    async def can_assign_role(
        self,
        assigner: UserContext,
        role_code: str,
        tenant_context: Optional[TenantContext] = None
    ) -> bool:
        """
        Check if a user can assign a specific role.
        
        Args:
            assigner: User wanting to assign the role
            role_code: Role code to check assignment permission for
            tenant_context: Tenant scope for check
            
        Returns:
            True if user can assign the role
        """
        # Superadmin can assign any role
        if assigner.is_superadmin:
            return True
        
        # Get role details
        role = await self._repository.get_role_by_code(
            role_code,
            tenant_context.tenant_id if tenant_context else None
        )
        
        if not role:
            return False
        
        # Get assigner's roles
        assigner_roles = await self.get_user_roles(assigner, tenant_context)
        
        # Check if assigner has appropriate level to assign this role
        max_assigner_level = max(
            (role.role_level for role in assigner_roles),
            default=RoleLevel.MEMBER
        )
        
        # Can only assign roles at or below your level
        return max_assigner_level.value >= role.role_level.value

    def _build_role_cache_key(self, user_id: str, tenant_id: Optional[str]) -> str:
        """Build cache key for user roles."""
        if tenant_id:
            return f"user_roles:{tenant_id}:{user_id}"
        return f"user_roles:platform:{user_id}"