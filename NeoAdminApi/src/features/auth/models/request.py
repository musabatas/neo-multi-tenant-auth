"""Auth request models."""

from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr


class AdminLoginRequest(BaseModel):
    """Request model for admin user login."""
    
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class AdminLogoutRequest(BaseModel):
    """Request model for admin user logout."""
    
    refresh_token: Optional[str] = Field(None, description="Refresh token to invalidate")
    all_sessions: bool = Field(False, description="Logout from all sessions")


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""
    
    email: EmailStr = Field(..., description="Email address to send reset link")


class SendEmailVerificationRequest(BaseModel):
    """Request model for sending email verification."""
    
    user_id: str = Field(..., description="User ID to send verification email")


class SendRequiredActionsRequest(BaseModel):
    """Request model for sending required actions email."""
    
    user_id: str = Field(..., description="User ID to send required actions")
    actions: List[str] = Field(..., description="Required actions to send", 
                               example=["UPDATE_PASSWORD", "VERIFY_EMAIL", "CONFIGURE_TOTP"])
    redirect_uri: Optional[str] = Field(None, description="Redirect URI after completing actions")


class RemoveTOTPRequest(BaseModel):
    """Request model for removing TOTP from user."""
    
    user_id: str = Field(..., description="User ID to remove TOTP from")