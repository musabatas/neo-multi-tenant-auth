"""
Response models for regions API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.common.models import PaginationMetadata
from src.common.utils import format_iso8601
from .domain import ConnectionType, HealthStatus, Region


class DatabaseHealthInfo(BaseModel):
    """Health information for a database connection."""
    status: HealthStatus
    is_active: bool
    is_healthy: bool
    last_check: Optional[datetime]
    consecutive_failures: int
    max_failures: int
    uptime_percentage: Optional[float] = Field(None, description="Calculated uptime percentage")
    response_time_ms: Optional[float] = Field(None, description="Last health check response time")
    
    @property
    def health_score(self) -> float:
        """Calculate health score from 0 to 100."""
        if not self.is_active:
            return 0.0
        if not self.is_healthy:
            return 25.0
        if self.consecutive_failures > 0:
            return 75.0 - (self.consecutive_failures * 10)
        return 100.0


class DatabaseConnectionResponse(BaseModel):
    """Response model for database connection."""
    id: str
    connection_name: str
    connection_type: ConnectionType
    host: str
    port: int
    database_name: str
    ssl_mode: str
    
    # Region info
    region_id: str
    region_name: str
    region_display_name: str
    region_active: bool
    
    # Pool configuration
    pool_config: Dict[str, Any] = Field(description="Connection pool configuration")
    
    # Health information
    health: DatabaseHealthInfo
    
    # Metadata
    metadata: Dict[str, Any]
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: format_iso8601
        }


class DatabaseConnectionListResponse(BaseModel):
    """Response model for paginated database connection list."""
    items: List[DatabaseConnectionResponse]
    pagination: PaginationMetadata


class DatabaseListSummary(BaseModel):
    """Summary statistics for database list."""
    total_databases: int
    active_databases: int
    healthy_databases: int
    degraded_databases: int
    unhealthy_databases: int
    by_type: Dict[str, int]
    by_region: Dict[str, int]
    overall_health_score: float


class RegionResponse(BaseModel):
    """Response model for a region."""
    id: str
    code: str
    name: str
    display_name: str
    
    # Location
    country_code: str
    continent: str
    city: Optional[str]
    timezone: str
    coordinates: Optional[str]
    
    # Compliance
    data_residency_compliant: bool
    gdpr_region: bool
    compliance_certifications: List[str]
    legal_entity: Optional[str]
    
    # Capacity & Status
    is_active: bool
    accepts_new_tenants: bool
    capacity_percentage: int
    max_tenants: Optional[int]
    current_tenants: int
    priority: int
    
    # Infrastructure
    provider: str
    provider_region: str
    availability_zones: Optional[List[str]]
    primary_endpoint: str
    backup_endpoints: Optional[List[str]]
    internal_network: Optional[str]
    
    # Costs
    cost_per_gb_monthly_cents: int
    cost_per_tenant_monthly_cents: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    database_count: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: format_iso8601
        }
    
    @classmethod
    def from_domain(cls, region: Region, database_count: Optional[int] = None) -> "RegionResponse":
        """Create response from domain model."""
        return cls(
            **region.model_dump(),
            database_count=database_count
        )


class RegionListResponse(BaseModel):
    """Response model for paginated region list."""
    items: List[RegionResponse]
    pagination: PaginationMetadata


class RegionListSummary(BaseModel):
    """Summary statistics for region list."""
    total_regions: int
    active_regions: int
    accepting_tenants: int
    gdpr_regions: int
    by_provider: Dict[str, int]
    by_continent: Dict[str, int]
    total_capacity: int
    total_current_tenants: int