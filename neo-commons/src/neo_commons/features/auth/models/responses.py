"""Authentication API response models."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Token response model."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    refresh_expires_in: Optional[int] = Field(None, description="Refresh token expiry in seconds")
    scope: Optional[str] = Field(None, description="Token scope")


class UserProfileResponse(BaseModel):
    """User profile response model."""
    
    user_id: str = Field(..., description="Platform user ID")
    keycloak_user_id: str = Field(..., description="Keycloak user ID")
    tenant_id: str = Field(..., description="Tenant ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    display_name: Optional[str] = Field(None, description="Display name")
    email_verified: bool = Field(default=False, description="Email verification status")
    enabled: bool = Field(default=True, description="Account enabled status")
    created_at: Optional[datetime] = Field(None, description="Account creation date")
    last_login: Optional[datetime] = Field(None, description="Last login date")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")


class LoginResponse(BaseModel):
    """Login response model."""
    
    tokens: TokenResponse = Field(..., description="Authentication tokens")
    user: UserProfileResponse = Field(..., description="User profile")
    session_id: Optional[str] = Field(None, description="Session ID")
    message: str = Field(default="Login successful", description="Response message")


class RegisterResponse(BaseModel):
    """Registration response model."""
    
    user_id: str = Field(..., description="Created user ID")
    keycloak_user_id: str = Field(..., description="Keycloak user ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    email_verification_required: bool = Field(default=True, description="Email verification required")
    message: str = Field(default="Registration successful", description="Response message")


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Operation success")
    details: Optional[Dict] = Field(None, description="Additional details")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class PasswordResetResponse(BaseModel):
    """Password reset response."""
    
    message: str = Field(..., description="Response message")
    reset_token_sent: bool = Field(default=True, description="Reset token sent status")
    expires_in: Optional[int] = Field(None, description="Reset token expiry in seconds")


class SessionInfoResponse(BaseModel):
    """Session information response."""
    
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    tenant_id: str = Field(..., description="Tenant ID")
    authenticated_at: datetime = Field(..., description="Authentication timestamp")
    expires_at: Optional[datetime] = Field(None, description="Session expiry")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")


class UserValidationResponse(BaseModel):
    """User validation response."""
    
    valid: bool = Field(..., description="Validation result")
    user_exists: Optional[bool] = Field(None, description="User existence check")
    email_available: Optional[bool] = Field(None, description="Email availability")
    username_available: Optional[bool] = Field(None, description="Username availability")
    details: Optional[Dict] = Field(None, description="Validation details")