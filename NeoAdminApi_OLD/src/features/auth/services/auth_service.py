"""
Simplified Authentication service using neo-commons infrastructure.
Handles login, logout, token management, and user operations.
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import timedelta
from loguru import logger

from src.common.cache.client import get_cache
from src.common.config.settings import settings
from src.common.exceptions.base import (
    UnauthorizedError,
    ValidationError,
    NotFoundError,
    ForbiddenError
)
from src.common.utils import utc_now, format_iso8601

# Use neo-commons auth infrastructure
from neo_commons.auth import create_auth_service
from neo_commons.auth.core.enums import ValidationStrategy
from neo_commons.auth.core.protocols import AuthConfigProtocol

from ..implementations import NeoAdminAuthConfig
from ..repositories.auth_repository import AuthRepository
from ..repositories.permission_repository import PermissionRepository


class AuthService:
    """
    Simplified authentication service using neo-commons infrastructure.
    
    Responsibilities:
    - User authentication flow via neo-commons
    - Token management delegation
    - Session handling
    - User profile management
    """
    
    def __init__(self):
        """Initialize authentication service."""
        self.auth_repo = AuthRepository()
        self.permission_repo = PermissionRepository()
        self.cache = get_cache()
        
        # Use neo-commons auth service with NeoAdminApi settings and database connection
        try:
            # Create custom auth config using NeoAdminApi settings
            auth_config = NeoAdminAuthConfig()
            
            # Create cache service for neo-commons
            from neo_commons.cache.implementations import TenantAwareCacheService
            cache_manager = self.cache  # Use the already initialized cache
            cache_service = TenantAwareCacheService(cache_manager)
            
            # Use a simple permission checker - the user sync issue is in the auth callback
            # The real solution is to make sure the user sync callback has database access
            permission_checker = None  # Will use default SimplePermissionChecker
            
            self.neo_auth_service = create_auth_service(
                auth_config=auth_config,
                cache_service=cache_service
            )
            logger.info("Neo-commons auth service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create neo-commons auth service: {e}")
            # For now, continue without neo-commons service
            self.neo_auth_service = None
        
        # Session cache patterns
        self.SESSION_KEY = "auth:session:{session_id}"
        self.USER_SESSION_KEY = "auth:user:{user_id}:sessions"
        self.SESSION_TTL = 86400  # 24 hours
    
    async def authenticate(
        self,
        username: str,
        password: str,
        remember_me: bool = False
    ) -> Dict[str, Any]:
        """
        Authenticate a platform user via neo-commons with user sync.
        
        Args:
            username: Username or email
            password: User password
            remember_me: Extend session duration
            
        Returns:
            Authentication response with tokens and user info
            
        Raises:
            UnauthorizedError: Invalid credentials
            ForbiddenError: User is not active or lacks access
        """
        try:
            # Check if neo-commons auth service is available
            if self.neo_auth_service is None:
                logger.error("Neo-commons auth service not initialized")
                raise UnauthorizedError("Authentication service unavailable")
            
            # Define user sync callback for database synchronization
            async def user_sync_callback(user_data: Dict[str, Any]) -> Dict[str, Any]:
                """Sync user data to local database."""
                return await self.auth_repo.create_or_update_user(
                    email=user_data.get('email'),
                    username=user_data.get('username'),
                    external_auth_provider="keycloak",
                    external_user_id=user_data.get('external_user_id'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    metadata=user_data.get('metadata', {})
                )
            
            # Use neo-commons for authentication with user sync
            auth_result = await self.neo_auth_service.authenticate(
                username=username,
                password=password,
                realm=settings.keycloak_admin_realm,
                user_sync_callback=user_sync_callback
            )
            
            # Extract user info from neo-commons result
            user_info = auth_result.get('user', {})
            
            # Check if user is active
            if not user_info.get("is_active", False):
                logger.warning(f"Authentication failed: Inactive user - {user_info.get('id')}")
                raise ForbiddenError("Account is disabled")
            
            # Update last login
            await self.auth_repo.update_last_login(user_info['id'])
            
            # Create session
            session_id = auth_result.get('session_id') or f"session_{user_info['id']}_{int(utc_now().timestamp())}"
            
            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_user_info = user_info.copy()
            for key, value in serializable_user_info.items():
                if hasattr(value, 'isoformat'):  # Check if it's a datetime object
                    serializable_user_info[key] = format_iso8601(value)
            
            session_data = {
                'user_id': user_info['id'],
                'session_id': session_id,
                'access_token': auth_result.get('access_token'),
                'refresh_token': auth_result.get('refresh_token'),
                'expires_in': auth_result.get('expires_in', 3600),
                'user_info': serializable_user_info
            }
            
            # Cache session
            await self.cache.set(
                self.SESSION_KEY.format(session_id=session_id),
                session_data,
                ttl=self.SESSION_TTL if not remember_me else self.SESSION_TTL * 7
            )
            
            return {
                'success': True,
                'session_id': session_id,
                'user': user_info,
                'tokens': {
                    'access_token': auth_result.get('access_token'),
                    'refresh_token': auth_result.get('refresh_token'),
                    'token_type': auth_result.get('token_type', 'Bearer')
                },
                'expires_in': auth_result.get('expires_in', 3600)
            }
            
        except Exception as e:
            logger.error(f"Authentication failed for {username}: {e}")
            if "unauthorized" in str(e).lower() or "invalid" in str(e).lower():
                raise UnauthorizedError("Invalid username or password")
            raise
    
    async def validate_token(
        self,
        access_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate access token via neo-commons.
        
        Args:
            access_token: JWT access token
            realm: Optional realm override
            
        Returns:
            Token claims and user info
        """
        try:
            return await self.neo_auth_service.validate_token(
                access_token,
                realm=realm or settings.keycloak_admin_realm
            )
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise UnauthorizedError("Invalid or expired token")
    
    async def logout(self, session_id: str) -> bool:
        """
        Logout user and invalidate session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        try:
            # Get session data
            session_data = await self.cache.get(
                self.SESSION_KEY.format(session_id=session_id)
            )
            
            if session_data:
                # Remove from cache
                await self.cache.delete(
                    self.SESSION_KEY.format(session_id=session_id)
                )
                
                # Optional: Call neo-commons logout if needed
                # await self.neo_auth_service.logout(session_data.get('access_token'))
                
                logger.info(f"Session {session_id} logged out successfully")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Logout failed for session {session_id}: {e}")
            return False
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Get user permissions from repository.
        
        Args:
            user_id: User identifier
            tenant_id: Optional tenant context
            
        Returns:
            List of permission codes
        """
        try:
            return await self.permission_repo.get_user_permissions(
                user_id=user_id,
                tenant_id=tenant_id
            )
        except Exception as e:
            logger.error(f"Failed to get permissions for user {user_id}: {e}")
            return []
    
    async def get_current_user(
        self,
        access_token: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get current user from access token with database lookup for complete user info.
        
        Args:
            access_token: JWT access token
            use_cache: Whether to use cached user data
            
        Returns:
            Complete user information including database fields and roles
        """
        try:
            # First validate the token using neo-commons
            token_data = await self.neo_auth_service.get_current_user(
                token=access_token,
                use_cache=use_cache
            )
            
            if not token_data:
                return None
            
            # Get the external user ID from token
            external_user_id = token_data.get("id")
            if not external_user_id:
                return None
            
            # Load complete user data from database using external_user_id
            user_data = await self.auth_repo.get_user_by_external_id(
                provider="keycloak",
                external_id=external_user_id
            )
            
            if not user_data:
                # If user not found in DB, return token data as fallback
                logger.warning(f"User {external_user_id} not found in database, using token data")
                return token_data
            
            # Load user's roles from the database
            user_roles = await self.auth_repo.get_user_roles(user_data["id"])
            
            # Format roles to match UserProfile model expectations
            formatted_roles = []
            for role in user_roles:
                formatted_roles.append({
                    'id': role.get('id'),
                    'name': role.get('name'),
                    'display_name': role.get('display_name', role.get('name', '').replace('_', ' ').title()),
                    'description': role.get('description', ''),
                    'level': role.get('level'),
                    'is_system': role.get('is_system', False),
                    'source': 'database'
                })
            
            # Load user's permissions from the database
            permissions = await self.get_user_permissions(user_data["id"])
            
            # Merge token data with database data, prioritizing database fields
            merged_user = {
                **token_data,  # Base token data
                **user_data,   # Override with database data
                "realm": token_data.get("realm"),  # Keep realm from token
                "email_verified": token_data.get("email_verified", False),  # Keep from token
                "roles": formatted_roles,  # Add database roles
                "permissions": permissions  # Add database permissions
            }
            
            return merged_user
            
        except Exception as e:
            logger.error(f"Get current user failed: {e}")
            return None

    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh access token via neo-commons.
        
        Args:
            refresh_token: Refresh token
            realm: Optional realm override
            
        Returns:
            New token data
        """
        try:
            return await self.neo_auth_service.refresh_token(
                refresh_token,
                realm=realm or settings.keycloak_admin_realm
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise UnauthorizedError("Invalid or expired refresh token")