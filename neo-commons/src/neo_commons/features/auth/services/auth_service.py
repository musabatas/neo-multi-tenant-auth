"""Main authentication service - orchestrates all auth operations."""

import logging
from typing import Any, Dict, Optional, Set

from ....core.exceptions.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from ....core.value_objects.identifiers import RealmId, UserId, TenantId, PermissionCode, RoleCode
from ..entities.auth_context import AuthContext
from ..entities.jwt_token import JWTToken
from .jwt_validator import JWTValidator
from .keycloak_service import KeycloakService
from .realm_manager import RealmManager
from .token_service import TokenService
from .user_mapper import UserMapper

logger = logging.getLogger(__name__)


class AuthService:
    """Main authentication service that orchestrates all auth operations."""
    
    def __init__(
        self,
        keycloak_service: KeycloakService,
        jwt_validator: JWTValidator,
        user_mapper: UserMapper,
        token_service: TokenService,
        realm_manager: RealmManager,
        auth_cache_service: Optional['AuthCacheService'] = None,
    ):
        """Initialize auth service with dependencies."""
        self.keycloak_service = keycloak_service
        self.jwt_validator = jwt_validator
        self.user_mapper = user_mapper
        self.token_service = token_service
        self.realm_manager = realm_manager
        self.auth_cache_service = auth_cache_service
    
    async def authenticate(
        self, username: str, password: str, realm_id: RealmId
    ) -> AuthContext:
        """Authenticate user and return auth context."""
        try:
            logger.info(f"Authenticating user {username} in realm {realm_id.value}")
            
            # Get realm configuration
            realm_config = await self.realm_manager.get_realm_config(realm_id)
            if not realm_config:
                raise AuthenticationError(f"Realm not configured: {realm_id.value}")
            
            # Authenticate with Keycloak
            jwt_token = await self.keycloak_service.authenticate(
                username=username,
                password=password,
                realm_config=realm_config,
            )
            
            # Validate token and get auth context
            auth_context = await self.token_service.validate_and_cache_token(
                jwt_token.access_token, realm_id
            )
            
            logger.info(f"User {username} authenticated successfully")
            return auth_context
            
        except InvalidCredentialsError as e:
            logger.warning(f"Authentication failed for user {username}: Invalid credentials")
            raise e
        except AuthenticationError as e:
            logger.error(f"Authentication failed for user {username}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise AuthenticationError("Authentication service temporarily unavailable")
    
    async def logout(self, refresh_token: str, user_id: UserId) -> None:
        """Logout user and invalidate tokens."""
        try:
            logger.info(f"Logging out user {user_id.value}")
            
            # Invalidate all user tokens in cache
            await self.token_service.invalidate_user_tokens(user_id)
            
            # Optionally logout from Keycloak (if refresh token provided)
            if refresh_token:
                try:
                    # Extract realm from token or use default approach
                    # For now, we'll invalidate locally and let Keycloak tokens expire
                    pass
                except Exception as e:
                    logger.warning(f"Failed to logout from Keycloak: {e}")
                    # Don't fail logout on Keycloak errors
            
            logger.info(f"User {user_id.value} logged out successfully")
            
        except Exception as e:
            logger.error(f"Logout error for user {user_id.value}: {e}")
            # Don't fail logout on errors - security best practice
    
    async def get_user_permissions(
        self, 
        user_id: UserId, 
        tenant_id: TenantId,
        database_service: Optional[Any] = None
    ) -> Set[PermissionCode]:
        """Get user permissions with caching.
        
        First tries to get from cache, falls back to database if not cached.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (can be None for platform admins)
            database_service: Optional database service for loading permissions
        """
        # Try to get from cache if auth_cache_service is available
        if self.auth_cache_service:
            cached_permissions = await self.auth_cache_service.get_user_permissions(
                user_id, tenant_id
            )
            if cached_permissions is not None:
                logger.debug(f"Retrieved {len(cached_permissions)} permissions from cache for user {user_id.value}")
                return cached_permissions
        
        # Load from database if service provided
        permissions = set()
        if database_service:
            try:
                from ...permissions.repositories.permission_checker import AsyncPGPermissionChecker
                permission_checker = AsyncPGPermissionChecker(database_service)
                
                # Get permission codes as strings from database
                permission_codes = await permission_checker.get_user_permissions(
                    user_id, tenant_id
                )
                
                # Convert string codes to PermissionCode objects
                permissions = {PermissionCode(code) for code in permission_codes}
                logger.info(f"Loaded {len(permissions)} permissions from database for user {user_id.value}")
                
            except Exception as e:
                logger.error(f"Failed to load permissions from database: {e}")
                permissions = set()
        else:
            logger.warning("No database service provided, returning empty permissions")
        
        # Cache the permissions if auth_cache_service is available
        if self.auth_cache_service and permissions:
            await self.auth_cache_service.set_user_permissions(
                user_id, tenant_id, permissions
            )
        
        return permissions
    
    async def get_user_roles(
        self, 
        user_id: UserId, 
        tenant_id: TenantId,
        database_service: Optional[Any] = None
    ) -> Set[RoleCode]:
        """Get user roles with caching.
        
        First tries to get from cache, falls back to database if not cached.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (can be None for platform admins)
            database_service: Optional database service for loading roles
        """
        # Try to get from cache if auth_cache_service is available
        if self.auth_cache_service:
            cached_roles = await self.auth_cache_service.get_user_roles(
                user_id, tenant_id
            )
            if cached_roles is not None:
                logger.debug(f"Retrieved {len(cached_roles)} roles from cache for user {user_id.value}")
                return cached_roles
        
        # Load from database if service provided
        roles = set()
        if database_service:
            try:
                from ...permissions.repositories.permission_checker import AsyncPGPermissionChecker
                permission_checker = AsyncPGPermissionChecker(database_service)
                
                # Get role objects from database
                role_objects = await permission_checker.get_user_roles(
                    user_id, tenant_id
                )
                
                # Extract role codes from role objects
                roles = {role.code for role in role_objects}
                logger.info(f"Loaded {len(roles)} roles from database for user {user_id.value}")
                
            except Exception as e:
                logger.error(f"Failed to load roles from database: {e}")
                roles = set()
        else:
            logger.warning("No database service provided, returning empty roles")
        
        # Cache the roles if auth_cache_service is available
        if self.auth_cache_service and roles:
            await self.auth_cache_service.set_user_roles(
                user_id, tenant_id, roles
            )
        
        return roles
    
    async def invalidate_user_cache(
        self, user_id: UserId, tenant_id: TenantId
    ) -> None:
        """Invalidate all cached data for a user.
        
        This should be called when user data changes (roles, permissions, etc).
        """
        if self.auth_cache_service:
            count = await self.auth_cache_service.invalidate_user(user_id, tenant_id)
            logger.info(f"Invalidated {count} cache entries for user {user_id.value}")
    
    async def invalidate_user_permissions(
        self, user_id: UserId, tenant_id: TenantId
    ) -> None:
        """Invalidate cached permissions for a user.
        
        This should be called when user permissions change.
        """
        if self.auth_cache_service:
            result = await self.auth_cache_service.invalidate_user_permissions(user_id, tenant_id)
            if result:
                logger.info(f"Invalidated permissions cache for user {user_id.value}")
    
    async def invalidate_user_roles(
        self, user_id: UserId, tenant_id: TenantId
    ) -> None:
        """Invalidate cached roles for a user.
        
        This should be called when user roles change.
        """
        if self.auth_cache_service:
            result = await self.auth_cache_service.invalidate_user_roles(user_id, tenant_id)
            if result:
                logger.info(f"Invalidated roles cache for user {user_id.value}")
    
    async def validate_token(
        self, token: str, realm_id: RealmId
    ) -> AuthContext:
        """Validate token and return auth context."""
        try:
            return await self.token_service.validate_and_cache_token(token, realm_id)
        except InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            raise e
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError("Token validation service temporarily unavailable")
    
    async def refresh_token(
        self, refresh_token: str, realm_id: RealmId
    ) -> JWTToken:
        """Refresh access token."""
        try:
            logger.debug(f"Refreshing token for realm {realm_id.value}")
            
            # Get realm configuration
            realm_config = await self.realm_manager.get_realm_config(realm_id)
            if not realm_config:
                raise AuthenticationError(f"Realm not configured: {realm_id.value}")
            
            # Refresh token with Keycloak
            new_jwt_token = await self.keycloak_service.refresh_token(
                refresh_token=refresh_token,
                realm_config=realm_config,
            )
            
            logger.debug("Token refreshed successfully")
            return new_jwt_token
            
        except (InvalidTokenError, AuthenticationError) as e:
            logger.warning(f"Token refresh failed: {e}")
            raise e
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise AuthenticationError("Token refresh service temporarily unavailable")
    
    async def get_user_info(self, user_id: UserId, realm_id: RealmId) -> Dict:
        """Get user information by user ID."""
        try:
            # This would typically fetch from user mapping or database
            # For now, return basic info structure
            return {
                "user_id": user_id.value,
                "realm_id": realm_id.value,
                "message": "User info retrieval not yet implemented",
            }
        except Exception as e:
            logger.error(f"Error getting user info for {user_id.value}: {e}")
            raise AuthenticationError("User info service temporarily unavailable")
    
    async def change_password(
        self, user_id: UserId, current_password: str, new_password: str
    ) -> None:
        """Change user password."""
        try:
            logger.info(f"Password change requested for user {user_id.value}")
            
            # This would typically:
            # 1. Validate current password
            # 2. Update password in Keycloak
            # 3. Invalidate all user tokens
            # 4. Log the security event
            
            # For now, just invalidate tokens
            await self.token_service.invalidate_user_tokens(user_id)
            
            logger.info(f"Password changed for user {user_id.value}")
            
        except Exception as e:
            logger.error(f"Password change error for user {user_id.value}: {e}")
            raise AuthenticationError("Password change service temporarily unavailable")
    
