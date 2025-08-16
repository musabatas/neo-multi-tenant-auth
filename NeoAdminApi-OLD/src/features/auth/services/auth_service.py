"""
Authentication service for platform administrators.
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
from src.common.utils.datetime import utc_now
from src.integrations.keycloak.async_client import get_keycloak_client
from src.integrations.keycloak.token_manager import get_token_manager, ValidationStrategy
from src.integrations.keycloak.realm_manager import get_realm_manager
from ..repositories.auth_repository import AuthRepository
from ..repositories.permission_repository import PermissionRepository


class AuthService:
    """
    Core authentication service for platform administrators.
    
    Responsibilities:
    - User authentication flow
    - Token management
    - Session handling
    - User profile management
    """
    
    def __init__(self):
        """Initialize authentication service."""
        self.auth_repo = AuthRepository()
        self.permission_repo = PermissionRepository()
        self.cache = get_cache()
        self.token_manager = get_token_manager()
        
        # Session cache patterns
        self.SESSION_KEY = "auth:session:{session_id}"
        self.USER_SESSION_KEY = "auth:user:{user_id}:sessions"
        self.SESSION_TTL = 86400  # 24 hours
    
    async def authenticate(
        self,
        username: str,
        password: str,
        tenant_id: Optional[str] = None,
        remember_me: bool = False
    ) -> Dict[str, Any]:
        """
        Authenticate a platform user.
        
        Args:
            username: Username or email
            password: User password
            tenant_id: Optional tenant context for scoped login
            remember_me: Extend session duration
            
        Returns:
            Authentication response with tokens and user info
            
        Raises:
            UnauthorizedError: Invalid credentials
            ForbiddenError: User is not active or lacks access
        """
        # Determine realm for authentication
        realm = settings.keycloak_admin_realm  # Default to admin realm
        
        try:
            # STEP 1: Authenticate with Keycloak first
            keycloak = await get_keycloak_client()
            token_response = await keycloak.authenticate(
                username=username,
                password=password,
                realm=realm
            )
            
            # STEP 2: Validate token to get user info from Keycloak
            token_claims = await self.token_manager.validate_token(
                token_response['access_token'],
                realm=realm,
                strategy=ValidationStrategy.LOCAL
            )
            
            # Extract user info from token
            keycloak_user_id = token_claims.get('sub')
            email = token_claims.get('email', username if '@' in username else f"{username}@example.com")
            preferred_username = token_claims.get('preferred_username', username)
            first_name = token_claims.get('given_name')
            last_name = token_claims.get('family_name')
            full_name = token_claims.get('name')
            
            # Extract additional Keycloak data
            keycloak_roles = []
            realm_access = token_claims.get('realm_access', {})
            if 'roles' in realm_access:
                keycloak_roles.extend(realm_access['roles'])
            
            resource_access = token_claims.get('resource_access', {})
            client_roles = {}
            for client, access in resource_access.items():
                if 'roles' in access:
                    client_roles[client] = access['roles']
            
            # Prepare enhanced metadata with all Keycloak data
            enhanced_metadata = {
                "realm": realm,
                "email_verified": token_claims.get('email_verified', False),
                "keycloak_session_id": token_claims.get('sid'),
                "keycloak_auth_time": token_claims.get('iat'),
                "keycloak_expires": token_claims.get('exp'),
                "keycloak_scopes": token_claims.get('scope', '').split(),
                "keycloak_realm_roles": keycloak_roles,
                "keycloak_client_roles": client_roles,
                "keycloak_azp": token_claims.get('azp'),  # Authorized party
                "keycloak_acr": token_claims.get('acr'),  # Authentication Context Class Reference
                "keycloak_full_name": full_name
            }
            logger.info(f"Storing enhanced metadata: {enhanced_metadata}")
            
            # STEP 3: Create or update user in our database
            user = await self.auth_repo.create_or_update_user(
                email=email,
                username=preferred_username,
                external_auth_provider="keycloak",
                external_user_id=keycloak_user_id,
                first_name=first_name,
                last_name=last_name,
                metadata=enhanced_metadata
            )
            
            # STEP 4: Check if user is active
            if not user.get("is_active", False):
                logger.warning(f"Authentication failed: Inactive user - {user['id']}")
                raise ForbiddenError("Account is disabled")
            
            # STEP 5: If tenant_id provided, check access
            if tenant_id:
                access = await self.auth_repo.check_tenant_access(user['id'], tenant_id)
                if not access:
                    logger.warning(f"User {user['id']} lacks access to tenant {tenant_id}")
                    raise ForbiddenError("No access to specified tenant")
            
            # Update last login
            await self.auth_repo.update_last_login(user['id'])
            
            # Get user permissions
            permissions = await self.permission_repo.get_user_permissions(
                user['id'],
                tenant_id
            )
            logger.info(f"Permissions fetched for user {user['id']}: {len(permissions)} permissions")
            if permissions:
                logger.info(f"First permission: {permissions[0]}")
            
            # Get user roles
            roles = await self.permission_repo.get_user_roles(
                user['id'],
                tenant_id
            )
            logger.info(f"Roles fetched for user {user['id']}: {len(roles)} roles")
            if roles:
                logger.info(f"First role: {roles[0]}")
            
            # Get accessible tenants
            tenant_access = await self.auth_repo.get_user_tenant_access(user['id'])
            
            # Debug: Log user metadata for troubleshooting
            logger.info(f"User metadata: {user.get('metadata', 'NO_METADATA')}")
            logger.info(f"User keys: {list(user.keys())}")
            
            # Create session
            session_id = await self._create_session(
                user_id=user['id'],
                access_token=token_response['access_token'],
                refresh_token=token_response['refresh_token'],
                expires_in=token_response.get('expires_in', 3600),
                tenant_id=tenant_id,
                remember_me=remember_me
            )
            
            # Extract metadata for Keycloak section
            metadata = user.get('metadata', {})
            logger.info(f"Building Keycloak section from metadata: {metadata}")
            
            keycloak_section = {
                "session_id": metadata.get('keycloak_session_id'),
                "realm": metadata.get('realm'),
                "email_verified": metadata.get('email_verified', False),
                "scopes": metadata.get('keycloak_scopes', []),
                "realm_roles": metadata.get('keycloak_realm_roles', []),
                "client_roles": metadata.get('keycloak_client_roles', {}),
                "authorized_party": metadata.get('keycloak_azp'),
                "auth_context_class": metadata.get('keycloak_acr'),
                "full_name": metadata.get('keycloak_full_name')
            }
            logger.info(f"Keycloak section: {keycloak_section}")
            
            # Build response
            response = {
                "access_token": token_response['access_token'],
                "refresh_token": token_response['refresh_token'],
                "token_type": "Bearer",
                "expires_in": token_response.get('expires_in', 3600),
                "session_id": session_id,
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "username": user['username'],
                    "first_name": user.get('first_name'),
                    "last_name": user.get('last_name'),
                    "display_name": user.get('display_name'),
                    "is_active": user.get('is_active', True),
                    "is_superadmin": user.get('is_superadmin', False),
                    "avatar_url": user.get('avatar_url'),
                    "timezone": user.get('timezone'),
                    "language": user.get('language'),
                    "roles": [
                        {
                            "id": role['role_id'],
                            "name": role['role_name'],
                            "display_name": role.get('role_display_name'),
                            "level": role.get('role_level'),
                            "priority": role.get('role_priority'),
                            "role_config": role.get('role_config', {})
                        }
                        for role in roles
                    ],
                    "permissions": [
                        {
                            "code": perm.get('name', f"{perm['resource']}:{perm['action']}"),
                            "resource": perm['resource'],
                            "action": perm['action'],
                            "scope_level": perm.get('scope_level'),
                            "is_dangerous": perm.get('is_dangerous', False),
                            "requires_mfa": perm.get('requires_mfa', False),
                            "requires_approval": perm.get('requires_approval', False),
                            "config": perm.get('permissions_config', {}),
                            "source": perm.get('source_type'),
                            "priority": perm.get('priority', 0)
                        }
                        for perm in permissions
                    ],
                    "tenants": [
                        {
                            "id": access['tenant_id'],
                            "name": access.get('tenant_name'),
                            "slug": access.get('tenant_slug'),
                            "access_level": access.get('access_level'),
                            "expires_at": access.get('expires_at')
                        }
                        for access in tenant_access
                    ],
                    "keycloak": keycloak_section
                }
            }
            
            logger.info(f"User {user['id']} authenticated successfully")
            return response
            
        except UnauthorizedError:
            # Update failed login count only if we have a user
            try:
                if 'user' in locals() and user and user.get('id'):
                    await self.auth_repo.update_failed_login(user['id'])
            except Exception as e:
                logger.warning(f"Failed to update failed login count: {e}")
            raise UnauthorizedError("Invalid username or password")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise UnauthorizedError("Authentication failed")
    
    async def refresh_token(
        self,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh an access token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token response
            
        Raises:
            UnauthorizedError: Invalid or expired refresh token
        """
        try:
            # Refresh with Keycloak
            keycloak = await get_keycloak_client()
            token_response = await keycloak.refresh_token(
                refresh_token=refresh_token,
                realm=settings.keycloak_admin_realm
            )
            
            # Validate new token to get user info
            token_claims = await self.token_manager.validate_token(
                token_response['access_token'],
                realm=settings.keycloak_admin_realm,
                strategy=ValidationStrategy.LOCAL
            )
            
            # Get user from database
            user_id = token_claims.get('sub')
            if user_id:
                # Update session with new tokens
                await self._update_session_tokens(
                    user_id=user_id,
                    access_token=token_response['access_token'],
                    refresh_token=token_response['refresh_token']
                )
                
                # Update user's Keycloak metadata with new token claims
                await self._update_user_keycloak_metadata(user_id, token_claims)
                
                # Clear cached user data since token claims might have changed
                cache_key = f"auth:user:{user_id}:info"
                await self.cache.delete(cache_key)
                logger.info(f"Cleared cached user data and updated metadata for user {user_id}")
            
            logger.info(f"Token refreshed for user {user_id}")
            
            return {
                "access_token": token_response['access_token'],
                "refresh_token": token_response['refresh_token'],
                "token_type": "Bearer",
                "expires_in": token_response.get('expires_in', 3600)
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise UnauthorizedError("Invalid or expired refresh token")
    
    async def logout(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        everywhere: bool = False
    ) -> bool:
        """
        Logout a user session.
        
        Args:
            access_token: Current access token
            refresh_token: Optional refresh token for complete logout
            everywhere: Logout from all devices/sessions
            
        Returns:
            True if logout successful
        """
        try:
            # Validate token to get user info
            token_claims = await self.token_manager.validate_token(
                access_token,
                realm=settings.keycloak_admin_realm,
                strategy=ValidationStrategy.LOCAL
            )
            
            user_id = token_claims.get('sub')
            
            # Revoke tokens
            await self.token_manager.revoke_token(access_token)
            
            # Logout from Keycloak if refresh token provided
            if refresh_token:
                keycloak = await get_keycloak_client()
                await keycloak.logout(
                    refresh_token=refresh_token,
                    realm=settings.keycloak_admin_realm
                )
            
            # Clear sessions
            if user_id:
                if everywhere:
                    # Clear all user sessions
                    await self._clear_all_user_sessions(user_id)
                    logger.info(f"User {user_id} logged out from all devices")
                else:
                    # Clear current session
                    await self._clear_user_session(user_id, access_token)
                    logger.info(f"User {user_id} logged out")
            
            return True
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Logout errors are not critical
            return False
    
    async def get_current_user(
        self,
        access_token: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get current user information from token.
        
        Args:
            access_token: Access token
            use_cache: Whether to use cached user info
            
        Returns:
            User information with roles and permissions
            
        Raises:
            UnauthorizedError: Invalid token
            NotFoundError: User not found
        """
        # Validate token
        token_claims = await self.token_manager.validate_token(
            access_token,
            realm=settings.keycloak_admin_realm,
            critical=False  # Use dual validation
        )
        
        # Get user ID from token
        external_id = token_claims.get('sub')
        if not external_id:
            raise UnauthorizedError("Invalid token claims")
        
        # Get user from database by external ID
        user = await self.auth_repo.get_user_by_external_id(
            provider="keycloak",
            external_id=external_id
        )
        
        if not user:
            # Try to get by email from token
            email = token_claims.get('email')
            if email:
                user = await self.auth_repo.get_user_by_email(email)
        
        if not user:
            raise NotFoundError("User", external_id)
        
        # Check if user is active
        if not user.get("is_active", False):
            raise ForbiddenError("Account is disabled")
        
        # Use centralized UserDataService for complete user data
        from src.features.users.services.user_data_service import UserDataService
        user_data_service = UserDataService()
        
        # Get complete user data using the centralized service
        user_info = await user_data_service.get_complete_user_data(
            user_id=user['id'],
            include_permissions=True,
            include_roles=True,
            include_tenants=True,
            include_onboarding=True,
            use_cache=use_cache
        )
        
        # Add Keycloak metadata
        metadata = user.get('metadata', {})
        user_info['keycloak'] = {
            "session_id": metadata.get('keycloak_session_id'),
            "realm": metadata.get('realm'),
            "email_verified": metadata.get('email_verified', False),
            "scopes": metadata.get('keycloak_scopes', []),
            "realm_roles": metadata.get('keycloak_realm_roles', []),
            "client_roles": metadata.get('keycloak_client_roles', {}),
            "authorized_party": metadata.get('keycloak_azp'),
            "auth_context_class": metadata.get('keycloak_acr'),
            "full_name": metadata.get('keycloak_full_name')
        }
        
        return user_info
    
    async def get_current_user_profile(
        self,
        access_token: str,
        use_cache: bool = True
    ) -> "UserProfile":
        """
        Get current user as UserProfile model with flattened Keycloak fields.
        
        This method centralizes the logic shared between /auth/me and /user/me endpoints.
        
        Args:
            access_token: Access token
            use_cache: Whether to use cached user info
            
        Returns:
            UserProfile model with flattened Keycloak fields
            
        Raises:
            UnauthorizedError: Invalid token
            NotFoundError: User not found
        """
        # Import here to avoid circular imports
        from ..models.response import UserProfile
        
        # Get raw user info
        user_info = await self.get_current_user(
            access_token=access_token,
            use_cache=use_cache
        )
        
        # Extract Keycloak data for flattened fields
        keycloak_data = user_info.get("keycloak", {})
        
        # Map to UserProfile model with flattened structure
        user_profile = UserProfile(
            id=user_info["id"],
            email=user_info["email"],
            username=user_info["username"],
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            display_name=user_info.get("display_name"),
            full_name=user_info.get("full_name"),
            avatar_url=user_info.get("avatar_url"),
            phone=user_info.get("phone"),
            job_title=user_info.get("job_title"),
            company=user_info.get("company"),
            departments=user_info.get("departments", []),
            timezone=user_info.get("timezone", "UTC"),
            locale=user_info.get("locale", "en-US"),
            language=user_info.get("language", "en"),
            notification_preferences=user_info.get("notification_preferences", {}),
            ui_preferences=user_info.get("ui_preferences", {}),
            is_onboarding_completed=user_info.get("is_onboarding_completed", False),
            profile_completion_percentage=user_info.get("profile_completion_percentage", 0),
            is_active=user_info.get("is_active", True),
            is_superadmin=user_info.get("is_superadmin", False),
            roles=user_info.get("roles", []),
            permissions=user_info.get("permissions", []),
            tenants=user_info.get("tenants", []),
            last_login_at=user_info.get("last_login_at"),
            created_at=user_info.get("created_at"),
            updated_at=user_info.get("updated_at"),
            external_auth_provider=user_info.get("external_auth_provider"),
            external_user_id=user_info.get("external_user_id"),
            # Flattened Keycloak fields
            session_id=keycloak_data.get("session_id"),
            realm=keycloak_data.get("realm"),
            email_verified=keycloak_data.get("email_verified", False),
            authorized_party=keycloak_data.get("authorized_party")
        )
        
        return user_profile
    
    async def invalidate_user_cache(self, user_id: str) -> None:
        """
        Invalidate user cache entries.
        
        Args:
            user_id: User ID to invalidate cache for
        """
        # Get user to find external ID
        user = await self.auth_repo.get_user_by_id(user_id)
        if user:
            external_id = user.get('external_user_id')
            if external_id:
                cache_key = f"auth:user:{external_id}:info"
                await self.cache.delete(cache_key)
    
    async def _create_session(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        tenant_id: Optional[str] = None,
        remember_me: bool = False
    ) -> str:
        """
        Create a new user session.
        
        Args:
            user_id: User ID
            access_token: Access token
            refresh_token: Refresh token
            expires_in: Token expiry in seconds
            tenant_id: Optional tenant context
            remember_me: Extend session duration
            
        Returns:
            Session ID
        """
        import uuid
        session_id = str(uuid.uuid4())
        
        # Calculate session TTL
        ttl = self.SESSION_TTL
        if remember_me:
            ttl = ttl * 7  # 7 days for remember me
        
        # Create session data
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "created_at": utc_now().isoformat(),
            "expires_at": (utc_now() + timedelta(seconds=expires_in)).isoformat(),
            "remember_me": remember_me
        }
        
        # Store session
        session_key = self.SESSION_KEY.format(session_id=session_id)
        await self.cache.set(session_key, session_data, ttl=ttl)
        
        # Add to user's session list
        user_sessions_key = self.USER_SESSION_KEY.format(user_id=user_id)
        await self.cache.sadd(user_sessions_key, session_id)
        await self.cache.expire(user_sessions_key, ttl)
        
        return session_id
    
    async def _update_session_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str
    ):
        """Update session with new tokens after refresh."""
        # Get user's sessions
        user_sessions_key = self.USER_SESSION_KEY.format(user_id=user_id)
        session_ids = await self.cache.smembers(user_sessions_key)
        
        # Update active sessions
        for session_id in session_ids:
            session_key = self.SESSION_KEY.format(session_id=session_id)
            session_data = await self.cache.get(session_key)
            
            if session_data:
                session_data['updated_at'] = utc_now().isoformat()
                ttl = await self.cache.ttl(session_key)
                await self.cache.set(session_key, session_data, ttl=ttl)
    
    async def _clear_user_session(self, user_id: str, access_token: str):
        """Clear a specific user session."""
        # Implementation depends on how we track sessions
        pass
    
    async def _clear_all_user_sessions(self, user_id: str):
        """Clear all sessions for a user."""
        # Get all user sessions
        user_sessions_key = self.USER_SESSION_KEY.format(user_id=user_id)
        session_ids = await self.cache.smembers(user_sessions_key)
        
        # Delete each session
        for session_id in session_ids:
            session_key = self.SESSION_KEY.format(session_id=session_id)
            await self.cache.delete(session_key)
        
        # Delete user sessions set
        await self.cache.delete(user_sessions_key)
        
        # Clear cached user info
        cache_key = f"auth:user:{user_id}:info"
        await self.cache.delete(cache_key)
        
        # Clear cached tokens
        await self.token_manager.clear_user_tokens(user_id)
    
    async def _update_user_keycloak_metadata(self, external_user_id: str, token_claims: Dict[str, Any]):
        """
        Update user's Keycloak metadata with fresh token claims.
        
        Args:
            external_user_id: Keycloak user ID (sub claim)
            token_claims: Fresh token claims from Keycloak
        """
        try:
            # Extract updated Keycloak data from token claims
            realm_access = token_claims.get('realm_access', {})
            keycloak_roles = []
            if 'roles' in realm_access:
                keycloak_roles.extend(realm_access['roles'])
            
            # Extract client roles
            resource_access = token_claims.get('resource_access', {})
            client_roles = {}
            for client, access in resource_access.items():
                if 'roles' in access:
                    client_roles[client] = access['roles']
            
            # Build full name
            first_name = token_claims.get('given_name', '')
            last_name = token_claims.get('family_name', '')
            full_name = f"{first_name} {last_name}".strip() or token_claims.get('name', '')
            
            # Prepare updated metadata
            updated_metadata = {
                "realm": settings.keycloak_admin_realm,
                "email_verified": token_claims.get('email_verified', False),
                "keycloak_session_id": token_claims.get('sid'),
                "keycloak_auth_time": token_claims.get('iat'),
                "keycloak_expires": token_claims.get('exp'),
                "keycloak_scopes": token_claims.get('scope', '').split(),
                "keycloak_realm_roles": keycloak_roles,
                "keycloak_client_roles": client_roles,
                "keycloak_azp": token_claims.get('azp'),
                "keycloak_acr": token_claims.get('acr'),
                "keycloak_full_name": full_name
            }
            
            # Update user metadata in database
            await self.auth_repo.update_user_metadata_by_external_id(
                provider="keycloak",
                external_id=external_user_id,
                metadata=updated_metadata
            )
            
            logger.info(f"Updated Keycloak metadata for user {external_user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to update Keycloak metadata for user {external_user_id}: {e}")
            # Don't raise - this is not critical for token refresh