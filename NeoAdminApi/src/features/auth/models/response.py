"""
Authentication response models.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import Field

from src.common.models.base import BaseSchema


class PermissionDetail(BaseSchema):
    """Permission detail model."""
    code: str = Field(..., description="Permission code")
    resource: str = Field(..., description="Resource name")
    action: str = Field(..., description="Action name")
    scope_level: Optional[str] = Field(None, description="Scope level")
    is_dangerous: bool = Field(False, description="Is dangerous permission")
    requires_mfa: bool = Field(False, description="Requires MFA")
    requires_approval: bool = Field(False, description="Requires approval")
    config: Dict[str, Any] = Field(default_factory=dict, description="Permission configuration")
    source: Optional[str] = Field(None, description="Permission source")
    priority: int = Field(0, description="Permission priority")


class KeycloakUserData(BaseSchema):
    """Keycloak user data model."""
    session_id: Optional[str] = Field(None, description="Keycloak session ID")
    realm: Optional[str] = Field(None, description="Keycloak realm")
    email_verified: bool = Field(False, description="Email verification status from Keycloak")
    scopes: List[str] = Field(default_factory=list, description="OAuth scopes")
    realm_roles: List[str] = Field(default_factory=list, description="Keycloak realm roles")
    client_roles: Dict[str, List[str]] = Field(default_factory=dict, description="Keycloak client roles")
    authorized_party: Optional[str] = Field(None, description="OAuth authorized party")
    auth_context_class: Optional[str] = Field(None, description="Authentication Context Class Reference")
    full_name: Optional[str] = Field(None, description="Full name from Keycloak")


class TokenResponse(BaseSchema):
    """Token response model."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_expires_in: Optional[int] = Field(None, description="Refresh token expiry in seconds")
    scope: Optional[str] = Field(None, description="Token scope")


class UserProfile(BaseSchema):
    """User profile model."""
    id: str = Field(..., description="User unique identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    timezone: Optional[str] = Field(None, description="User timezone")
    language: Optional[str] = Field(None, description="Preferred language")
    is_superadmin: bool = Field(False, description="Is platform superadmin")
    roles: List[Dict[str, Any]] = Field(default_factory=list, description="User roles")
    permissions: Union[List[str], List[PermissionDetail]] = Field(default_factory=list, description="User permissions")
    tenants: List[Dict[str, Any]] = Field(default_factory=list, description="Accessible tenants")
    keycloak: Optional[KeycloakUserData] = Field(None, description="Keycloak user data")


class LoginResponse(BaseSchema):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    session_id: str = Field(..., description="Session identifier")
    user: UserProfile = Field(..., description="User profile")


class SessionInfo(BaseSchema):
    """Session information model."""
    session_id: str = Field(..., description="Session identifier")
    user_id: UUID = Field(..., description="User identifier")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiry time")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    is_active: bool = Field(True, description="Session active status")


class AuthStatus(BaseSchema):
    """Authentication status model."""
    is_authenticated: bool = Field(..., description="Authentication status")
    user: Optional[UserProfile] = Field(None, description="User profile if authenticated")
    session: Optional[SessionInfo] = Field(None, description="Session information")
    permissions: List[str] = Field(default_factory=list, description="Current permissions")
    roles: List[str] = Field(default_factory=list, description="Current roles")


class PasswordChangeResponse(BaseSchema):
    """Password change response model."""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    requires_relogin: bool = Field(False, description="Whether user needs to login again")


class PasswordResetResponse(BaseSchema):
    """Password reset response model."""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    email_sent: bool = Field(False, description="Whether email was sent")


class EmailVerificationResponse(BaseSchema):
    """Email verification response model."""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    email_verified: bool = Field(False, description="Email verification status")


class LogoutResponse(BaseSchema):
    """Logout response model."""
    success: bool = Field(..., description="Operation success")
    message: str = Field("Successfully logged out", description="Response message")
    sessions_terminated: int = Field(1, description="Number of sessions terminated")


class PermissionResponse(BaseSchema):
    """Permission response model."""
    id: int = Field(..., description="Permission ID")
    code: str = Field(..., description="Permission code")
    resource: str = Field(..., description="Resource name")
    action: str = Field(..., description="Action name")
    scope_level: str = Field(..., description="Scope level (platform/tenant)")
    description: Optional[str] = Field(None, description="Permission description")
    is_dangerous: bool = Field(False, description="Is dangerous permission")
    requires_mfa: bool = Field(False, description="Requires MFA")
    requires_approval: bool = Field(False, description="Requires approval")