"""Get user context query."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, Set, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId, PermissionCode, RoleCode
from ...core.value_objects import RealmIdentifier
from ...core.entities import UserContext
from ...core.exceptions import AuthenticationFailed


@dataclass
class GetUserContextRequest:
    """Request to get user context."""
    
    user_id: UserId
    tenant_id: Optional[TenantId] = None
    realm_id: Optional[RealmIdentifier] = None
    
    # Context loading options
    load_permissions: bool = True
    load_roles: bool = True
    load_teams: bool = True
    load_profile: bool = True
    
    # Permission context
    permission_scope: str = "all"  # all, tenant, platform
    include_team_permissions: bool = True
    include_role_permissions: bool = True
    
    # Caching options
    use_cache: bool = True
    cache_ttl_seconds: Optional[int] = None


@dataclass
class GetUserContextResponse:
    """Response from get user context query."""
    
    user_context: UserContext
    loaded_timestamp: datetime
    
    # Loading statistics
    permissions_loaded: int = 0
    roles_loaded: int = 0
    teams_loaded: int = 0
    
    # Cache information
    loaded_from_cache: bool = False
    cache_hit_ratio: Optional[float] = None
    
    def __post_init__(self):
        """Initialize response after creation."""
        if not hasattr(self, 'loaded_timestamp') or self.loaded_timestamp is None:
            object.__setattr__(self, 'loaded_timestamp', datetime.now(timezone.utc))


@runtime_checkable
class UserProvider(Protocol):
    """Protocol for user data operations."""
    
    async def get_user_profile(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> Dict[str, Any]:
        """Get user profile information."""
        ...


@runtime_checkable
class PermissionProvider(Protocol):
    """Protocol for permission loading operations."""
    
    async def get_user_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope: str = "all"
    ) -> Set[PermissionCode]:
        """Get user permissions with scope filtering."""
        ...
    
    async def get_team_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> Set[PermissionCode]:
        """Get permissions from team memberships."""
        ...


@runtime_checkable
class RoleProvider(Protocol):
    """Protocol for role loading operations."""
    
    async def get_user_roles(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> Set[RoleCode]:
        """Get user roles."""
        ...


@runtime_checkable
class TeamProvider(Protocol):
    """Protocol for team information operations."""
    
    async def get_user_teams(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> Dict[str, Any]:
        """Get user team memberships."""
        ...


@runtime_checkable
class ContextCache(Protocol):
    """Protocol for user context caching operations."""
    
    async def get_cached_context(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> Optional[UserContext]:
        """Get cached user context."""
        ...
    
    async def cache_context(
        self,
        user_context: UserContext,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Cache user context."""
        ...


class GetUserContext:
    """Query to get user context following maximum separation principle.
    
    Handles ONLY user context retrieval workflow orchestration.
    Does not handle user storage, permission calculation, or cache implementation.
    """
    
    def __init__(
        self,
        user_provider: UserProvider,
        permission_provider: PermissionProvider,
        role_provider: RoleProvider,
        team_provider: TeamProvider,
        context_cache: Optional[ContextCache] = None
    ):
        """Initialize query with protocol dependencies."""
        self._user_provider = user_provider
        self._permission_provider = permission_provider
        self._role_provider = role_provider
        self._team_provider = team_provider
        self._context_cache = context_cache
    
    async def execute(self, request: GetUserContextRequest) -> GetUserContextResponse:
        """Execute get user context query.
        
        Args:
            request: User context request with user ID and options
            
        Returns:
            User context response with loaded context and statistics
            
        Raises:
            AuthenticationFailed: When user context cannot be loaded
        """
        load_start = datetime.now(timezone.utc)
        
        try:
            # Step 1: Try to load from cache if enabled
            cached_context = None
            if request.use_cache and self._context_cache:
                cached_context = await self._context_cache.get_cached_context(
                    user_id=request.user_id,
                    tenant_id=request.tenant_id
                )
                
                if cached_context and self._is_cache_valid(cached_context, request):
                    return GetUserContextResponse(
                        user_context=cached_context,
                        loaded_timestamp=load_start,
                        loaded_from_cache=True,
                        cache_hit_ratio=1.0
                    )
            
            # Step 2: Load user profile
            user_profile = {}
            if request.load_profile:
                try:
                    user_profile = await self._user_provider.get_user_profile(
                        user_id=request.user_id,
                        tenant_id=request.tenant_id
                    )
                except Exception as e:
                    # Profile loading failure doesn't prevent context creation
                    user_profile = {"profile_error": str(e)}
            
            # Step 3: Load permissions
            permissions_loaded = 0
            direct_permissions: Set[PermissionCode] = set()
            team_permissions: Set[PermissionCode] = set()
            
            if request.load_permissions:
                # Load direct permissions
                try:
                    direct_permissions = await self._permission_provider.get_user_permissions(
                        user_id=request.user_id,
                        tenant_id=request.tenant_id,
                        scope=request.permission_scope
                    )
                    permissions_loaded += len(direct_permissions)
                except Exception:
                    pass  # Continue with empty permissions
                
                # Load team permissions if requested
                if request.include_team_permissions and request.load_teams:
                    try:
                        team_permissions = await self._permission_provider.get_team_permissions(
                            user_id=request.user_id,
                            tenant_id=request.tenant_id
                        )
                        permissions_loaded += len(team_permissions)
                    except Exception:
                        pass  # Continue with empty team permissions
            
            # Step 4: Load roles
            roles_loaded = 0
            user_roles: Set[RoleCode] = set()
            
            if request.load_roles:
                try:
                    user_roles = await self._role_provider.get_user_roles(
                        user_id=request.user_id,
                        tenant_id=request.tenant_id
                    )
                    roles_loaded = len(user_roles)
                except Exception:
                    pass  # Continue with empty roles
            
            # Step 5: Load team information
            teams_loaded = 0
            team_info = {}
            
            if request.load_teams:
                try:
                    team_info = await self._team_provider.get_user_teams(
                        user_id=request.user_id,
                        tenant_id=request.tenant_id
                    )
                    teams_loaded = len(team_info.get('teams', []))
                except Exception:
                    pass  # Continue with empty team info
            
            # Step 6: Create user context
            user_context = UserContext(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                realm_id=request.realm_id,
                
                # Profile information
                email=user_profile.get('email'),
                username=user_profile.get('username'),
                display_name=user_profile.get('display_name'),
                first_name=user_profile.get('first_name'),
                last_name=user_profile.get('last_name'),
                avatar_url=user_profile.get('avatar_url'),
                phone=user_profile.get('phone'),
                job_title=user_profile.get('job_title'),
                company=user_profile.get('company'),
                
                # Status and flags
                is_active=user_profile.get('status') == 'active',
                is_system_user=user_profile.get('is_system_user', False),
                is_onboarding_completed=user_profile.get('is_onboarding_completed', True),
                requires_mfa=user_profile.get('requires_mfa', False),
                
                # Localization
                timezone=user_profile.get('timezone', 'UTC'),
                locale=user_profile.get('locale', 'en-US'),
                
                # Permissions and roles
                roles=user_roles,
                direct_permissions=direct_permissions,
                team_permissions=team_permissions,
                
                # Metadata
                user_metadata=user_profile.get('metadata', {}),
                
                # Context timestamps
                context_created_at=load_start,
                permissions_loaded_at=load_start if request.load_permissions else None,
                
                # Authentication status (not authenticated via this query)
                is_authenticated=False
            )
            
            # Step 7: Cache the context if caching is enabled
            if request.use_cache and self._context_cache:
                try:
                    await self._context_cache.cache_context(
                        user_context=user_context,
                        ttl_seconds=request.cache_ttl_seconds
                    )
                except Exception:
                    pass  # Cache failure doesn't affect response
            
            # Step 8: Return response
            return GetUserContextResponse(
                user_context=user_context,
                loaded_timestamp=load_start,
                permissions_loaded=permissions_loaded,
                roles_loaded=roles_loaded,
                teams_loaded=teams_loaded,
                loaded_from_cache=False,
                cache_hit_ratio=0.0 if cached_context is None else 0.5
            )
            
        except Exception as e:
            raise AuthenticationFailed(
                "Failed to load user context",
                reason="context_load_error",
                context={
                    "user_id": str(request.user_id.value),
                    "tenant_id": str(request.tenant_id.value) if request.tenant_id else None,
                    "error": str(e)
                }
            ) from e
    
    def _is_cache_valid(self, cached_context: UserContext, request: GetUserContextRequest) -> bool:
        """Check if cached context is still valid for the request.
        
        Args:
            cached_context: Cached user context
            request: Current request
            
        Returns:
            True if cached context is valid
        """
        # Check if context is too old (default 5 minutes)
        if cached_context.context_age_seconds > 300:
            return False
        
        # Check if permissions were loaded when required
        if request.load_permissions and not cached_context.permissions_loaded_at:
            return False
        
        # Context is valid
        return True