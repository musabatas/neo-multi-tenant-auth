"""
Authentication API endpoints for platform administrators.
"""
from typing import Optional, Dict, Any
from fastapi import Depends, Request, Response, status
from src.common.routers.base import NeoAPIRouter
from fastapi.security import HTTPAuthorizationCredentials
from loguru import logger

from neo_commons.auth.decorators import require_permission as require_permission_decorator
from ..dependencies import security, require_permission

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
    UserProfile
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
            remember_me=request.remember_me
        )
        
        # Extract Keycloak data for flattened fields
        keycloak_data = result["user"].get("keycloak", {})
        
        # Map to response model with complete user profile using flattened structure
        login_response = LoginResponse(
            access_token=result["tokens"]["access_token"],
            refresh_token=result["tokens"]["refresh_token"],
            token_type=result["tokens"]["token_type"],
            expires_in=result["expires_in"],
            refresh_expires_in=result.get("refresh_expires_in"),
            session_id=result["session_id"],
            user=UserProfile(
                id=result["user"]["id"],
                email=result["user"]["email"],
                username=result["user"]["username"],
                first_name=result["user"].get("first_name"),
                last_name=result["user"].get("last_name"),
                display_name=result["user"].get("display_name"),
                full_name=result["user"].get("full_name"),
                avatar_url=result["user"].get("avatar_url"),
                phone=result["user"].get("phone"),
                job_title=result["user"].get("job_title"),
                company=result["user"].get("company"),
                departments=result["user"].get("departments", []),
                timezone=result["user"].get("timezone", "UTC"),
                locale=result["user"].get("locale", "en-US"),
                language=result["user"].get("language", "en"),
                notification_preferences=result["user"].get("notification_preferences", {}),
                ui_preferences=result["user"].get("ui_preferences", {}),
                is_onboarding_completed=result["user"].get("is_onboarding_completed", False),
                profile_completion_percentage=result["user"].get("profile_completion_percentage", 0),
                is_active=result["user"].get("is_active", True),
                is_superadmin=result["user"].get("is_superadmin", False),
                roles=result["user"].get("roles", []),
                permissions=result["user"].get("permissions", []),
                tenants=result["user"].get("tenants", []),
                last_login_at=result["user"].get("last_login_at"),
                created_at=result["user"].get("created_at"),
                updated_at=result["user"].get("updated_at"),
                external_auth_provider=result["user"].get("external_auth_provider"),
                external_user_id=result["user"].get("external_user_id"),
                # Flattened Keycloak fields
                session_id=keycloak_data.get("session_id"),
                realm=keycloak_data.get("realm"),
                email_verified=keycloak_data.get("email_verified", False),
                authorized_party=keycloak_data.get("authorized_party")
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
        
        # Reduce frequent login logging
        
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
@require_permission_decorator("auth:logout", scope="platform", description="Logout from platform")
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
@require_permission_decorator("users:read_self", scope="platform", description="View own user profile")
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
        # Use shared method from AuthService with database lookup
        user_profile = await auth_service.get_current_user(
            access_token=access_token,
            use_cache=True
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
@require_permission_decorator("users:update_self", scope="platform", description="Change own password")
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
@require_permission_decorator("auth:reset_password", scope="platform", description="Reset password with token")
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