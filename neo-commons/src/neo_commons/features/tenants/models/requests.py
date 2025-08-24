"""Tenant request models for API endpoints."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class TenantCreateRequest(BaseModel):
    """Request model for creating a new tenant."""
    
    organization_id: str = Field(..., description="Organization ID that owns this tenant")
    slug: str = Field(..., min_length=4, max_length=54, description="Tenant slug (URL-safe identifier)")
    name: str = Field(..., min_length=2, max_length=100, description="Tenant display name")
    description: Optional[str] = Field(None, max_length=500, description="Tenant description")
    custom_domain: Optional[str] = Field(None, description="Custom domain for tenant")
    deployment_type: Optional[str] = Field("schema", description="Deployment type (schema, database)")
    environment: Optional[str] = Field("production", description="Environment type")
    region_id: Optional[str] = Field(None, description="Preferred region ID")
    allow_impersonations: Optional[bool] = Field(False, description="Allow admin impersonations")
    features_enabled: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Enabled features")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        """Validate slug format."""
        import re
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        if '--' in v:
            raise ValueError('Slug cannot contain consecutive hyphens')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "organization_id": "01234567-89ab-cdef-0123-456789abcdef",
                "slug": "acme-corp",
                "name": "Acme Corporation",
                "description": "Leading provider of widgets and gadgets",
                "custom_domain": "acme.example.com",
                "features_enabled": {
                    "analytics": True,
                    "advanced_reporting": False
                }
            }
        }


class TenantUpdateRequest(BaseModel):
    """Request model for updating tenant information."""
    
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Tenant display name")
    description: Optional[str] = Field(None, max_length=500, description="Tenant description")
    custom_domain: Optional[str] = Field(None, description="Custom domain for tenant")
    allow_impersonations: Optional[bool] = Field(None, description="Allow admin impersonations")
    features_enabled: Optional[Dict[str, Any]] = Field(None, description="Enabled features")
    feature_overrides: Optional[Dict[str, Any]] = Field(None, description="Feature overrides")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Acme Corporation - Updated",
                "description": "Updated description",
                "features_enabled": {
                    "analytics": True,
                    "advanced_reporting": True
                }
            }
        }


class TenantProvisionRequest(BaseModel):
    """Request model for tenant provisioning operations."""
    
    provision_database: Optional[bool] = Field(True, description="Provision database schema")
    provision_keycloak: Optional[bool] = Field(True, description="Provision Keycloak realm")
    initial_admin_user: Optional[Dict[str, str]] = Field(None, description="Initial admin user details")
    template_name: Optional[str] = Field(None, description="Configuration template to apply")
    provisioning_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional provisioning options")
    
    class Config:
        schema_extra = {
            "example": {
                "provision_database": True,
                "provision_keycloak": True,
                "initial_admin_user": {
                    "email": "admin@acme.com",
                    "first_name": "Admin",
                    "last_name": "User"
                },
                "template_name": "enterprise_template"
            }
        }


class TenantConfigRequest(BaseModel):
    """Request model for tenant configuration operations."""
    
    configs: Dict[str, Any] = Field(..., description="Configuration key-value pairs")
    namespace: Optional[str] = Field(None, description="Configuration namespace")
    merge_existing: Optional[bool] = Field(True, description="Merge with existing configurations")
    
    class Config:
        schema_extra = {
            "example": {
                "configs": {
                    "max_users": 100,
                    "features.analytics": True,
                    "ui.theme": "dark",
                    "integrations.slack_webhook": "https://hooks.slack.com/..."
                },
                "namespace": "app_settings",
                "merge_existing": True
            }
        }