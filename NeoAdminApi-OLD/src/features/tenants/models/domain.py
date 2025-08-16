"""
Domain models for tenant management.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class DeploymentType(str, Enum):
    """Tenant deployment types."""
    SCHEMA = "schema"  # Shared database with schema isolation
    DATABASE = "database"  # Dedicated database
    HYBRID = "hybrid"  # Mixed approach


class EnvironmentType(str, Enum):
    """Tenant environment types."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TESTING = "testing"


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""
    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    DELETED = "deleted"


class AuthProvider(str, Enum):
    """Authentication providers."""
    KEYCLOAK = "keycloak"
    AUTH0 = "auth0"
    COGNITO = "cognito"
    OKTA = "okta"
    CUSTOM = "custom"


class Tenant(BaseModel):
    """Tenant domain model."""
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    id: UUID
    organization_id: UUID
    slug: str = Field(..., min_length=2, max_length=54, 
                     pattern=r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Database configuration
    schema_name: str = Field(..., min_length=1, max_length=63,
                            pattern=r'^[a-z][a-z0-9_]*$')
    database_name: Optional[str] = Field(None, max_length=63)
    deployment_type: DeploymentType = DeploymentType.SCHEMA
    environment: EnvironmentType = EnvironmentType.PRODUCTION
    
    # Regional configuration
    region_id: Optional[UUID] = None
    database_connection_id: Optional[UUID] = None
    custom_domain: Optional[str] = Field(None, max_length=253)
    
    # Authentication configuration
    external_auth_provider: AuthProvider
    external_auth_realm: str = Field(..., min_length=1, max_length=100)
    external_user_id: str = Field(..., min_length=1, max_length=255)
    external_auth_metadata: Dict[str, Any] = Field(default_factory=dict)
    allow_impersonations: bool = False
    
    # Status and lifecycle
    status: TenantStatus = TenantStatus.PENDING
    provisioned_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    
    # Features and configuration
    features_enabled: Dict[str, bool] = Field(default_factory=dict)
    feature_overrides: Dict[str, Any] = Field(default_factory=dict)
    internal_notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE
    
    @property
    def is_deleted(self) -> bool:
        """Check if tenant is soft deleted."""
        return self.deleted_at is not None
    
    @property
    def requires_provisioning(self) -> bool:
        """Check if tenant needs provisioning."""
        return self.status == TenantStatus.PENDING and self.provisioned_at is None


class TenantContact(BaseModel):
    """Tenant contact information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    user_id: UUID
    contact_type: str  # billing, technical, admin, support
    contact_info: Dict[str, Any] = Field(default_factory=dict)
    is_primary: bool = False
    receive_notifications: bool = True
    receive_billing_emails: bool = False
    receive_technical_alerts: bool = False
    receive_marketing_emails: bool = True
    emergency_phone: Optional[str] = None
    alternative_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime