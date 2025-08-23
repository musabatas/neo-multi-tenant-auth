"""
Tenant entity representing a tenant in the multi-tenant platform.

The Tenant entity encapsulates the core properties and business rules
for tenants within the NeoMultiTenant platform.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from ..value_objects import TenantId, OrganizationId


class TenantStatus(Enum):
    """Possible states of a tenant."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class DeploymentType(Enum):
    """Type of deployment for the tenant."""
    SCHEMA = "schema"      # Schema-based multi-tenancy
    DATABASE = "database"  # Database-based multi-tenancy
    DEDICATED = "dedicated"  # Dedicated infrastructure


@dataclass(frozen=True)
class Tenant:
    """
    Core tenant entity for the NeoMultiTenant platform.
    
    Represents a tenant with their essential properties and configuration.
    Each tenant represents an organization or customer using the platform
    with their own isolated data and configuration.
    
    Attributes:
        id: Unique identifier for the tenant
        organization_id: ID of the organization this tenant belongs to
        slug: URL-friendly identifier for the tenant
        name: Human-readable name of the tenant
        schema_name: Database schema name for schema-based tenancy
        region: Geographic region where tenant data is stored
        deployment_type: Type of multi-tenancy deployment
        status: Current status of the tenant
        is_active: Whether the tenant is active
        created_at: When the tenant was created
        updated_at: When the tenant was last updated
        activated_at: When the tenant was activated
        suspended_at: When the tenant was suspended (if applicable)
    """
    
    id: TenantId
    organization_id: OrganizationId
    slug: str
    name: str
    schema_name: Optional[str] = None
    region: str = "us-east-1"
    deployment_type: DeploymentType = DeploymentType.SCHEMA
    status: TenantStatus = TenantStatus.PENDING
    is_active: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate tenant data after initialization."""
        if not self.slug or not self.slug.strip():
            raise ValueError("Tenant must have a non-empty slug")
        
        if not self.name or not self.name.strip():
            raise ValueError("Tenant must have a non-empty name")
        
        # Validate slug format (URL-friendly)
        import re
        if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', self.slug):
            raise ValueError(
                "Tenant slug must contain only lowercase letters, numbers, "
                "and hyphens, and cannot start or end with a hyphen"
            )
        
        # For schema-based tenancy, schema_name should be set
        if self.deployment_type == DeploymentType.SCHEMA and not self.schema_name:
            # Auto-generate schema name from slug if not provided
            object.__setattr__(self, 'schema_name', f"tenant_{self.slug}")
    
    @property
    def is_ready(self) -> bool:
        """
        Check if the tenant is ready for use.
        
        Returns:
            bool: True if tenant is active and has required configuration
        """
        return (
            self.status == TenantStatus.ACTIVE
            and self.is_active
            and (
                self.deployment_type != DeploymentType.SCHEMA 
                or self.schema_name is not None
            )
        )
    
    @property
    def is_suspended(self) -> bool:
        """
        Check if the tenant is currently suspended.
        
        Returns:
            bool: True if tenant status is suspended
        """
        return self.status == TenantStatus.SUSPENDED
    
    @property
    def can_be_activated(self) -> bool:
        """
        Check if the tenant can be activated.
        
        Returns:
            bool: True if tenant is in pending status
        """
        return self.status == TenantStatus.PENDING
    
    @property
    def database_identifier(self) -> str:
        """
        Get the database identifier for this tenant.
        
        Returns:
            str: Schema name for schema-based, database name for database-based
        """
        if self.deployment_type == DeploymentType.SCHEMA:
            return self.schema_name or f"tenant_{self.slug}"
        else:
            return f"tenant_{self.slug}"
    
    def get_keycloak_realm_name(self) -> str:
        """
        Get the Keycloak realm name for this tenant.
        
        Returns:
            str: Keycloak realm name following the pattern tenant-{slug}
        """
        return f"tenant-{self.slug}"
    
    def is_in_region(self, region: str) -> bool:
        """
        Check if the tenant is deployed in a specific region.
        
        Args:
            region: The region to check
            
        Returns:
            bool: True if tenant is in the specified region
        """
        return self.region == region
    
    def uses_deployment_type(self, deployment_type: DeploymentType) -> bool:
        """
        Check if the tenant uses a specific deployment type.
        
        Args:
            deployment_type: The deployment type to check
            
        Returns:
            bool: True if tenant uses the specified deployment type
        """
        return self.deployment_type == deployment_type