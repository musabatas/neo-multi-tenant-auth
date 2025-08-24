"""Authentication API response models."""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field

from ....core.value_objects.identifiers import UserId
from ..entities.auth_context import AuthContext


class TokenResponse(BaseModel):
    """Token response model."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    refresh_expires_in: Optional[int] = Field(None, description="Refresh token expiry in seconds")
    scope: Optional[str] = Field(None, description="Token scope")


class UserProfileResponse(BaseModel):
    """User profile response model with complete database schema."""
    
    # Core Identity
    user_id: str = Field(..., description="Platform user ID")
    keycloak_user_id: str = Field(..., description="Keycloak user ID")
    email: str = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Username")
    
    # External Auth
    external_user_id: Optional[str] = Field(None, description="External auth provider user ID")
    external_auth_provider: Optional[str] = Field(None, description="External auth provider")
    external_auth_metadata: Optional[Dict[str, Any]] = Field(None, description="External auth metadata")
    
    # Profile Information
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    phone: Optional[str] = Field(None, description="Phone number")
    job_title: Optional[str] = Field(None, description="Job title")
    
    # Localization
    timezone: Optional[str] = Field(None, description="User timezone")
    locale: Optional[str] = Field(None, description="User locale")
    
    # Status
    status: Optional[str] = Field(None, description="User status (active, inactive, suspended)")
    
    # Organizational
    departments: Optional[List[str]] = Field(None, description="User departments")
    company: Optional[str] = Field(None, description="Company name")
    manager_id: Optional[str] = Field(None, description="Manager user ID")
    
    # Role and Access
    default_role_level: Optional[str] = Field(None, description="Default role level")
    is_system_user: Optional[bool] = Field(None, description="System user flag")
    
    # Onboarding and Profile
    is_onboarding_completed: Optional[bool] = Field(None, description="Onboarding completion status")
    profile_completion_percentage: Optional[int] = Field(None, description="Profile completion percentage")
    
    # Preferences
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")
    ui_preferences: Optional[Dict[str, Any]] = Field(None, description="UI preferences")
    feature_flags: Optional[Dict[str, Any]] = Field(None, description="Feature flags")
    
    # Tags and Custom Fields
    tags: Optional[List[str]] = Field(None, description="User tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    # Activity Tracking
    invited_at: Optional[datetime] = Field(None, description="Invitation timestamp")
    activated_at: Optional[datetime] = Field(None, description="Account activation timestamp")
    last_activity_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    # Audit Fields
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    
    # Legacy/Compatibility Fields  
    email_verified: bool = Field(default=False, description="Email verification status")
    enabled: bool = Field(default=True, description="Account enabled status")
    
    # Authentication & Authorization
    roles: List[str] = Field(default_factory=list, description="User role codes")
    permissions: List[Union[str, Dict[str, Any]]] = Field(default_factory=list, description="User permissions (can be strings or rich permission objects)")
    session_id: Optional[str] = Field(None, description="Current session ID")

    @classmethod
    async def from_auth_context(
        cls, 
        auth_context: AuthContext, 
        schema_name: str = "admin",
        database_service = None
    ) -> "UserProfileResponse":
        """Create complete user profile from auth context with database data."""
        # Get rich permissions from auth context metadata
        permissions = auth_context.metadata.get('rich_permissions', [])
        if not permissions:
            # Fallback to simple permission codes if no rich permissions
            permissions = [perm.value for perm in auth_context.permissions]
        
        # Build base user profile from auth context
        user_profile_data = {
            "user_id": auth_context.user_id.value,
            "keycloak_user_id": auth_context.keycloak_user_id.value,
            "email": auth_context.email,
            "username": auth_context.username,
            "first_name": auth_context.first_name,
            "last_name": auth_context.last_name,
            "display_name": auth_context.display_name,
            "created_at": auth_context.authenticated_at,
            "roles": [role.value for role in auth_context.roles],
            "permissions": permissions,
            "session_id": auth_context.session_id,
        }
        
        # Try to get database service and fetch complete user data
        if database_service is None:
            try:
                from ...database.services.database_manager import DatabaseManager
                database_service = await DatabaseManager.get_instance()
            except Exception:
                # If database service creation fails, return basic profile
                return cls(**user_profile_data)
        
        try:
            # Import user service here to avoid circular imports
            from ...users.services.user_service import UserService
            from ...users.repositories.user_repository import UserRepository
            
            # Create user service with provided database service
            user_repository = UserRepository(database_service)
            user_service = UserService(user_repository)
            
            # Fetch complete user data
            complete_user_data = await user_service.get_complete_user_data(
                auth_context.user_id, 
                schema_name=schema_name
            )
            
            # If we have complete user data from database, merge it in
            if complete_user_data:
                # Merge database data, but keep auth context values for core identity
                for key, value in complete_user_data.items():
                    if key not in ["user_id", "keycloak_user_id", "email", "username", "roles", "permissions"]:
                        user_profile_data[key] = value
                        
                # Use database email if auth context email is missing
                if not user_profile_data.get("email") and complete_user_data.get("email"):
                    user_profile_data["email"] = complete_user_data["email"]
            else:
                # No database data found - try to sync user from auth context to database
                try:
                    # Sync user to database if not exists
                    await user_service.sync_keycloak_user(
                        external_user_id=auth_context.keycloak_user_id.value,
                        username=auth_context.username or "",
                        email=auth_context.email or "",
                        first_name=auth_context.first_name or "",
                        last_name=auth_context.last_name or "",
                        schema_name=schema_name
                    )
                    # Try to fetch data again after sync
                    complete_user_data = await user_service.get_complete_user_data(
                        auth_context.user_id, 
                        schema_name=schema_name
                    )
                    if complete_user_data:
                        for key, value in complete_user_data.items():
                            if key not in ["user_id", "keycloak_user_id", "roles", "permissions"]:
                                user_profile_data[key] = value
                except Exception as sync_error:
                    pass  # Continue with auth context data if sync fails
            
            return cls(**user_profile_data)
            
        except Exception as e:
            # Fall back to basic user profile from auth context
            return cls(**user_profile_data)


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