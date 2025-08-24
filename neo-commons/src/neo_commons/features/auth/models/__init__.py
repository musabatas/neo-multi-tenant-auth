"""Authentication API models."""

from .admin_models import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLogoutRequest,
    AdminTokenResponse,
    AdminUserResponse,
    EmailVerificationResponse,
    RemoveTOTPRequest,
    RemoveTOTPResponse,
    RequiredActionsResponse,
    SendEmailVerificationRequest,
    SendRequiredActionsRequest,
    UserCredentialsResponse,
    create_admin_login_response,
    create_admin_user_response_from_context,
)
from .requests import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from .responses import (
    ErrorResponse,
    LoginResponse,
    MessageResponse,
    PasswordResetResponse,
    RegisterResponse,
    SessionInfoResponse,
    TokenResponse,
    UserProfileResponse,
    UserValidationResponse,
)

__all__ = [
    # Base Request models
    "LoginRequest",
    "RegisterRequest", 
    "RefreshTokenRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "LogoutRequest",
    "ChangePasswordRequest",
    
    # Base Response models
    "TokenResponse",
    "UserProfileResponse",
    "LoginResponse",
    "RegisterResponse", 
    "MessageResponse",
    "ErrorResponse",
    "PasswordResetResponse",
    "SessionInfoResponse",
    "UserValidationResponse",
    
    # Admin models
    "AdminLoginRequest",
    "AdminLoginResponse",
    "AdminLogoutRequest", 
    "AdminTokenResponse",
    "AdminUserResponse",
    "EmailVerificationResponse",
    "RemoveTOTPRequest",
    "RemoveTOTPResponse",
    "RequiredActionsResponse",
    "SendEmailVerificationRequest",
    "SendRequiredActionsRequest",
    "UserCredentialsResponse",
    "create_admin_login_response",
    "create_admin_user_response_from_context",
]