"""
Centralized user data service for consistent user information fetching.
This service is used by all user-related endpoints to avoid redundancy.
"""

from typing import Optional, Dict, Any, List
from loguru import logger

from src.common.cache.client import get_cache
from src.common.exceptions.base import NotFoundError
from src.common.utils import utc_now
from src.features.auth.repositories.auth_repository import AuthRepository
from src.features.auth.repositories.permission_repository import PermissionRepository
from ..repositories.user_repository import PlatformUserRepository


class UserDataService:
    """
    Centralized service for fetching complete user data.
    Used by /auth/me, /users/me, and /users/{id} endpoints.
    """
    
    def __init__(self):
        """Initialize the service."""
        self.user_repo = PlatformUserRepository()
        self.auth_repo = AuthRepository()
        self.permission_repo = PermissionRepository()
        self.cache = get_cache()
        
        # Cache configuration
        self.CACHE_KEY_COMPLETE_USER = "user:complete:{user_id}"
        self.CACHE_TTL = 300  # 5 minutes
    
    async def get_complete_user_data(
        self,
        user_id: str,
        include_permissions: bool = True,
        include_roles: bool = True,
        include_tenants: bool = True,
        include_onboarding: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get complete user data with all related information.
        
        This is the single source of truth for user data fetching.
        All user endpoints should use this method.
        
        Args:
            user_id: User ID to fetch
            include_permissions: Include user permissions
            include_roles: Include user roles
            include_tenants: Include tenant access
            include_onboarding: Include onboarding status
            use_cache: Use cached data if available
            
        Returns:
            Complete user data dictionary
        """
        # Check cache first
        if use_cache:
            cache_key = self.CACHE_KEY_COMPLETE_USER.format(user_id=user_id)
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for user {user_id}")
                return cached
        
        # Get base user data
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Build complete user data
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip() if (user.first_name or user.last_name) else user.display_name,
            "avatar_url": user.avatar_url,
            "phone": user.phone,
            "timezone": user.timezone or "UTC",
            "locale": user.locale or "en-US",
            "language": user.locale[:2] if user.locale else "en",  # Derive from locale
            "job_title": user.job_title,
            "company": user.company,
            "departments": user.departments or [],
            "is_active": user.is_active,
            "is_superadmin": user.is_superadmin,
            "external_auth_provider": user.external_auth_provider if isinstance(user.external_auth_provider, str) else (user.external_auth_provider.value if user.external_auth_provider else None),
            "external_user_id": user.external_user_id,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "metadata": user.metadata or {}
        }
        
        # Add onboarding information
        if include_onboarding:
            user_data["is_onboarding_completed"] = user.is_onboarding_completed
            user_data["profile_completion_percentage"] = await self._calculate_profile_completion(user_data)
            user_data["onboarding_steps"] = await self._get_onboarding_steps(user_id, user_data)
        
        # Add notification and UI preferences
        user_data["notification_preferences"] = user.notification_preferences or {}
        user_data["ui_preferences"] = user.ui_preferences or {}
        
        # Add roles if requested
        if include_roles:
            roles_data = await self._get_user_roles_formatted(user_id)
            user_data["roles"] = roles_data["platform_roles"]
            user_data["platform_roles"] = [r["name"] for r in roles_data["platform_roles"]]
            user_data["tenant_roles"] = roles_data["tenant_roles"]
        
        # Add permissions if requested
        if include_permissions:
            permissions = await self._get_user_permissions_formatted(user_id)
            user_data["permissions"] = permissions
        
        # Add tenant access if requested
        if include_tenants:
            tenant_access = await self._get_user_tenants_formatted(user_id)
            user_data["tenants"] = tenant_access
            user_data["tenant_count"] = len(tenant_access)
        
        # Cache the complete data
        if use_cache:
            await self.cache.set(cache_key, user_data, ttl=self.CACHE_TTL)
        
        return user_data
    
    async def _get_user_roles_formatted(self, user_id: str) -> Dict[str, Any]:
        """Get formatted user roles."""
        # Get all roles (platform and tenant)
        all_roles = await self.permission_repo.get_user_roles(user_id)
        
        formatted_platform_roles = []
        # Filter and format platform roles
        for role in all_roles:
            if role.get("level") == "platform" or not role.get("tenant_id"):
                formatted_platform_roles.append({
                    "id": role.get("role_id"),
                    "name": role.get("role_name", "unknown"),
                    "code": role.get("role_code", role.get("role_name", "unknown")),
                    "display_name": role.get("role_display_name"),
                    "level": role.get("role_level", "platform"),
                    "priority": role.get("role_priority", 999),
                    "config": role.get("role_config", {}),
                    "granted_at": role.get("granted_at").isoformat() if role.get("granted_at") else None,
                    "expires_at": role.get("expires_at").isoformat() if role.get("expires_at") else None
                })
        
        # Get tenant roles with better formatting
        tenant_roles = {}
        
        # Process tenant roles from the same all_roles list
        for role in all_roles:
            if role.get("level") == "tenant" and role.get("tenant_id"):
                tenant_id = str(role.get("tenant_id"))
                if tenant_id not in tenant_roles:
                    tenant_roles[tenant_id] = []
                tenant_roles[tenant_id].append({
                    "id": role.get("role_id"),
                    "name": role.get("role_name", "unknown"),
                    "code": role.get("role_code", role.get("role_name", "unknown")),
                    "team_id": role.get("team_id"),
                    "granted_at": role.get("granted_at").isoformat() if role.get("granted_at") else None
                })
        
        return {
            "platform_roles": formatted_platform_roles,
            "tenant_roles": tenant_roles
        }
    
    async def _get_user_permissions_formatted(self, user_id: str) -> List[Dict[str, Any]]:
        """Get formatted user permissions."""
        permissions = await self.permission_repo.get_user_permissions(user_id)
        
        formatted_permissions = []
        for perm in permissions:
            formatted_permissions.append({
                "code": perm.get("name", f"{perm.get('resource', 'unknown')}:{perm.get('action', 'unknown')}"),
                "resource": perm.get("resource"),
                "action": perm.get("action"),
                "scope_level": perm.get("scope_level"),
                "is_dangerous": perm.get("is_dangerous", False),
                "requires_mfa": perm.get("requires_mfa", False),
                "requires_approval": perm.get("requires_approval", False),
                "config": perm.get("permissions_config", {}),
                "source": perm.get("source_type"),
                "priority": perm.get("priority", 0)
            })
        
        return formatted_permissions
    
    async def _get_user_tenants_formatted(self, user_id: str) -> List[Dict[str, Any]]:
        """Get formatted user tenant access."""
        tenant_access = await self.auth_repo.get_user_tenant_access(user_id)
        
        formatted_tenants = []
        for access in tenant_access:
            formatted_tenants.append({
                "id": str(access.get("tenant_id")) if access.get("tenant_id") else None,
                "name": access.get("tenant_name"),
                "slug": access.get("tenant_slug"),
                "access_level": access.get("access_level"),
                "is_primary": access.get("is_primary", False),
                "joined_at": access.get("joined_at").isoformat() if access.get("joined_at") else None,
                "expires_at": access.get("expires_at").isoformat() if access.get("expires_at") else None
            })
        
        return formatted_tenants
    
    async def _calculate_profile_completion(self, user_data: Dict[str, Any]) -> int:
        """Calculate profile completion percentage."""
        # Define weights for each field
        field_weights = {
            'first_name': 10,
            'last_name': 10,
            'display_name': 5,
            'avatar_url': 10,
            'phone': 10,
            'job_title': 10,
            'company': 10,
            'departments': 10,
            'timezone': 5,
            'locale': 5,
            'notification_preferences': 10,
            'ui_preferences': 5
        }
        
        total_weight = sum(field_weights.values())
        completed_weight = 0
        
        # Check each field
        if user_data.get('first_name') and user_data['first_name'].strip():
            completed_weight += field_weights['first_name']
        if user_data.get('last_name') and user_data['last_name'].strip():
            completed_weight += field_weights['last_name']
        if user_data.get('display_name') and user_data['display_name'].strip():
            completed_weight += field_weights['display_name']
        if user_data.get('avatar_url'):
            completed_weight += field_weights['avatar_url']
        if user_data.get('phone'):
            completed_weight += field_weights['phone']
        if user_data.get('job_title'):
            completed_weight += field_weights['job_title']
        if user_data.get('company'):
            completed_weight += field_weights['company']
        if user_data.get('departments') and len(user_data['departments']) > 0:
            completed_weight += field_weights['departments']
        if user_data.get('timezone') and user_data['timezone'] != 'UTC':
            completed_weight += field_weights['timezone']
        if user_data.get('locale') and user_data['locale'] != 'en-US':
            completed_weight += field_weights['locale']
        if user_data.get('notification_preferences') and len(user_data['notification_preferences']) > 0:
            completed_weight += field_weights['notification_preferences']
        if user_data.get('ui_preferences') and len(user_data['ui_preferences']) > 0:
            completed_weight += field_weights['ui_preferences']
        
        return int((completed_weight / total_weight) * 100)
    
    async def _get_onboarding_steps(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, bool]:
        """Get onboarding steps status."""
        # Determine user type
        is_platform_admin = (
            user_data.get('is_superadmin') or 
            any(role in ['platform_admin', 'organization_owner', 'organization_admin'] 
                for role in user_data.get('platform_roles', []))
        )
        
        if is_platform_admin:
            # Platform admin onboarding
            return {
                "profile_completed": user_data.get('profile_completion_percentage', 0) >= 70,
                "organization_created": await self._has_organization(user_id),
                "first_tenant_created": user_data.get('tenant_count', 0) > 0,
                "billing_setup": False,  # TODO: Check billing status
                "security_configured": await self._has_security_configured(user_id)
            }
        else:
            # Tenant user onboarding
            return {
                "profile_completed": user_data.get('profile_completion_percentage', 0) >= 70,
                "tenant_joined": user_data.get('tenant_count', 0) > 0,
                "team_joined": await self._has_team_membership(user_id),
                "workspace_accessed": await self._has_accessed_workspace(user_id),
                "preferences_configured": self._has_preferences_configured(user_data)
            }
    
    async def _has_organization(self, user_id: str) -> bool:
        """Check if user has created or belongs to an organization."""
        # TODO: Implement when organization feature is ready
        return False
    
    async def _has_team_membership(self, user_id: str) -> bool:
        """Check if user belongs to any team."""
        # TODO: Implement when team feature is ready
        return False
    
    async def _has_accessed_workspace(self, user_id: str) -> bool:
        """Check if user has accessed their workspace."""
        # TODO: Check access logs or last activity
        return False
    
    def _has_preferences_configured(self, user_data: Dict[str, Any]) -> bool:
        """Check if user has configured their preferences."""
        return (
            user_data.get('notification_preferences') and 
            len(user_data['notification_preferences']) > 0 and
            user_data.get('ui_preferences') and 
            len(user_data['ui_preferences']) > 0
        )
    
    async def _has_security_configured(self, user_id: str) -> bool:
        """Check if user has configured security settings (2FA, etc)."""
        # TODO: Check security settings when implemented
        return False
    
    async def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cached data for a user."""
        cache_key = self.CACHE_KEY_COMPLETE_USER.format(user_id=user_id)
        await self.cache.delete(cache_key)
        logger.info(f"Invalidated cache for user {user_id}")