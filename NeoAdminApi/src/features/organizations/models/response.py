"""Organization response models."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from neo_commons.features.organizations.entities import Organization


class OrganizationResponse(BaseModel):
    """Response model for organizations."""
    
    id: UUID = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    display_name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Description")
    domain: Optional[str] = Field(None, description="Primary domain")
    contact_email: str = Field(..., description="Contact email")
    plan_id: str = Field(..., description="Subscription plan ID")
    is_active: bool = Field(..., description="Active status")
    tenant_count: int = Field(0, description="Number of tenants")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_entity(cls, organization: Organization) -> "OrganizationResponse":
        """Create response from neo-commons organization entity."""
        return cls(
            id=UUID(organization.id.value),
            name=organization.name,
            display_name=organization.display_name,
            description=organization.description,
            domain=organization.domain,
            contact_email=organization.contact_email,
            plan_id=organization.plan_id,
            is_active=organization.is_active,
            tenant_count=getattr(organization, 'tenant_count', 0),
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )


class OrganizationListResponse(BaseModel):
    """Response model for organization list."""
    
    organizations: List[OrganizationResponse] = Field(
        ...,
        description="List of organizations"
    )
    total: int = Field(..., description="Total number of organizations")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")
    
    @property
    def has_more(self) -> bool:
        """Check if there are more items available."""
        return self.skip + len(self.organizations) < self.total


class OrganizationStatsResponse(BaseModel):
    """Response model for organization statistics."""
    
    total_organizations: int = Field(..., description="Total organizations")
    active_organizations: int = Field(..., description="Active organizations")
    inactive_organizations: int = Field(..., description="Inactive organizations")
    total_tenants: int = Field(..., description="Total tenants across all organizations")
    organizations_created_this_month: int = Field(
        ...,
        description="Organizations created this month"
    )