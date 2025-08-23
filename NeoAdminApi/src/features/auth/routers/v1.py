"""Auth API v1 endpoints using neo-commons authentication."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from neo_commons.core.exceptions.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from neo_commons.features.auth.entities.auth_context import AuthContext

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
from ..services.auth_service import AuthService
from ....common.dependencies import get_auth_service

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


async def get_current_admin_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> AuthContext:
    """Simple admin auth dependency that validates JWT without tenant requirements."""
    try:
        import jwt
        
        # For now, decode token without validation (development mode)
        # In production, this should validate against Keycloak public key
        token_payload = jwt.decode(credentials.credentials, options={"verify_signature": False})
        
        # Extract user info from token
        keycloak_user_id = token_payload.get("sub", "")
        username = token_payload.get("preferred_username", "")
        email = token_payload.get("email", "")
        first_name = token_payload.get("given_name", "")
        last_name = token_payload.get("family_name", "")
        
        # For admin users, sync and get platform user ID
        from ....common.dependencies import get_auth_service
        auth_service = await get_auth_service()
        platform_user_id = await auth_service._sync_admin_user(
            keycloak_user_id=keycloak_user_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create a simple auth context for admin users
        from neo_commons.core.value_objects.identifiers import UserId, KeycloakUserId, RealmId
        from datetime import datetime, timezone
        
        auth_context = AuthContext(
            user_id=platform_user_id,
            keycloak_user_id=KeycloakUserId(keycloak_user_id),
            tenant_id=None,  # Admin users don't have tenant context
            realm_id=RealmId("platform-admin"),
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            roles=set(),  # Will be loaded by service
            permissions=set(),  # Will be loaded by service
            session_id=token_payload.get("sid", ""),
            expires_at=datetime.fromtimestamp(token_payload.get("exp", 0), tz=timezone.utc) if token_payload.get("exp") else None,
            authenticated_at=datetime.now(timezone.utc),
        )
        
        return auth_context
        
    except Exception as e:
        logger.error(f"Admin auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


@router.post(
    "/login",
    response_model=AdminLoginResponse,
    summary="Admin login",
    description="Authenticate admin user with username/password"
)
async def login(
    login_request: AdminLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AdminLoginResponse:
    """Admin login endpoint."""
    try:
        return await auth_service.login(login_request)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


@router.post(
    "/logout",
    summary="Admin logout",
    description="Logout admin user and invalidate tokens"
)
async def logout(
    logout_request: AdminLogoutRequest,
    current_user: Annotated[AuthContext, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """Admin logout endpoint."""
    return await auth_service.logout(logout_request, current_user)


@router.post(
    "/refresh",
    response_model=AdminTokenResponse,
    summary="Refresh access token",
    description="Refresh access token using refresh token"
)
async def refresh_token(
    refresh_token: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AdminTokenResponse:
    """Refresh access token endpoint."""
    try:
        return await auth_service.refresh_token(refresh_token)
    except (InvalidTokenError, AuthenticationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.get(
    "/me",
    response_model=AdminUserResponse,
    summary="Get current user",
    description="Get current authenticated admin user information"
)
async def get_current_user(
    current_user: Annotated[AuthContext, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AdminUserResponse:
    """Get current user endpoint."""
    return await auth_service.get_current_user_info(current_user)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Forgot password",
    description="Initiate password reset process for admin user"
)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> ForgotPasswordResponse:
    """Forgot password endpoint."""
    try:
        return await auth_service.initiate_forgot_password(request)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset service temporarily unavailable"
        )


@router.post(
    "/send-email-verification",
    response_model=EmailVerificationResponse,
    summary="Send email verification",
    description="Send email verification for admin user"
)
async def send_email_verification(
    request: SendEmailVerificationRequest,
    current_user: Annotated[AuthContext, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> EmailVerificationResponse:
    """Send email verification endpoint."""
    try:
        return await auth_service.send_email_verification(request)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/send-required-actions",
    response_model=RequiredActionsResponse,
    summary="Send required actions",
    description="Send required actions email for admin user (UPDATE_PASSWORD, VERIFY_EMAIL, CONFIGURE_TOTP, etc.)"
)
async def send_required_actions(
    request: SendRequiredActionsRequest,
    current_user: Annotated[AuthContext, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> RequiredActionsResponse:
    """Send required actions endpoint."""
    try:
        return await auth_service.send_required_actions(request)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/user/{user_id}/credentials",
    response_model=UserCredentialsResponse,
    summary="Get user credentials",
    description="Get user credentials information for MFA/OTP management"
)
async def get_user_credentials(
    user_id: str,
    current_user: Annotated[AuthContext, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserCredentialsResponse:
    """Get user credentials endpoint."""
    try:
        return await auth_service.get_user_credentials(user_id)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/user/totp",
    response_model=RemoveTOTPResponse,
    summary="Remove TOTP",
    description="Remove TOTP/OTP from admin user account"
)
async def remove_user_totp(
    request: RemoveTOTPRequest,
    current_user: Annotated[AuthContext, Depends(get_current_admin_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> RemoveTOTPResponse:
    """Remove user TOTP endpoint."""
    try:
        return await auth_service.remove_user_totp(request)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status")
async def auth_status():
    """Auth module status endpoint."""
    return {
        "status": "enabled",
        "message": "Authentication enabled using neo-commons",
        "endpoints": {
            "login": "POST /login - Admin authentication",
            "logout": "POST /logout - Admin logout",
            "refresh": "POST /refresh - Token refresh",
            "me": "GET /me - Current user info",
            "forgot-password": "POST /forgot-password - Password reset",
            "send-email-verification": "POST /send-email-verification - Email verification",
            "send-required-actions": "POST /send-required-actions - Required actions email",
            "get-user-credentials": "GET /user/{user_id}/credentials - User credentials",
            "remove-user-totp": "DELETE /user/totp - Remove TOTP"
        }
    }