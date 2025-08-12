"""
Domain models for regions and database connections.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ConnectionType(str, Enum):
    """Database connection types."""
    PRIMARY = "primary"
    REPLICA = "replica"
    ANALYTICS = "analytics"
    BACKUP = "backup"


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DatabaseConnection(BaseModel):
    """Domain model for database connection."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    region_id: str
    connection_name: str
    connection_type: ConnectionType
    host: str
    port: int = 5432
    database_name: str
    ssl_mode: str = "require"
    username: str = "postgres"
    encrypted_password: Optional[str] = None  # Used only for health checks, not exposed in API responses
    pool_min_size: int = 5
    pool_max_size: int = 20
    pool_timeout_seconds: int = 30
    pool_recycle_seconds: int = 3600
    pool_pre_ping: bool = True
    is_active: bool = True
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    # Joined fields
    region_name: Optional[str] = None
    region_display_name: Optional[str] = None
    region_active: Optional[bool] = None


class Region(BaseModel):
    """Domain model for region."""
    model_config = ConfigDict(from_attributes=True)
    
    # Core fields
    id: str
    code: str
    name: str
    display_name: str
    
    # Location
    country_code: str
    continent: str
    city: Optional[str] = None
    timezone: str
    coordinates: Optional[str] = None
    
    # Compliance
    data_residency_compliant: bool = True
    gdpr_region: bool = False
    compliance_certifications: List[str] = Field(default_factory=list)
    legal_entity: Optional[str] = None
    
    # Capacity & Status
    is_active: bool = True
    accepts_new_tenants: bool = True
    capacity_percentage: int = 0
    max_tenants: Optional[int] = None
    current_tenants: int = 0
    priority: int = 0
    
    # Infrastructure
    provider: str = "Docker"
    provider_region: str
    availability_zones: Optional[List[str]] = None
    primary_endpoint: str
    backup_endpoints: Optional[List[str]] = None
    internal_network: Optional[str] = None
    
    # Costs (in cents)
    cost_per_gb_monthly_cents: int = 0
    cost_per_tenant_monthly_cents: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime