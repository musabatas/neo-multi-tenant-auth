"""
Platform Users service for business logic and Keycloak synchronization.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from loguru import logger

from src.common.exceptions.base import (
    NotFoundError, 
    ValidationError, 
    ConflictError,
    UnauthorizedError
)
from src.common.models.base import PaginationParams
from src.common.services.base import BaseService
from src.common.cache.client import get_cache
from src.common.utils import utc_now
from neo_commons.auth import create_auth_service

from ..models.domain import (
    PlatformUser, AuthProvider
)
from ..models.request import (
    PlatformUserCreate, PlatformUserUpdate, PlatformUserFilter,
    RoleAssignmentRequest, PermissionGrantRequest, UserStatusUpdate,
    UserPreferencesUpdate, BulkUserOperation, UserSearchRequest
)
from ..models.response import (
    PlatformUserResponse, PlatformUserListItem, PlatformUserListResponse,
    PlatformUserListSummary, UserRoleAssignmentResponse,
    UserPermissionGrantResponse, BulkOperationResponse, UserSearchResponse
)
from ..repositories.user_repository import PlatformUserRepository


class PlatformUserService(BaseService):
    """Service for platform user business logic."""
    
    def __init__(self):
        """Initialize the service."""
        super().__init__()
        self.repository = PlatformUserRepository()
        self.cache = get_cache()
        self.auth_service = create_auth_service()
        
        # Cache key patterns
        self.CACHE_KEY_USER = "platform_user:{user_id}"
        self.CACHE_KEY_USER_EMAIL = "platform_user:email:{email}"
        self.CACHE_KEY_USER_USERNAME = "platform_user:username:{username}"
        self.CACHE_KEY_USER_PERMISSIONS = "platform_user_permissions:{user_id}"
        self.CACHE_KEY_USER_ROLES = "platform_user_roles:{user_id}"
        self.CACHE_TTL = 600  # 10 minutes
    
    async def get_user(self, user_id: str) -> PlatformUserResponse:
        """Get a platform user by ID."""
        # Use centralized UserDataService
        from .user_data_service import UserDataService
        user_data_service = UserDataService()
        
        # Get complete user data
        user_data = await user_data_service.get_complete_user_data(
            user_id=user_id,
            include_permissions=True,
            include_roles=True,
            include_tenants=True,
            include_onboarding=True,
            use_cache=True
        )
        
        # Convert to PlatformUserResponse
        # Map the data to match PlatformUserResponse model
        response_data = {
            "id": user_data["id"],
            "email": user_data["email"],
            "username": user_data["username"],
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "display_name": user_data.get("display_name"),
            "full_name": user_data.get("full_name"),
            "avatar_url": user_data.get("avatar_url"),
            "phone": user_data.get("phone"),
            "timezone": user_data.get("timezone", "UTC"),
            "locale": user_data.get("locale", "en-US"),
            "job_title": user_data.get("job_title"),
            "company": user_data.get("company"),
            "departments": user_data.get("departments", []),
            "notification_preferences": user_data.get("notification_preferences", {}),
            "ui_preferences": user_data.get("ui_preferences", {}),
            "is_active": user_data.get("is_active", True),
            "is_superadmin": user_data.get("is_superadmin", False),
            "is_onboarding_completed": user_data.get("is_onboarding_completed", False),
            "profile_completion_percentage": user_data.get("profile_completion_percentage", 0),
            "external_auth_provider": user_data.get("external_auth_provider"),
            "external_user_id": user_data.get("external_user_id"),
            "last_login_at": user_data.get("last_login_at"),
            "created_at": user_data.get("created_at"),
            "updated_at": user_data.get("updated_at"),
            "platform_roles": user_data.get("platform_roles", []),
            "tenant_roles": user_data.get("tenant_roles", {}),
            "permissions": [p["code"] for p in user_data.get("permissions", [])],
            "tenant_count": user_data.get("tenant_count", 0)
        }
        
        return PlatformUserResponse(**response_data)
    
    async def get_user_by_email(self, email: str) -> PlatformUserResponse:
        """Get a platform user by email."""
        # Try cache first
        cache_key = self.CACHE_KEY_USER_EMAIL.format(email=email.lower())
        cached = await self.cache.get(cache_key)
        if cached:
            return PlatformUserResponse(**cached)
        
        user = await self.repository.get_by_email(email)
        response = await self.get_user(str(user.id))
        
        # Cache by email too
        await self.cache.set(cache_key, response.model_dump(), ttl=self.CACHE_TTL)
        
        return response
    
    async def get_user_by_username(self, username: str) -> PlatformUserResponse:
        """Get a platform user by username."""
        # Try cache first
        cache_key = self.CACHE_KEY_USER_USERNAME.format(username=username.lower())
        cached = await self.cache.get(cache_key)
        if cached:
            return PlatformUserResponse(**cached)
        
        user = await self.repository.get_by_username(username)
        response = await self.get_user(str(user.id))
        
        # Cache by username too
        await self.cache.set(cache_key, response.model_dump(), ttl=self.CACHE_TTL)
        
        return response
    
    async def list_users(
        self,
        filters: Optional[PlatformUserFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PlatformUserListResponse:
        """List platform users with optional filters and pagination."""
        if pagination is None:
            pagination = PaginationParams(page=1, page_size=20)
        
        # Validate pagination
        self.validate_pagination_params(pagination.page, pagination.page_size)
        
        # Get users from repository
        offset = (pagination.page - 1) * pagination.page_size
        users, total_count = await self.repository.list(
            filters=filters,
            limit=pagination.page_size,
            offset=offset
        )
        
        # Build list items with summary data
        items = []
        for user in users:
            platform_roles = await self._get_user_role_codes(str(user.id))
            tenant_count = await self.repository.get_user_tenant_count(str(user.id))
            
            item = PlatformUserListItem(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                display_name=user.display_name,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                external_auth_provider=user.external_auth_provider,
                is_active=user.is_active,
                is_superadmin=user.is_superadmin,
                last_login_at=user.last_login_at,
                company=user.company,
                job_title=user.job_title,
                created_at=user.created_at,
                role_count=len(platform_roles),
                tenant_count=tenant_count,
                permission_count=0  # Could be expensive to calculate here
            )
            items.append(item)
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page, 
            pagination.page_size, 
            total_count
        )
        
        return PlatformUserListResponse(
            items=items,
            pagination=pagination_meta.model_dump()
        )
    
    async def create_user(
        self,
        user_data: PlatformUserCreate,
        created_by: Optional[str] = None
    ) -> PlatformUserResponse:
        """Create a new platform user."""
        # Validate user data
        await self._validate_user_create(user_data)
        
        # Create user in database
        user = await self.repository.create(user_data)
        
        logger.info(f"Created platform user {user.id} ({user.email}) by {created_by or 'system'}")
        
        # Return full response
        return await self.get_user(str(user.id))
    
    async def update_user(
        self,
        user_id: str,
        update_data: PlatformUserUpdate
    ) -> PlatformUserResponse:
        """Update a platform user."""
        # Update user
        user = await self.repository.update(user_id, update_data)
        
        # Invalidate cache
        await self._invalidate_user_cache(user_id, user.email, user.username)
        
        logger.info(f"Updated platform user {user_id}")
        
        return await self.get_user(user_id)
    
    async def update_user_status(
        self,
        user_id: str,
        status_update: UserStatusUpdate
    ) -> PlatformUserResponse:
        """Update user active status."""
        update_data = PlatformUserUpdate(is_active=status_update.is_active)
        result = await self.update_user(user_id, update_data)
        
        logger.info(
            f"Updated user {user_id} status to {'active' if status_update.is_active else 'inactive'}"
            f"{f' - {status_update.reason}' if status_update.reason else ''}"
        )
        
        return result
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences_update: UserPreferencesUpdate
    ) -> PlatformUserResponse:
        """Update user preferences."""
        update_data = PlatformUserUpdate(
            timezone=preferences_update.timezone,
            locale=preferences_update.locale,
            notification_preferences=preferences_update.notification_preferences,
            ui_preferences=preferences_update.ui_preferences
        )
        
        return await self.update_user(user_id, update_data)
    
    async def delete_user(self, user_id: str) -> None:
        """Delete (deactivate) a platform user."""
        # Get user first for cache invalidation
        user = await self.repository.get_by_id(user_id)
        
        # Soft delete
        await self.repository.delete(user_id)
        
        # Invalidate cache
        await self._invalidate_user_cache(user_id, user.email, user.username)
        
        logger.info(f"Soft deleted platform user {user_id}")
    
    async def sync_user_from_keycloak(
        self,
        token: str,
        provider: AuthProvider = AuthProvider.KEYCLOAK,
        create_if_not_exists: bool = True
    ) -> PlatformUserResponse:
        """Sync user data from Keycloak token."""
        try:
            # Validate token and extract user data
            token_data = await self.auth_service.validate_token(token)
            
            external_user_id = token_data.get('sub')
            if not external_user_id:
                raise UnauthorizedError('Token missing user ID')
            
            # Try to find existing user
            existing_user = await self.repository.get_by_external_id(provider, external_user_id)
            
            if existing_user:
                # Update last login
                await self.repository.update_last_login(str(existing_user.id))
                
                # Update user data from token if needed
                user_update = self._extract_user_update_from_token(token_data)
                if any(v is not None for v in user_update.model_dump(exclude_unset=True).values()):
                    await self.repository.update(str(existing_user.id), user_update)
                
                return await self.get_user(str(existing_user.id))
            
            elif create_if_not_exists:
                # Create new user from token data
                user_create = self._extract_user_create_from_token(token_data, provider)
                return await self.create_user(user_create)
            
            else:
                raise NotFoundError(
                    resource="PlatformUser",
                    identifier=f"{provider.value}:{external_user_id}"
                )
        
        except Exception as e:
            logger.error(f"Failed to sync user from Keycloak: {e}")
            raise UnauthorizedError("Invalid token or user sync failed")
    
    async def search_users(self, search_request: UserSearchRequest) -> UserSearchResponse:
        """Advanced user search."""
        # For now, use the standard list with search filter
        search_filter = PlatformUserFilter(search=search_request.query)
        if search_request.filters:
            # Merge additional filters
            for field, value in search_request.filters.model_dump(exclude_unset=True).items():
                setattr(search_filter, field, value)
        
        # Use standard pagination
        pagination = PaginationParams(page=1, page_size=50)
        result = await self.list_users(search_filter, pagination)
        
        return UserSearchResponse(
            query=search_request.query,
            total_results=result.pagination['total_items'],
            results=result.items,
            pagination=result.pagination
        )
    
    async def bulk_operation(
        self,
        bulk_request: BulkUserOperation,
        performed_by: Optional[str] = None
    ) -> BulkOperationResponse:
        """Perform bulk operations on users."""
        successful = []
        failed = []
        errors = []
        
        for user_id in bulk_request.user_ids:
            try:
                if bulk_request.operation == 'activate':
                    await self.update_user_status(
                        str(user_id), 
                        UserStatusUpdate(is_active=True, reason=bulk_request.reason)
                    )
                    successful.append(user_id)
                
                elif bulk_request.operation == 'deactivate':
                    await self.update_user_status(
                        str(user_id), 
                        UserStatusUpdate(is_active=False, reason=bulk_request.reason)
                    )
                    successful.append(user_id)
                
                elif bulk_request.operation == 'delete':
                    await self.delete_user(str(user_id))
                    successful.append(user_id)
                
                else:
                    failed.append(user_id)
                    errors.append({
                        'user_id': str(user_id),
                        'error': f'Unknown operation: {bulk_request.operation}'
                    })
            
            except Exception as e:
                failed.append(user_id)
                errors.append({
                    'user_id': str(user_id),
                    'error': str(e)
                })
        
        logger.info(
            f"Bulk {bulk_request.operation} completed by {performed_by or 'system'}: "
            f"{len(successful)} successful, {len(failed)} failed"
        )
        
        return BulkOperationResponse(
            operation=bulk_request.operation,
            total_requested=len(bulk_request.user_ids),
            successful=len(successful),
            failed=len(failed),
            errors=errors,
            successful_ids=successful,
            failed_ids=failed
        )
    
    async def _get_user_role_codes(self, user_id: str) -> List[str]:
        """Get platform role codes for user."""
        # Try cache first
        cache_key = self.CACHE_KEY_USER_ROLES.format(user_id=user_id)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        roles = await self.repository.get_user_platform_roles(user_id)
        role_codes = [role.role.code if role.role else "unknown" for role in roles]
        
        # Cache for shorter time since roles change more frequently
        await self.cache.set(cache_key, role_codes, ttl=300)  # 5 minutes
        
        return role_codes
    
    async def _get_user_tenant_roles_summary(self, user_id: str) -> Dict[str, List[str]]:
        """Get tenant roles summary for user."""
        tenant_roles = await self.repository.get_user_tenant_roles(user_id)
        
        summary = {}
        for role in tenant_roles:
            tenant_id = str(role.tenant_id)
            if tenant_id not in summary:
                summary[tenant_id] = []
            summary[tenant_id].append(role.role.code if role.role else "unknown")
        
        return summary
    
    async def _validate_user_create(self, user_data: PlatformUserCreate) -> None:
        """Validate user creation data."""
        errors = []
        
        # Additional business validation could go here
        # For now, the model validation handles most cases
        
        if errors:
            raise ValidationError(
                message="User validation failed",
                errors=errors
            )
    
    def _extract_user_create_from_token(
        self, 
        token_data: Dict[str, Any], 
        provider: AuthProvider
    ) -> PlatformUserCreate:
        """Extract user creation data from Keycloak token."""
        email = token_data.get('email', '')
        username = token_data.get('preferred_username', email.split('@')[0] if email else 'user')
        
        # Generate a unique username if needed
        if not username or len(username) < 3:
            username = f"user_{token_data.get('sub', 'unknown')[-8:]}"
        
        return PlatformUserCreate(
            email=email,
            username=username,
            first_name=token_data.get('given_name'),
            last_name=token_data.get('family_name'),
            display_name=token_data.get('name'),
            external_auth_provider=provider,
            external_user_id=token_data.get('sub', ''),
            provider_metadata=token_data,
            is_active=True
        )
    
    def _extract_user_update_from_token(self, token_data: Dict[str, Any]) -> PlatformUserUpdate:
        """Extract user update data from Keycloak token."""
        return PlatformUserUpdate(
            first_name=token_data.get('given_name'),
            last_name=token_data.get('family_name'),
            display_name=token_data.get('name'),
            # Don't update email/username from token to avoid conflicts
        )
    
    async def _create_list_summary(self, users: List[PlatformUser]) -> PlatformUserListSummary:
        """Create summary statistics for user list."""
        by_provider = {}
        by_company = {}
        by_department = {}
        
        active_count = 0
        superadmin_count = 0
        total_profile_completion = 0
        users_with_tenant_access = 0
        recent_logins_7d = 0
        recent_logins_30d = 0
        
        from datetime import timedelta
        
        now = utc_now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        for user in users:
            # Active count
            if user.is_active:
                active_count += 1
            
            # Superadmin count
            if user.is_superadmin:
                superadmin_count += 1
            
            # Provider counts
            provider = user.external_auth_provider if isinstance(user.external_auth_provider, str) else user.external_auth_provider.value
            by_provider[provider] = by_provider.get(provider, 0) + 1
            
            # Company counts
            if user.company:
                by_company[user.company] = by_company.get(user.company, 0) + 1
            
            # Department counts
            if user.departments:
                for dept in user.departments:
                    by_department[dept] = by_department.get(dept, 0) + 1
            
            # Profile completion
            total_profile_completion += user.profile_completion_percentage
            
            # Recent login tracking
            if user.last_login_at:
                if user.last_login_at >= seven_days_ago:
                    recent_logins_7d += 1
                if user.last_login_at >= thirty_days_ago:
                    recent_logins_30d += 1
        
        # Get tenant access count (expensive query, consider caching)
        # For now, skip this calculation in summary
        
        average_profile_completion = (
            total_profile_completion / len(users) if users else 0
        )
        
        return PlatformUserListSummary(
            total_users=len(users),
            active_users=active_count,
            inactive_users=len(users) - active_count,
            superadmin_users=superadmin_count,
            by_provider=by_provider,
            by_company=by_company,
            by_department=by_department,
            recent_logins_7d=recent_logins_7d,
            recent_logins_30d=recent_logins_30d,
            users_with_tenant_access=users_with_tenant_access,
            average_profile_completion=round(average_profile_completion, 1)
        )
    
    async def _invalidate_user_cache(self, user_id: str, email: str, username: str) -> None:
        """Invalidate user cache entries."""
        cache_keys = [
            self.CACHE_KEY_USER.format(user_id=user_id),
            self.CACHE_KEY_USER_EMAIL.format(email=email.lower()),
            self.CACHE_KEY_USER_USERNAME.format(username=username.lower()),
            self.CACHE_KEY_USER_PERMISSIONS.format(user_id=user_id),
            self.CACHE_KEY_USER_ROLES.format(user_id=user_id)
        ]
        
        for key in cache_keys:
            await self.cache.delete(key)
    
    # New methods for onboarding and profile completion
    
    async def get_user_with_complete_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user with complete profile including computed fields."""
        # Use centralized UserDataService
        from .user_data_service import UserDataService
        user_data_service = UserDataService()
        
        # Get complete user data
        return await user_data_service.get_complete_user_data(
            user_id=user_id,
            include_permissions=True,
            include_roles=True,
            include_tenants=True,
            include_onboarding=True,
            use_cache=True
        )
    
    async def update_user_with_completion(
        self, 
        user_id: str, 
        update_data: PlatformUserUpdate
    ) -> PlatformUserResponse:
        """Update user and recalculate profile completion."""
        # Update user
        updated_user = await self.update_user(user_id, update_data)
        
        # Recalculate profile completion
        completion_percentage = self._calculate_profile_completion(updated_user)
        
        # Update completion percentage in database if changed
        if completion_percentage != updated_user.profile_completion_percentage:
            await self.repository.update(
                user_id,
                {"profile_completion_percentage": completion_percentage}
            )
            updated_user.profile_completion_percentage = completion_percentage
            
            # Invalidate cache to reflect new completion
            user = await self.repository.get_by_id(user_id)
            await self._invalidate_user_cache(user_id, user.email, user.username)
        
        return updated_user
    
    async def complete_user_onboarding(
        self,
        user_id: str,
        completed_steps: Optional[Dict[str, bool]] = None
    ) -> PlatformUserResponse:
        """Mark user onboarding as complete."""
        # Update onboarding status
        updates = {
            "is_onboarding_completed": True,
            "metadata": {}
        }
        
        # Store completed steps in metadata if provided
        if completed_steps:
            user = await self.repository.get_by_id(user_id)
            metadata = user.metadata or {}
            metadata["onboarding_steps"] = completed_steps
            metadata["onboarding_completed_at"] = utc_now().isoformat()
            updates["metadata"] = metadata
        
        # Update user
        await self.repository.update(user_id, updates)
        
        # Get updated user
        updated_user = await self.get_user(user_id)
        
        # Invalidate cache
        user = await self.repository.get_by_id(user_id)
        await self._invalidate_user_cache(user_id, user.email, user.username)
        
        return updated_user
    
    async def get_onboarding_status(self, user_id: str) -> Dict[str, Any]:
        """Get detailed onboarding status for a user.
        
        This method now delegates to the centralized UserDataService to avoid redundancy.
        """
        from .user_data_service import UserDataService
        user_data_service = UserDataService()
        
        # Get complete user data including onboarding information
        user_data = await user_data_service.get_complete_user_data(
            user_id=user_id,
            include_onboarding=True,
            use_cache=True
        )
        
        # Simply return the onboarding-related data
        return {
            "is_completed": user_data.get("is_onboarding_completed", False),
            "completion_percentage": user_data.get("profile_completion_percentage", 0),
            "onboarding_steps": user_data.get("onboarding_steps", {}),
            "user_type": "platform_admin" if (
                user_data.get("is_superadmin") or 
                any(role in ['platform_admin', 'organization_owner', 'organization_admin'] 
                    for role in user_data.get("platform_roles", []))
            ) else "tenant_user",
            "user_created_at": user_data.get("created_at")
        }
    
    def _calculate_profile_completion(self, user: PlatformUserResponse) -> int:
        """Calculate profile completion percentage.
        
        Kept for backward compatibility with update_user_with_completion.
        """
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
        if user.first_name and user.first_name.strip():
            completed_weight += field_weights['first_name']
        if user.last_name and user.last_name.strip():
            completed_weight += field_weights['last_name']
        if user.display_name and user.display_name.strip():
            completed_weight += field_weights['display_name']
        if user.avatar_url:
            completed_weight += field_weights['avatar_url']
        if user.phone:
            completed_weight += field_weights['phone']
        if user.job_title:
            completed_weight += field_weights['job_title']
        if user.company:
            completed_weight += field_weights['company']
        if user.departments and len(user.departments) > 0:
            completed_weight += field_weights['departments']
        if user.timezone and user.timezone != 'UTC':
            completed_weight += field_weights['timezone']
        if user.locale and user.locale != 'en-US':
            completed_weight += field_weights['locale']
        if user.notification_preferences and len(user.notification_preferences) > 0:
            completed_weight += field_weights['notification_preferences']
        if user.ui_preferences and len(user.ui_preferences) > 0:
            completed_weight += field_weights['ui_preferences']
        
        return int((completed_weight / total_weight) * 100)
    
    def _is_profile_complete(self, user: PlatformUserResponse) -> bool:
        """Check if user profile is sufficiently complete."""
        # Consider profile complete if > 70% filled
        return user.profile_completion_percentage >= 70
