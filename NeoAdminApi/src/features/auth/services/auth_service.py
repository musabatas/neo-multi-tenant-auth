"""Auth service for admin authentication using neo-commons."""

import logging
from typing import Optional

from neo_commons.core.exceptions.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from neo_commons.core.value_objects.identifiers import RealmId, UserId, KeycloakUserId
from neo_commons.core.value_objects import RoleCode, PermissionCode
from neo_commons.features.auth.entities.auth_context import AuthContext
from neo_commons.features.auth.entities.jwt_token import JWTToken
from neo_commons.features.auth.entities.keycloak_config import KeycloakConfig
from neo_commons.features.auth.services.password_reset_service import PasswordResetService
from neo_commons.features.auth.adapters.keycloak_admin import KeycloakAdminAdapter
from neo_commons.core.value_objects.identifiers import TenantId

from ..models.request import (
    AdminLoginRequest, 
    AdminLogoutRequest,
    ForgotPasswordRequest,
    SendEmailVerificationRequest,
    SendRequiredActionsRequest,
    RemoveTOTPRequest
)
from ..models.response import (
    AdminLoginResponse, 
    AdminTokenResponse, 
    AdminUserResponse,
    ForgotPasswordResponse,
    EmailVerificationResponse,
    RequiredActionsResponse,
    UserCredentialsResponse,
    RemoveTOTPResponse
)

logger = logging.getLogger(__name__)


class AuthService:
    """Admin authentication service using neo-commons auth features."""
    
    def __init__(self, auth_factory):
        """Initialize with neo-commons auth factory."""
        self.auth_factory = auth_factory
    
    async def login(self, login_request: AdminLoginRequest) -> AdminLoginResponse:
        """Authenticate admin user and return tokens."""
        try:
            # Use centralized configuration
            from neo_commons.config.manager import get_env_config
            env_config = get_env_config()
            
            keycloak_config = KeycloakConfig(
                server_url=env_config.keycloak_server_url,
                realm_name=env_config.keycloak_realm,
                client_id=env_config.keycloak_client_id,
                client_secret=env_config.keycloak_client_secret,
                require_https=False,  # Disable HTTPS requirement for development
            )
            
            # Authenticate with Keycloak
            from neo_commons.features.auth.adapters.keycloak_openid import KeycloakOpenIDAdapter
            async with KeycloakOpenIDAdapter(keycloak_config) as openid_client:
                jwt_token = await openid_client.authenticate(
                    login_request.username, login_request.password
                )
                
                # For admin authentication, create a simple auth context without tenant lookups
                import jwt
                
                # Decode token to get user info (without validation for now)
                token_payload = jwt.decode(jwt_token.access_token, options={"verify_signature": False})
                
                # Extract roles from token
                realm_access = token_payload.get("realm_access", {})
                role_names = realm_access.get("roles", [])
                roles = [RoleCode(role) for role in role_names if role]
                
                # Sync user to database if needed
                keycloak_user_id = token_payload.get("sub", "")
                username = token_payload.get("preferred_username", login_request.username)
                email = token_payload.get("email", "")
                first_name = token_payload.get("given_name", "")
                last_name = token_payload.get("family_name", "")
                
                # For admin users, check if they exist in admin.users table and sync if needed
                platform_user_id = await self._sync_admin_user(
                    keycloak_user_id=keycloak_user_id,
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Load database roles and permissions
                from ....common.dependencies import get_database_service
                from neo_commons.features.users import UserPermissionService
                
                database_service = await get_database_service()
                permission_service = UserPermissionService(database_service)
                
                # Get user's roles and permissions from database
                user_auth_context = await permission_service.get_user_auth_context(
                    platform_user_id, tenant_id=None
                )
                
                # Convert database roles and permissions to AuthContext format
                db_roles = {RoleCode(role_code) for role_code in user_auth_context['roles']['codes']}
                db_permissions = {PermissionCode(perm['code']) for perm in user_auth_context['permissions']}
                
                # Create admin auth context with database RBAC
                from datetime import datetime, timezone
                
                auth_context = AuthContext(
                    user_id=platform_user_id,
                    keycloak_user_id=KeycloakUserId(keycloak_user_id),
                    tenant_id=None,  # Admin users don't belong to a specific tenant
                    realm_id=RealmId(keycloak_config.realm_name),
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    roles=db_roles,  # Database roles instead of Keycloak
                    permissions=db_permissions,  # Database permissions instead of empty
                    session_id=token_payload.get("sid", ""),
                    expires_at=datetime.fromtimestamp(token_payload.get("exp", 0), tz=timezone.utc) if token_payload.get("exp") else None,
                    authenticated_at=datetime.now(timezone.utc),
                )
                
                logger.info(f"Admin user {username} authenticated and mapped to platform user ID: {platform_user_id.value}")
                
                # Create response
                token_response = AdminTokenResponse(
                    access_token=jwt_token.access_token,
                    refresh_token=jwt_token.refresh_token,
                    token_type=jwt_token.token_type,
                    expires_in=jwt_token.expires_in,
                    refresh_expires_in=jwt_token.refresh_expires_in,
                )
                
                # Get comprehensive user data from database
                from neo_commons.features.users import UserService, UserRepository
                user_repository = UserRepository(database_service)
                user_service = UserService(user_repository)
                
                complete_user_data = await user_service.get_complete_user_data(
                    platform_user_id, schema_name="admin"
                )
                
                # Create user response with comprehensive data and permissions
                user_response = AdminUserResponse.from_auth_context_with_user_data(
                    auth_context, complete_user_data or {}, user_auth_context['permissions']
                )
                
                logger.info(f"Admin user {login_request.username} logged in successfully")
                
                return AdminLoginResponse(
                    tokens=token_response,
                    user=user_response,
                    session_id=auth_context.session_id,
                    message="Admin login successful",
                )
                
        except InvalidCredentialsError as e:
            logger.warning(f"Login failed for user {login_request.username}: Invalid credentials")
            raise e
        except AuthenticationError as e:
            logger.error(f"Login failed for user {login_request.username}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error during admin login: {e}")
            raise AuthenticationError("Login service temporarily unavailable")
    
    async def logout(self, logout_request: AdminLogoutRequest, current_user: AuthContext) -> dict:
        """Logout admin user and invalidate tokens."""
        try:
            if logout_request.refresh_token:
                # Use centralized configuration
                from neo_commons.config.manager import get_env_config
                env_config = get_env_config()
                
                keycloak_config = KeycloakConfig(
                    server_url=env_config.keycloak_server_url,
                    realm_name=env_config.keycloak_realm,
                    client_id=env_config.keycloak_client_id,
                    client_secret=env_config.keycloak_client_secret,
                    require_https=False,  # Disable HTTPS requirement for development
                )
                
                # Logout from Keycloak
                from neo_commons.features.auth.adapters.keycloak_openid import KeycloakOpenIDAdapter
                async with KeycloakOpenIDAdapter(keycloak_config) as openid_client:
                    await openid_client.logout(logout_request.refresh_token)
            
            # For admin logout, we just invalidate in Keycloak
            # No need for complex token cache invalidation for admin users
            
            logger.info(f"Admin user {current_user.user_id.value} logged out successfully")
            
            return {
                "message": "Admin logout successful",
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Don't fail logout on errors
            return {
                "message": "Logout completed",
                "success": True,
            }
    
    async def get_current_user_info(self, current_user: AuthContext) -> AdminUserResponse:
        """Get current admin user information with fresh permissions."""
        try:
            # Load fresh permissions from database
            from ....common.dependencies import get_database_service
            from neo_commons.features.users import UserPermissionService
            
            database_service = await get_database_service()
            permission_service = UserPermissionService(database_service)
            
            # Get fresh user auth context
            user_auth_context = await permission_service.get_user_auth_context(
                current_user.user_id, tenant_id=None
            )
            
            # Create updated auth context with fresh permissions
            updated_context = AuthContext(
                user_id=current_user.user_id,
                keycloak_user_id=current_user.keycloak_user_id,
                tenant_id=current_user.tenant_id,
                realm_id=current_user.realm_id,
                username=current_user.username,
                email=current_user.email,
                first_name=current_user.first_name,
                last_name=current_user.last_name,
                roles={RoleCode(role_code) for role_code in user_auth_context['roles']['codes']},
                permissions={PermissionCode(perm['code']) for perm in user_auth_context['permissions']},
                session_id=current_user.session_id,
                expires_at=current_user.expires_at,
                authenticated_at=current_user.authenticated_at,
            )
            
            # Get comprehensive user data from database
            from neo_commons.features.users import UserService, UserRepository
            user_repository = UserRepository(database_service)
            user_service = UserService(user_repository)
            
            complete_user_data = await user_service.get_complete_user_data(
                current_user.user_id, schema_name="admin"
            )
            
            return AdminUserResponse.from_auth_context_with_user_data(
                updated_context, complete_user_data or {}, user_auth_context['permissions']
            )
            
        except Exception as e:
            logger.error(f"Failed to get fresh user info for {current_user.user_id.value}: {e}")
            # Fallback to cached context
            return AdminUserResponse.from_auth_context(current_user)
    
    async def _sync_admin_user(
        self,
        keycloak_user_id: str,
        username: str,
        email: str,
        first_name: str,
        last_name: str
    ) -> UserId:
        """Sync Keycloak user to admin.users table using neo-commons UserService."""
        try:
            from ....common.dependencies import get_database_service
            from neo_commons.features.users import UserRepository, UserService
            
            # Get database service
            database_service = await get_database_service()
            
            # Create user repository and service
            user_repository = UserRepository(database_service)
            user_service = UserService(user_repository)
            
            # Use neo-commons service to sync user
            user_id = await user_service.sync_keycloak_user(
                external_user_id=keycloak_user_id,
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                schema_name="admin"
            )
            
            logger.info(f"Successfully synced admin user {username} with ID: {user_id.value}")
            return user_id
                    
        except Exception as e:
            logger.error(f"Failed to sync admin user {username}: {e}")
            # Return keycloak_user_id as fallback
            return UserId(keycloak_user_id)
    
    
    async def refresh_token(self, refresh_token: str) -> AdminTokenResponse:
        """Refresh admin user access token."""
        try:
            import os
            # Create Keycloak config directly from environment variables for admin realm
            keycloak_config = KeycloakConfig(
                server_url=os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
                realm_name=os.getenv("KEYCLOAK_ADMIN_REALM", "platform-admin"),
                client_id=os.getenv("KEYCLOAK_CLIENT_ID", "neo-admin-api"),
                client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET", ""),
                require_https=False,  # Disable HTTPS requirement for development
            )
            
            # Refresh token with Keycloak
            from neo_commons.features.auth.adapters.keycloak_openid import KeycloakOpenIDAdapter
            async with KeycloakOpenIDAdapter(keycloak_config) as openid_client:
                jwt_token = await openid_client.refresh_token(refresh_token)
                
                return AdminTokenResponse(
                    access_token=jwt_token.access_token,
                    refresh_token=jwt_token.refresh_token,
                    token_type=jwt_token.token_type,
                    expires_in=jwt_token.expires_in,
                    refresh_expires_in=jwt_token.refresh_expires_in,
                )
                
        except (InvalidTokenError, AuthenticationError) as e:
            logger.warning(f"Token refresh failed: {e}")
            raise e
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise AuthenticationError("Token refresh service temporarily unavailable")
    
    async def _get_keycloak_config(self):
        """Get Keycloak configuration for admin realm."""
        import os
        return KeycloakConfig(
            server_url=os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
            realm_name=os.getenv("KEYCLOAK_ADMIN_REALM", "platform-admin"),
            client_id=os.getenv("KEYCLOAK_CLIENT_ID", "neo-admin-api"),
            client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET", ""),
            require_https=False,  # Disable HTTPS requirement for development
        )
    
    async def _get_password_reset_service(self) -> PasswordResetService:
        """Get password reset service with Keycloak admin adapter.
        
        Supports two authentication methods:
        1. Client credentials (preferred): Uses KEYCLOAK_CLIENT_ID + KEYCLOAK_CLIENT_SECRET
        2. Admin credentials (fallback): Uses KEYCLOAK_ADMIN + KEYCLOAK_PASSWORD
        """
        import os
        
        server_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
        
        # Try client credentials first (preferred method)
        client_id = os.getenv("KEYCLOAK_CLIENT_ID")
        client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        admin_realm = os.getenv("KEYCLOAK_ADMIN_REALM", "master")
        
        if client_id and client_secret:
            # Use client credentials authentication
            keycloak_admin = KeycloakAdminAdapter(
                server_url=server_url,
                realm_name=admin_realm,
                client_id=client_id,
                client_secret=client_secret,
                verify=False,  # Disable SSL verification for development
            )
        else:
            # Fallback to admin username/password
            admin_username = os.getenv("KEYCLOAK_ADMIN", "admin")
            admin_password = os.getenv("KEYCLOAK_PASSWORD", "admin")
            
            keycloak_admin = KeycloakAdminAdapter(
                server_url=server_url,
                realm_name=admin_realm,
                username=admin_username,
                password=admin_password,
                verify=False,  # Disable SSL verification for development
            )
        
        return PasswordResetService(keycloak_admin)
    
    async def initiate_forgot_password(self, request: ForgotPasswordRequest) -> ForgotPasswordResponse:
        """Initiate forgot password process for admin user."""
        try:
            password_service = await self._get_password_reset_service()
            keycloak_config = await self._get_keycloak_config()
            
            # For admin realm, we don't need a tenant_id, but the service requires it
            # We'll use a dummy tenant_id since this is admin realm
            admin_tenant_id = TenantId("00000000-0000-0000-0000-000000000000")
            
            from neo_commons.features.auth.models.requests import ForgotPasswordRequest as NeoForgotPasswordRequest
            neo_request = NeoForgotPasswordRequest(email=request.email)
            
            result = await password_service.initiate_password_reset(
                request=neo_request,
                tenant_id=admin_tenant_id,
                realm_name=keycloak_config.realm_name,
            )
            
            logger.info(f"Password reset initiated for admin email: {request.email}")
            
            return ForgotPasswordResponse(
                message=result.message,
                success=True,
                reset_token_sent=result.reset_token_sent,
                expires_in=getattr(result, 'expires_in', None),
            )
            
        except Exception as e:
            logger.error(f"Failed to initiate password reset for {request.email}: {e}")
            # Return generic success message for security
            return ForgotPasswordResponse(
                message="If an account with this email exists, you will receive a password reset link.",
                success=True,
                reset_token_sent=False,
            )
    
    async def send_email_verification(self, request: SendEmailVerificationRequest) -> EmailVerificationResponse:
        """Send email verification for admin user."""
        try:
            password_service = await self._get_password_reset_service()
            keycloak_config = await self._get_keycloak_config()
            
            result = await password_service.send_verify_email(
                user_id=request.user_id,
                realm_name=keycloak_config.realm_name,
            )
            
            logger.info(f"Email verification sent for admin user: {request.user_id}")
            
            return EmailVerificationResponse(
                message=result.message,
                success=result.success,
            )
            
        except Exception as e:
            logger.error(f"Failed to send email verification for {request.user_id}: {e}")
            raise AuthenticationError("Email verification service temporarily unavailable")
    
    async def send_required_actions(self, request: SendRequiredActionsRequest) -> RequiredActionsResponse:
        """Send required actions email for admin user."""
        try:
            password_service = await self._get_password_reset_service()
            keycloak_config = await self._get_keycloak_config()
            
            result = await password_service.send_required_actions_email(
                user_id=request.user_id,
                realm_name=keycloak_config.realm_name,
                actions=request.actions,
                redirect_uri=request.redirect_uri,
                client_id=keycloak_config.client_id,
            )
            
            logger.info(f"Required actions sent for admin user {request.user_id}: {request.actions}")
            
            return RequiredActionsResponse(
                message=result.message,
                success=result.success,
                actions=request.actions,
            )
            
        except Exception as e:
            logger.error(f"Failed to send required actions for {request.user_id}: {e}")
            raise AuthenticationError("Required actions service temporarily unavailable")
    
    async def get_user_credentials(self, user_id: str) -> UserCredentialsResponse:
        """Get user credentials information for MFA/OTP management."""
        try:
            password_service = await self._get_password_reset_service()
            keycloak_config = await self._get_keycloak_config()
            
            result = await password_service.get_user_credentials(
                user_id=user_id,
                realm_name=keycloak_config.realm_name,
            )
            
            logger.info(f"Retrieved credentials for admin user: {user_id}")
            
            return UserCredentialsResponse(
                success=result["success"],
                user_id=result["user_id"],
                credentials=result["credentials"]
            )
            
        except Exception as e:
            logger.error(f"Failed to get credentials for {user_id}: {e}")
            raise AuthenticationError("Credentials service temporarily unavailable")
    
    async def remove_user_totp(self, request: RemoveTOTPRequest) -> RemoveTOTPResponse:
        """Remove TOTP/OTP from admin user account."""
        try:
            password_service = await self._get_password_reset_service()
            keycloak_config = await self._get_keycloak_config()
            
            result = await password_service.remove_totp(
                user_id=request.user_id,
                realm_name=keycloak_config.realm_name,
            )
            
            logger.info(f"TOTP removed for admin user: {request.user_id}")
            
            return RemoveTOTPResponse(
                message=result.message,
                success=result.success,
            )
            
        except Exception as e:
            logger.error(f"Failed to remove TOTP for {request.user_id}: {e}")
            raise AuthenticationError("TOTP service temporarily unavailable")