"""
Request models for tenant API endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import date
from uuid import UUID

from .domain import DeploymentType, EnvironmentType, TenantStatus, AuthProvider


class TenantCreate(BaseModel):
    """Request model for creating a new tenant."""
    
    organization_id: UUID = Field(..., description="Organization that owns this tenant")
    slug: str = Field(..., min_length=2, max_length=54, 
                     pattern=r'^[a-z0-9][a-z0-9-]*[a-z0-9]$',
                     description="URL-safe unique identifier")
    name: str = Field(..., min_length=1, max_length=255,
                     description="Display name for the tenant")
    description: Optional[str] = Field(None, max_length=1000,
                                      description="Tenant description")
    
    # Deployment configuration
    deployment_type: DeploymentType = Field(DeploymentType.SCHEMA,
                                           description="Database isolation strategy")
    environment: EnvironmentType = Field(EnvironmentType.PRODUCTION,
                                        description="Environment type")
    region_id: Optional[UUID] = Field(None, description="Target region for deployment")
    custom_domain: Optional[str] = Field(None, max_length=253,
                                        description="Custom domain for tenant")
    
    # Authentication configuration  
    external_auth_provider: AuthProvider = Field(AuthProvider.KEYCLOAK,
                                                description="Authentication provider")
    external_auth_realm: Optional[str] = Field(None, min_length=1, max_length=100,
                                              description="External auth realm name")
    allow_impersonations: bool = Field(False,
                                      description="Allow admin impersonation")
    
    # Features
    features_enabled: Dict[str, bool] = Field(default_factory=dict,
                                             description="Enabled feature flags")
    internal_notes: Optional[str] = Field(None, max_length=5000,
                                         description="Internal admin notes")
    metadata: Dict[str, Any] = Field(default_factory=dict,
                                    description="Additional metadata")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not v or not v.replace('-', '').isalnum():
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Slug cannot start or end with a hyphen")
        return v.lower()
    
    @field_validator('custom_domain')
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        """Validate domain format."""
        if v:
            # Basic domain validation
            if '..' in v or v.startswith('.') or v.endswith('.'):
                raise ValueError("Invalid domain format")
            if len(v) > 253:
                raise ValueError("Domain name too long")
        return v


class TenantUpdate(BaseModel):
    """Request model for updating a tenant."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    custom_domain: Optional[str] = Field(None, max_length=253)
    environment: Optional[EnvironmentType] = None
    allow_impersonations: Optional[bool] = None
    features_enabled: Optional[Dict[str, bool]] = None
    feature_overrides: Optional[Dict[str, Any]] = None
    internal_notes: Optional[str] = Field(None, max_length=5000)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('custom_domain')
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        """Validate domain format."""
        if v is not None and v != "":
            if '..' in v or v.startswith('.') or v.endswith('.'):
                raise ValueError("Invalid domain format")
            if len(v) > 253:
                raise ValueError("Domain name too long")
        return v


class TenantStatusUpdate(BaseModel):
    """Request model for updating tenant status."""
    
    status: TenantStatus = Field(..., description="New tenant status")
    reason: Optional[str] = Field(None, max_length=500,
                                 description="Reason for status change")
    suspend_until: Optional[date] = Field(None,
                                         description="Auto-reactivation date for suspension")
    
    @field_validator('status')
    @classmethod
    def validate_status_transition(cls, v: TenantStatus) -> TenantStatus:
        """Validate status transitions."""
        # Note: Actual transition validation should be done in service layer
        # based on current status
        if v == TenantStatus.DELETED:
            raise ValueError("Cannot directly set status to DELETED. Use delete endpoint.")
        return v


class TenantFilter(BaseModel):
    """Filter parameters for listing tenants."""
    
    organization_id: Optional[UUID] = Field(None, description="Filter by organization")
    status: Optional[List[TenantStatus]] = Field(None, description="Filter by status")
    environment: Optional[EnvironmentType] = Field(None, description="Filter by environment")
    region_id: Optional[UUID] = Field(None, description="Filter by region")
    deployment_type: Optional[DeploymentType] = Field(None, description="Filter by deployment type")
    external_auth_provider: Optional[AuthProvider] = Field(None, description="Filter by auth provider")
    search: Optional[str] = Field(None, min_length=1, max_length=100,
                                 description="Search in name, slug, description")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    has_custom_domain: Optional[bool] = Field(None, description="Filter by custom domain presence")
    created_after: Optional[date] = Field(None, description="Filter by creation date")
    created_before: Optional[date] = Field(None, description="Filter by creation date")


class TenantProvisionRequest(BaseModel):
    """Request model for provisioning a tenant."""
    
    subscription_plan_id: UUID = Field(..., description="Subscription plan for the tenant")
    initial_admin_email: str = Field(..., description="Email for initial admin user")
    initial_admin_username: Optional[str] = Field(None, description="Username for initial admin")
    send_welcome_email: bool = Field(True, description="Send welcome email to admin")
    create_sample_data: bool = Field(False, description="Create sample data for demo")
    
    @field_validator('initial_admin_email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError("Invalid email format")
        return v.lower()


class TenantContactCreate(BaseModel):
    """Request model for adding a tenant contact."""
    
    user_id: UUID = Field(..., description="Platform user ID")
    contact_type: str = Field(..., pattern=r'^(billing|technical|admin|support)$',
                            description="Type of contact")
    is_primary: bool = Field(False, description="Primary contact for this type")
    receive_notifications: bool = Field(True, description="Receive general notifications")
    receive_billing_emails: bool = Field(False, description="Receive billing emails")
    receive_technical_alerts: bool = Field(False, description="Receive technical alerts")
    receive_marketing_emails: bool = Field(True, description="Receive marketing emails")
    emergency_phone: Optional[str] = Field(None, max_length=20,
                                          description="Emergency contact phone")
    alternative_email: Optional[str] = Field(None, max_length=320,
                                            description="Alternative email address")
    contact_info: Dict[str, Any] = Field(default_factory=dict,
                                        description="Additional contact information")