"""
Authentication request models.
"""
from typing import Optional
from pydantic import Field, EmailStr, field_validator
import re

from src.common.models.base import BaseSchema


class LoginRequest(BaseSchema):
    """Login request model."""
    username: str = Field(..., min_length=3, max_length=50, description="Username or email")
    password: str = Field(..., min_length=8, max_length=100, description="Password")
    remember_me: bool = Field(False, description="Remember this session")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        # Allow email or alphanumeric username
        if '@' in v:
            # Validate as email
            EmailStr._validate(v)
        else:
            # Validate as username (alphanumeric, underscore, dash)
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username must be alphanumeric with optional underscores and dashes')
        return v.lower()


class RefreshTokenRequest(BaseSchema):
    """Refresh token request model."""
    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseSchema):
    """Logout request model."""
    refresh_token: Optional[str] = Field(None, description="Refresh token for complete logout")
    everywhere: bool = Field(False, description="Logout from all devices")


class ChangePasswordRequest(BaseSchema):
    """Change password request model."""
    current_password: str = Field(..., min_length=8, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Confirm new password")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


class ForgotPasswordRequest(BaseSchema):
    """Forgot password request model."""
    email: EmailStr = Field(..., description="Email address")


class ResetPasswordRequest(BaseSchema):
    """Reset password request model."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Confirm new password")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate that passwords match."""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


class VerifyEmailRequest(BaseSchema):
    """Email verification request model."""
    token: str = Field(..., description="Email verification token")


class ResendVerificationRequest(BaseSchema):
    """Resend verification email request model."""
    email: EmailStr = Field(..., description="Email address")