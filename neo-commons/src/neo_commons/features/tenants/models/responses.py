"""Tenant response models for API endpoints."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class TenantResponse(BaseModel):
    """Response model for tenant information."""
    
    id: str = Field(..., description="Tenant ID")
    organization_id: str = Field(..., description="Organization ID")
    slug: str = Field(..., description="Tenant slug")
    name: str = Field(..., description="Tenant display name")
    description: Optional[str] = Field(None, description="Tenant description")
    schema_name: str = Field(..., description="Database schema name")
    database_name: Optional[str] = Field(None, description="Database name (if database-per-tenant)")
    custom_domain: Optional[str] = Field(None, description="Custom domain")
    deployment_type: str = Field(..., description="Deployment type")
    environment: str = Field(..., description="Environment type")
    region_id: Optional[str] = Field(None, description="Region ID")
    
    # External auth
    external_auth_provider: str = Field(..., description="External auth provider")
    external_auth_realm: str = Field(..., description="External auth realm")
    
    # Status and configuration
    allow_impersonations: bool = Field(..., description="Allow admin impersonations")
    status: str = Field(..., description="Tenant status")
    features_enabled: Dict[str, Any] = Field(..., description="Enabled features")
    
    # Activity tracking
    provisioned_at: Optional[datetime] = Field(None, description="Provisioning completion time")
    activated_at: Optional[datetime] = Field(None, description="Activation time")
    suspended_at: Optional[datetime] = Field(None, description="Suspension time")
    last_activity_at: Optional[datetime] = Field(None, description="Last activity time")
    
    # Metadata and audit
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    
    # Computed properties
    is_active: bool = Field(..., description="Is tenant active")
    is_suspended: bool = Field(..., description="Is tenant suspended")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "01234567-89ab-cdef-0123-456789abcdef",
                "organization_id": "01234567-89ab-cdef-0123-456789abcdef",
                "slug": "acme-corp",
                "name": "Acme Corporation",
                "description": "Leading provider of widgets",
                "schema_name": "tenant_acme_corp",
                "custom_domain": "acme.example.com",
                "deployment_type": "schema",
                "environment": "production",
                "external_auth_provider": "keycloak",
                "external_auth_realm": "tenant-acme-corp",
                "allow_impersonations": False,
                "status": "active",
                "features_enabled": {"analytics": True},
                "is_active": True,
                "is_suspended": False
            }
        }


class TenantListResponse(BaseModel):
    """Response model for tenant list operations."""
    
    tenants: List[TenantResponse] = Field(..., description="List of tenants")
    total: int = Field(..., description="Total number of tenants")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenants": [],
                "total": 25,
                "page": 1,
                "size": 10
            }
        }


class TenantStatusResponse(BaseModel):
    """Response model for tenant status operations."""
    
    id: str = Field(..., description="Tenant ID")
    slug: str = Field(..., description="Tenant slug")
    previous_status: str = Field(..., description="Previous status")
    current_status: str = Field(..., description="Current status")
    status_changed_at: datetime = Field(..., description="Status change timestamp")
    reason: Optional[str] = Field(None, description="Reason for status change")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "01234567-89ab-cdef-0123-456789abcdef",
                "slug": "acme-corp",
                "previous_status": "provisioning",
                "current_status": "active",
                "status_changed_at": "2024-08-24T19:30:00Z",
                "reason": "Provisioning completed successfully"
            }
        }


class TenantConfigResponse(BaseModel):
    """Response model for tenant configuration operations."""
    
    tenant_id: str = Field(..., description="Tenant ID")
    configs: Dict[str, Any] = Field(..., description="Configuration values")
    namespace: Optional[str] = Field(None, description="Configuration namespace")
    total_configs: int = Field(..., description="Total number of configurations")
    last_updated: Optional[datetime] = Field(None, description="Last configuration update")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "01234567-89ab-cdef-0123-456789abcdef",
                "configs": {
                    "max_users": 100,
                    "features.analytics": True,
                    "ui.theme": "dark"
                },
                "total_configs": 15,
                "last_updated": "2024-08-24T19:30:00Z"
            }
        }


class TenantHealthResponse(BaseModel):
    """Response model for tenant health check."""
    
    tenant_id: str = Field(..., description="Tenant ID")
    slug: str = Field(..., description="Tenant slug")
    status: str = Field(..., description="Tenant status")
    health_score: float = Field(..., description="Overall health score (0-100)")
    checks: Dict[str, Any] = Field(..., description="Individual health check results")
    last_activity_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    
    # Service health
    database_healthy: bool = Field(..., description="Database connectivity")
    cache_healthy: bool = Field(..., description="Cache connectivity")
    auth_healthy: bool = Field(..., description="Authentication service")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "01234567-89ab-cdef-0123-456789abcdef",
                "slug": "acme-corp",
                "status": "active",
                "health_score": 95.5,
                "checks": {
                    "database": {"status": "healthy", "response_time_ms": 5},
                    "cache": {"status": "healthy", "hit_rate": 0.85},
                    "auth": {"status": "healthy", "realm_active": True}
                },
                "database_healthy": True,
                "cache_healthy": True,
                "auth_healthy": True
            }
        }