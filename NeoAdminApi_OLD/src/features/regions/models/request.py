"""
Request models for regions API endpoints.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from .domain import ConnectionType


class DatabaseConnectionFilter(BaseModel):
    """Filter parameters for database connections."""
    region_id: Optional[str] = Field(None, description="Filter by region ID")
    connection_type: Optional[ConnectionType] = Field(None, description="Filter by connection type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_healthy: Optional[bool] = Field(None, description="Filter by health status")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    search: Optional[str] = Field(None, description="Search in connection name or database name")


class HealthCheckRequest(BaseModel):
    """Request to perform health check on databases."""
    connection_ids: Optional[List[str]] = Field(
        None, 
        description="Specific connection IDs to check. If empty, checks all active connections."
    )
    force_check: bool = Field(
        False,
        description="Force health check even if recently checked"
    )
    timeout_seconds: int = Field(
        5,
        description="Timeout for each health check",
        ge=1,
        le=30
    )


class RegionFilter(BaseModel):
    """Filter parameters for regions."""
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    accepts_new_tenants: Optional[bool] = Field(None, description="Filter by tenant acceptance")
    gdpr_region: Optional[bool] = Field(None, description="Filter by GDPR compliance")
    provider: Optional[str] = Field(None, description="Filter by cloud provider")
    continent: Optional[str] = Field(None, description="Filter by continent")
    search: Optional[str] = Field(None, description="Search in name, code, or display name")


class RegionCreate(BaseModel):
    """Request model for creating a region."""
    code: str = Field(..., description="Region code (e.g., us-east-1)")
    name: str = Field(..., description="Region name")
    display_name: str = Field(..., description="Display name for UI")
    country_code: str = Field(..., max_length=2, description="ISO country code")
    continent: str = Field(..., description="Continent name")
    city: Optional[str] = Field(None, description="City name")
    timezone: str = Field(..., description="Timezone (e.g., America/New_York)")
    coordinates: Optional[str] = Field(None, description="GPS coordinates")
    
    # Compliance
    data_residency_compliant: bool = Field(True, description="Data residency compliance")
    gdpr_region: bool = Field(False, description="GDPR region flag")
    compliance_certifications: List[str] = Field(default_factory=list, description="Compliance certs")
    
    # Infrastructure
    provider: str = Field("Docker", description="Cloud provider")
    provider_region: str = Field(..., description="Provider's region code")
    primary_endpoint: str = Field(..., description="Primary database endpoint")
    
    # Capacity
    max_tenants: Optional[int] = Field(None, description="Maximum tenants allowed")
    accepts_new_tenants: bool = Field(True, description="Accept new tenants")
    priority: int = Field(0, description="Region priority for tenant placement")


class RegionUpdate(BaseModel):
    """Request model for updating a region."""
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    accepts_new_tenants: Optional[bool] = None
    max_tenants: Optional[int] = None
    priority: Optional[int] = None
    compliance_certifications: Optional[List[str]] = None
    cost_per_gb_monthly_cents: Optional[int] = None
    cost_per_tenant_monthly_cents: Optional[int] = None