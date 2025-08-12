"""
Authentication API endpoints for platform administrators.
"""
from typing import Optional, Dict, Any
from fastapi import Depends, Request, Response, status
from src.common.routers.base import NeoAPIRouter
from fastapi.security import HTTPAuthorizationCredentials
from loguru import logger

from ..decorators import require_permission
from ..dependencies import security

from src.common.models.base import APIResponse
from src.common.exceptions.base import UnauthorizedError, ForbiddenError
from ..models.request import (
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from ..models.response import (
    LoginResponse,
    TokenResponse,
    LogoutResponse,
    UserProfile,
    KeycloakUserData
)
from ..services.auth_service import AuthService
from ..services.permission_service import PermissionService

router = NeoAPIRouter()


@router.post(
    "/login",
    response_model=APIResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="Login to platform",
    description="Authenticate platform administrator and obtain access tokens"
)
async def login(
    request: LoginRequest,
    response: Response
) -> APIResponse[LoginResponse]:
    """
    Login endpoint for platform administrators.
    
    Returns access token, refresh token, and user information.
    """
    auth_service = AuthService()
    
    try:
        # Authenticate user
        result = await auth_service.authenticate(
            username=request.username,
            password=request.password,
            tenant_id=request.tenant_id,
            remember_me=request.remember_me
        )
        
        # Prepare Keycloak data
        keycloak_data = None
        if "keycloak" in result["user"]:
            keycloak_raw = result["user"]["keycloak"]
            keycloak_data = KeycloakUserData(
                session_id=keycloak_raw.get("session_id"),
                realm=keycloak_raw.get("realm"),
                email_verified=keycloak_raw.get("email_verified", False),
                scopes=keycloak_raw.get("scopes", []),
                realm_roles=keycloak_raw.get("realm_roles", []),
                client_roles=keycloak_raw.get("client_roles", {}),
                authorized_party=keycloak_raw.get("authorized_party"),
                auth_context_class=keycloak_raw.get("auth_context_class"),
                full_name=keycloak_raw.get("full_name")
            )
        
        # Map to response model
        login_response = LoginResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            session_id=result["session_id"],
            user=UserProfile(
                id=result["user"]["id"],
                email=result["user"]["email"],
                username=result["user"]["username"],
                first_name=result["user"]["first_name"],
                last_name=result["user"]["last_name"],
                display_name=result["user"]["display_name"],
                is_superadmin=result["user"]["is_superadmin"],
                avatar_url=result["user"]["avatar_url"],
                timezone=result["user"].get("timezone"),
                language=result["user"].get("language"),
                roles=result["user"]["roles"],
                permissions=result["user"]["permissions"],
                tenants=result["user"]["tenants"],
                keycloak=keycloak_data
            )
        )
        
        # Set secure cookie for refresh token (optional)
        if request.remember_me:
            response.set_cookie(
                key="refresh_token",
                value=result["refresh_token"],
                max_age=604800,  # 7 days
                httponly=True,
                secure=True,
                samesite="strict"
            )
        
        logger.info(f"User {result['user']['id']} logged in successfully")
        
        return APIResponse.success_response(
            message="Login successful",
            data=login_response
        )
        
    except UnauthorizedError as e:
        logger.warning(f"Login failed: {e.message}")
        raise
    except ForbiddenError as e:
        logger.warning(f"Login forbidden: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise UnauthorizedError("Authentication failed")


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange refresh token for new access token"
)
async def refresh_token(
    request: RefreshTokenRequest
) -> APIResponse[TokenResponse]:
    """
    Refresh access token using refresh token.
    """
    auth_service = AuthService()
    
    try:
        result = await auth_service.refresh_token(
            refresh_token=request.refresh_token
        )
        
        token_response = TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"]
        )
        
        return APIResponse.success_response(
            message="Token refreshed successfully",
            data=token_response
        )
        
    except UnauthorizedError as e:
        logger.warning(f"Token refresh failed: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise UnauthorizedError("Token refresh failed")


@router.post(
    "/logout",
    response_model=APIResponse[LogoutResponse],
    status_code=status.HTTP_200_OK,
    summary="Logout from platform",
    description="Invalidate current session and optionally all sessions"
)
@require_permission("auth:logout", scope="platform", description="Logout from platform")
async def logout(
    request: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    response: Response = None
) -> APIResponse[LogoutResponse]:
    """
    Logout endpoint for platform administrators.
    """
    auth_service = AuthService()
    
    # Extract access token
    access_token = credentials.credentials
    
    # Perform logout
    success = await auth_service.logout(
        access_token=access_token,
        refresh_token=request.refresh_token,
        everywhere=request.everywhere
    )
    
    # Clear refresh token cookie if exists
    if response:
        response.delete_cookie(key="refresh_token")
    
    logout_response = LogoutResponse(
        success=success,
        message="Logged out successfully" if success else "Logout completed"
    )
    
    return APIResponse.success_response(
        message=logout_response.message,
        data=logout_response
    )


@router.get(
    "/me",
    response_model=APIResponse[UserProfile],
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get current authenticated user information"
)
@require_permission("users:read_self", scope="platform", description="View own user profile")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[UserProfile]:
    """
    Get current user information from token.
    """
    auth_service = AuthService()
    
    # Extract access token
    access_token = credentials.credentials
    
    try:
        # Get user info
        user_info = await auth_service.get_current_user(
            access_token=access_token,
            use_cache=True
        )
        
        # Prepare Keycloak data for /me endpoint
        keycloak_data = None
        if "keycloak" in user_info:
            keycloak_raw = user_info["keycloak"]
            keycloak_data = KeycloakUserData(
                session_id=keycloak_raw.get("session_id"),
                realm=keycloak_raw.get("realm"),
                email_verified=keycloak_raw.get("email_verified", False),
                scopes=keycloak_raw.get("scopes", []),
                realm_roles=keycloak_raw.get("realm_roles", []),
                client_roles=keycloak_raw.get("client_roles", {}),
                authorized_party=keycloak_raw.get("authorized_party"),
                auth_context_class=keycloak_raw.get("auth_context_class"),
                full_name=keycloak_raw.get("full_name")
            )
        
        # Map to response model
        user_profile = UserProfile(
            id=user_info["id"],
            email=user_info["email"],
            username=user_info["username"],
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            display_name=user_info["display_name"],
            is_superadmin=user_info.get("is_superadmin", False),
            avatar_url=user_info["avatar_url"],
            timezone=user_info.get("timezone"),
            language=user_info.get("language"),
            roles=user_info["roles"],
            permissions=user_info["permissions"],
            tenants=user_info["tenants"],
            keycloak=keycloak_data
        )
        
        return APIResponse.success_response(
            message="User retrieved successfully",
            data=user_profile
        )
        
    except UnauthorizedError as e:
        logger.warning(f"Get current user failed: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise UnauthorizedError("Failed to get user information")


@router.post(
    "/change-password",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change current user's password"
)
@require_permission("users:update_self", scope="platform", description="Change own password")
async def change_password(
    request: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[Dict[str, Any]]:
    """
    Change password for current user.
    
    Note: This is a placeholder. Full implementation requires Keycloak Admin API.
    """
    # Extract access token
    access_token = credentials.credentials
    
    # TODO: Implement password change through Keycloak Admin API
    # This requires:
    # 1. Validate current password
    # 2. Update password in Keycloak
    # 3. Optionally invalidate all sessions
    
    return APIResponse.success_response(
        message="Password change feature coming soon",
        data={"status": "not_implemented"}
    )


@router.post(
    "/forgot-password",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Send password reset email"
)
async def forgot_password(
    request: ForgotPasswordRequest
) -> APIResponse[Dict[str, Any]]:
    """
    Request password reset email.
    
    Note: This is a placeholder. Full implementation requires email service.
    """
    # TODO: Implement forgot password flow
    # This requires:
    # 1. Verify email exists
    # 2. Generate reset token
    # 3. Send email with reset link
    
    # Always return success for security (don't reveal if email exists)
    return APIResponse.success_response(
        message="If the email exists, a password reset link has been sent",
        data={"email_sent": True}
    )


@router.post(
    "/reset-password",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Reset password",
    description="Reset password using token from email"
)
@require_permission("auth:reset_password", scope="platform", description="Reset password with token")
async def reset_password(
    request: ResetPasswordRequest
) -> APIResponse[Dict[str, Any]]:
    """
    Reset password using token.
    
    Note: This is a placeholder. Full implementation requires token validation.
    """
    # TODO: Implement password reset
    # This requires:
    # 1. Validate reset token
    # 2. Update password in Keycloak
    # 3. Invalidate reset token
    
    return APIResponse.success_response(
        message="Password reset feature coming soon",
        data={"status": "not_implemented"}
    )