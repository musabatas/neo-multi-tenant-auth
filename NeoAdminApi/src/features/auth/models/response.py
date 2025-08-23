"""Auth response models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from neo_commons.features.auth.entities.auth_context import AuthContext


class AdminUserResponse(BaseModel):
    """Response model for admin user information with comprehensive user data."""
    
    # Core Identity
    user_id: UUID = Field(..., description="User ID")
    keycloak_user_id: UUID = Field(..., description="Keycloak user ID") 
    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username")
    
    # External Auth
    external_user_id: str = Field(..., description="External user ID")
    external_auth_provider: str = Field(..., description="External auth provider")
    
    # Profile Information
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    phone: Optional[str] = Field(None, description="Phone number")
    job_title: Optional[str] = Field(None, description="Job title")
    
    # Localization
    timezone: str = Field(default="UTC", description="User timezone")
    locale: str = Field(default="en-US", description="User locale")
    
    # Status
    status: str = Field(..., description="User status")
    
    # Organizational
    departments: List[str] = Field(default_factory=list, description="User departments")
    company: Optional[str] = Field(None, description="Company name")
    manager_id: Optional[UUID] = Field(None, description="Manager ID")
    
    # Role and Access
    default_role_level: str = Field(default="member", description="Default role level")
    is_system_user: bool = Field(default=False, description="Is system user")
    
    # Onboarding and Profile
    is_onboarding_completed: bool = Field(default=False, description="Onboarding completed")
    profile_completion_percentage: int = Field(default=0, description="Profile completion percentage")
    
    # Preferences
    notification_preferences: Dict[str, Any] = Field(default_factory=dict, description="Notification preferences")
    ui_preferences: Dict[str, Any] = Field(default_factory=dict, description="UI preferences")
    feature_flags: Dict[str, Any] = Field(default_factory=dict, description="Feature flags")
    
    # Tags and Custom Fields
    tags: List[str] = Field(default_factory=list, description="User tags")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom fields")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="User metadata")
    
    # Activity Tracking
    invited_at: Optional[datetime] = Field(None, description="Invitation timestamp")
    activated_at: Optional[datetime] = Field(None, description="Activation timestamp")
    last_activity_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    # Audit Fields
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    authenticated_at: datetime = Field(..., description="Authentication timestamp")
    
    # RBAC Data
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[Dict[str, Any]] = Field(default_factory=list, description="User permissions with metadata")
    
    @classmethod
    def from_auth_context(cls, context: AuthContext) -> "AdminUserResponse":
        """Create response from neo-commons auth context (simple permissions)."""
        return cls(
            user_id=UUID(context.user_id.value),
            keycloak_user_id=UUID(context.keycloak_user_id.value),
            email=context.email,
            username=context.username,
            external_user_id=context.keycloak_user_id.value,  # Use Keycloak ID as external ID
            external_auth_provider="keycloak",  # Default provider
            first_name=context.first_name,
            last_name=context.last_name,
            display_name=context.display_name,
            status="active",  # Default status
            roles=[role.value for role in context.roles],
            permissions=[{'code': perm.value} for perm in context.permissions],
            authenticated_at=context.authenticated_at,
        )
    
    @classmethod
    def from_auth_context_with_user_data(
        cls, 
        context: AuthContext, 
        user_data: Dict[str, Any],
        permissions_data: List[Dict[str, Any]]
    ) -> "AdminUserResponse":
        """Create response from auth context with comprehensive user data and permissions."""
        return cls(
            # Core Identity
            user_id=UUID(context.user_id.value),
            keycloak_user_id=UUID(context.keycloak_user_id.value),
            email=user_data.get("email", context.email),
            username=user_data.get("username", context.username),
            
            # External Auth
            external_user_id=user_data.get("external_user_id", ""),
            external_auth_provider=user_data.get("external_auth_provider", "keycloak"),
            
            # Profile Information
            first_name=user_data.get("first_name", context.first_name),
            last_name=user_data.get("last_name", context.last_name),
            display_name=user_data.get("display_name", context.display_name),
            avatar_url=user_data.get("avatar_url"),
            phone=user_data.get("phone"),
            job_title=user_data.get("job_title"),
            
            # Localization
            timezone=user_data.get("timezone", "UTC"),
            locale=user_data.get("locale", "en-US"),
            
            # Status
            status=user_data.get("status", "active"),
            
            # Organizational
            departments=user_data.get("departments", []),
            company=user_data.get("company"),
            manager_id=UUID(user_data["manager_id"]) if user_data.get("manager_id") else None,
            
            # Role and Access
            default_role_level=user_data.get("default_role_level", "member"),
            is_system_user=user_data.get("is_system_user", False),
            
            # Onboarding and Profile
            is_onboarding_completed=user_data.get("is_onboarding_completed", False),
            profile_completion_percentage=user_data.get("profile_completion_percentage", 0),
            
            # Preferences
            notification_preferences=user_data.get("notification_preferences", {}),
            ui_preferences=user_data.get("ui_preferences", {}),
            feature_flags=user_data.get("feature_flags", {}),
            
            # Tags and Custom Fields
            tags=user_data.get("tags", []),
            custom_fields=user_data.get("custom_fields", {}),
            metadata=user_data.get("metadata", {}),
            
            # Activity Tracking
            invited_at=user_data.get("invited_at"),
            activated_at=user_data.get("activated_at"),
            last_activity_at=user_data.get("last_activity_at"),
            last_login_at=user_data.get("last_login_at"),
            
            # Audit Fields
            created_at=user_data.get("created_at"),
            updated_at=user_data.get("updated_at"),
            authenticated_at=context.authenticated_at,
            
            # RBAC Data
            roles=[role.value for role in context.roles],
            permissions=permissions_data,
        )


class AdminTokenResponse(BaseModel):
    """Response model for authentication tokens."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    refresh_expires_in: Optional[int] = Field(None, description="Refresh token expiry")


class AdminLoginResponse(BaseModel):
    """Response model for admin login."""
    
    tokens: AdminTokenResponse = Field(..., description="Authentication tokens")
    user: AdminUserResponse = Field(..., description="User information")
    session_id: Optional[str] = Field(None, description="Session ID")
    message: str = Field("Login successful", description="Success message")


class ForgotPasswordResponse(BaseModel):
    """Response model for forgot password."""
    
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")
    reset_token_sent: bool = Field(..., description="Whether reset token was sent")
    expires_in: Optional[int] = Field(None, description="Token expiry in seconds")


class EmailVerificationResponse(BaseModel):
    """Response model for email verification."""
    
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")


class RequiredActionsResponse(BaseModel):
    """Response model for required actions email."""
    
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")
    actions: List[str] = Field(..., description="Actions that were sent")


class UserCredentialsResponse(BaseModel):
    """Response model for user credentials information."""
    
    success: bool = Field(..., description="Operation success status")
    user_id: str = Field(..., description="User ID")
    credentials: List[Dict[str, Any]] = Field(..., description="User credentials information")


class RemoveTOTPResponse(BaseModel):
    """Response model for removing TOTP."""
    
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")