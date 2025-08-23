"""
Response models for organization API endpoints.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from src.common.models.base import BaseSchema


class OrganizationResponse(BaseSchema):
    """Response model for organization details."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Identity
    id: UUID
    name: str
    slug: str
    legal_name: Optional[str]
    
    # Tax & Business Information
    tax_id: Optional[str]
    business_type: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    website_url: Optional[str]
    
    # Contact Information
    primary_contact_id: Optional[UUID]
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    
    # Address
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state_province: Optional[str]
    postal_code: Optional[str]
    country_code: Optional[str]
    full_address: Optional[str]
    
    # Preferences
    default_timezone: str
    default_locale: str
    default_currency: str
    
    # Branding
    logo_url: Optional[str]
    brand_colors: Dict[str, Any]
    
    # Status
    is_active: bool
    is_verified: bool
    verified_at: Optional[datetime]
    verification_documents: List[str]
    
    # Statistics
    tenant_count: int = 0
    user_count: int = 0
    active_tenant_count: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_domain(
        cls,
        organization: "Organization",
        stats: Optional[Dict[str, Any]] = None,
        contact_info: Optional[Dict[str, Any]] = None
    ) -> "OrganizationResponse":
        """Create response from domain model."""
        stats = stats or {}
        contact_info = contact_info or {}
        
        return cls(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            legal_name=organization.legal_name,
            tax_id=organization.tax_id,
            business_type=organization.business_type,
            industry=organization.industry,
            company_size=organization.company_size,
            website_url=organization.website_url,
            primary_contact_id=organization.primary_contact_id,
            primary_contact_name=contact_info.get('name'),
            primary_contact_email=contact_info.get('email'),
            address_line1=organization.address_line1,
            address_line2=organization.address_line2,
            city=organization.city,
            state_province=organization.state_province,
            postal_code=organization.postal_code,
            country_code=organization.country_code,
            full_address=organization.full_address,
            default_timezone=organization.default_timezone,
            default_locale=organization.default_locale,
            default_currency=organization.default_currency,
            logo_url=organization.logo_url,
            brand_colors=organization.brand_colors,
            is_active=organization.is_active,
            is_verified=organization.is_verified,
            verified_at=organization.verified_at,
            verification_documents=organization.verification_documents,
            tenant_count=stats.get('tenant_count', 0),
            user_count=stats.get('user_count', 0),
            active_tenant_count=stats.get('active_tenant_count', 0),
            created_at=organization.created_at,
            updated_at=organization.updated_at
        )


class OrganizationListItem(BaseSchema):
    """Simplified organization information for list views."""
    
    id: UUID
    name: str
    slug: str
    industry: Optional[str]
    country_code: Optional[str]
    is_active: bool
    is_verified: bool
    tenant_count: int
    user_count: int
    created_at: datetime


class OrganizationListSummary(BaseSchema):
    """Summary statistics for organization list."""
    
    total_organizations: int
    active_organizations: int
    verified_organizations: int
    by_country: Dict[str, int]
    by_industry: Dict[str, int]
    by_company_size: Dict[str, int]
    total_tenants: int
    total_users: int


class OrganizationListResponse(BaseSchema):
    """Response model for organization list with pagination."""
    
    items: List[OrganizationListItem]
    pagination: Dict[str, Any]