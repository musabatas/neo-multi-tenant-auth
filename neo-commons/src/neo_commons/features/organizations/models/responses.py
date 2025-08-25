"""Organization response models with override capability.

Provides base Pydantic models that can be used across services and
extended/overridden for service-specific requirements.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

from ....core.value_objects import OrganizationId


class OrganizationResponse(BaseModel):
    """Full organization response model.
    
    Base model that can be extended by services for additional fields.
    """
    
    id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization display name")
    slug: str = Field(..., description="Organization slug")
    legal_name: Optional[str] = Field(None, description="Legal business name")
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    business_type: Optional[str] = Field(None, description="Type of business entity")
    industry: Optional[str] = Field(None, description="Industry category")
    company_size: Optional[str] = Field(None, description="Company size category")
    website_url: Optional[str] = Field(None, description="Website URL")
    primary_contact_id: Optional[str] = Field(None, description="Primary contact user ID")
    
    # Address fields
    address_line1: Optional[str] = Field(None, description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: Optional[str] = Field(None, description="City")
    state_province: Optional[str] = Field(None, description="State or province")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country_code: Optional[str] = Field(None, description="ISO 2-letter country code")
    full_address: Optional[str] = Field(None, description="Formatted full address")
    
    # Localization
    default_timezone: str = Field(..., description="Default timezone")
    default_locale: str = Field(..., description="Default locale")
    default_currency: str = Field(..., description="Default currency")
    
    # Branding
    logo_url: Optional[str] = Field(None, description="Logo URL")
    brand_colors: Dict[str, str] = Field(default_factory=dict, description="Brand color scheme")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Status fields
    is_active: bool = Field(..., description="Whether organization is active")
    is_verified: bool = Field(..., description="Whether organization is verified")
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")
    verification_documents: List[str] = Field(default_factory=list, description="Verification documents")
    
    # Audit fields
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    @classmethod
    def from_entity(cls, organization) -> "OrganizationResponse":
        """Create response from organization entity."""
        return cls(
            id=str(organization.id.value),
            name=organization.name,
            slug=organization.slug,
            legal_name=organization.legal_name,
            tax_id=organization.tax_id,
            business_type=organization.business_type,
            industry=organization.industry,
            company_size=organization.company_size,
            website_url=organization.website_url,
            primary_contact_id=organization.primary_contact_id,
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
            metadata=organization.metadata or {},
            is_active=organization.is_active,
            is_verified=organization.is_verified,
            verified_at=organization.verified_at,
            verification_documents=organization.verification_documents,
            created_at=organization.created_at,
            updated_at=organization.updated_at
        )
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for service-specific extensions
        json_schema_extra = {
            "example": {
                "id": "01234567-89ab-cdef-0123-456789abcdef",
                "name": "Acme Corporation",
                "slug": "acme-corp",
                "legal_name": "Acme Corporation Ltd.",
                "tax_id": "123456789",
                "business_type": "Corporation",
                "industry": "Technology",
                "company_size": "51-200",
                "website_url": "https://acme.com",
                "address_line1": "123 Business St",
                "city": "San Francisco",
                "state_province": "CA",
                "postal_code": "94105",
                "country_code": "US",
                "full_address": "123 Business St, San Francisco, CA, 94105, US",
                "default_timezone": "America/Los_Angeles",
                "default_locale": "en-US",
                "default_currency": "USD",
                "logo_url": "https://cdn.acme.com/logo.png",
                "brand_colors": {
                    "primary": "#007bff",
                    "secondary": "#6c757d"
                },
                "metadata": {
                    "source": "api",
                    "classification": "enterprise",
                    "tags": ["technology", "saas"],
                    "custom_fields": {
                        "account_manager": "john.doe@company.com",
                        "contract_type": "annual"
                    }
                },
                "is_active": True,
                "is_verified": True,
                "verified_at": "2024-01-15T10:30:00Z",
                "verification_documents": [
                    "https://docs.acme.com/business-license.pdf"
                ],
                "created_at": "2024-01-01T09:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class OrganizationSummaryResponse(BaseModel):
    """Lightweight organization response for lists and summaries."""
    
    id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization display name")
    slug: str = Field(..., description="Organization slug")
    industry: Optional[str] = Field(None, description="Industry category")
    country_code: Optional[str] = Field(None, description="ISO 2-letter country code")
    logo_url: Optional[str] = Field(None, description="Logo URL")
    is_active: bool = Field(..., description="Whether organization is active")
    is_verified: bool = Field(..., description="Whether organization is verified")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @classmethod
    def from_entity(cls, organization) -> "OrganizationSummaryResponse":
        """Create summary response from organization entity."""
        return cls(
            id=str(organization.id.value),
            name=organization.name,
            slug=organization.slug,
            industry=organization.industry,
            country_code=organization.country_code,
            logo_url=organization.logo_url,
            is_active=organization.is_active,
            is_verified=organization.is_verified,
            created_at=organization.created_at
        )
    
    class Config:
        """Pydantic config."""
        extra = "allow"


class OrganizationListResponse(BaseModel):
    """Response model for organization lists with pagination."""
    
    organizations: List[Union[OrganizationSummaryResponse, OrganizationResponse]] = Field(..., description="List of organizations")
    total: int = Field(..., description="Total number of organizations")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "organizations": [
                    {
                        "id": "01234567-89ab-cdef-0123-456789abcdef",
                        "name": "Acme Corporation",
                        "slug": "acme-corp",
                        "industry": "Technology",
                        "country_code": "US",
                        "is_active": True,
                        "is_verified": True,
                        "created_at": "2024-01-01T09:00:00Z"
                    }
                ],
                "total": 150,
                "page": 1,
                "per_page": 20,
                "has_next": True,
                "has_prev": False
            }
        }


class OrganizationSearchResponse(BaseModel):
    """Response model for organization search results."""
    
    organizations: List[Union[OrganizationSummaryResponse, OrganizationResponse]] = Field(..., description="Search results")
    query: str = Field(..., description="Original search query")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    total: int = Field(..., description="Total number of results")
    took_ms: Optional[int] = Field(None, description="Search duration in milliseconds")
    
    class Config:
        """Pydantic config."""
        extra = "allow"


class OrganizationConfigResponse(BaseModel):
    """Response model for organization configuration."""
    
    organization_id: str = Field(..., description="Organization ID")
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    namespace: Optional[str] = Field(None, description="Configuration namespace")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic config."""
        extra = "allow"


class OrganizationStatsResponse(BaseModel):
    """Response model for organization statistics."""
    
    total_organizations: int = Field(..., description="Total number of organizations")
    active_organizations: int = Field(..., description="Number of active organizations")
    verified_organizations: int = Field(..., description="Number of verified organizations")
    by_industry: Dict[str, int] = Field(default_factory=dict, description="Organizations by industry")
    by_country: Dict[str, int] = Field(default_factory=dict, description="Organizations by country")
    by_company_size: Dict[str, int] = Field(default_factory=dict, description="Organizations by company size")
    recent_verifications: int = Field(..., description="Recent verifications (last 30 days)")
    growth_rate: Optional[float] = Field(None, description="Monthly growth rate percentage")
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "total_organizations": 1250,
                "active_organizations": 1180,
                "verified_organizations": 950,
                "by_industry": {
                    "Technology": 450,
                    "Healthcare": 280,
                    "Finance": 220,
                    "Education": 150,
                    "Other": 150
                },
                "by_country": {
                    "US": 680,
                    "CA": 180,
                    "GB": 150,
                    "DE": 120,
                    "Other": 120
                },
                "by_company_size": {
                    "1-10": 350,
                    "11-50": 420,
                    "51-200": 280,
                    "201-1000": 150,
                    "1000+": 50
                },
                "recent_verifications": 45,
                "growth_rate": 12.5
            }
        }


class OrganizationMetadataResponse(BaseModel):
    """Response model for organization metadata operations."""
    
    organization_id: str = Field(..., description="Organization ID")
    metadata: Dict[str, Any] = Field(..., description="Organization metadata")
    updated_at: datetime = Field(..., description="Last metadata update timestamp")
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "organization_id": "01234567-89ab-cdef-0123-456789abcdef",
                "metadata": {
                    "tags": ["enterprise", "saas"],
                    "integration": {
                        "crm": "salesforce",
                        "billing": "stripe"
                    },
                    "custom_fields": {
                        "account_manager": "john.doe@company.com",
                        "renewal_date": "2024-12-31"
                    }
                },
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class OrganizationActivityResponse(BaseModel):
    """Response model for organization activity tracking."""
    
    organization_id: str = Field(..., description="Organization ID")
    activity_type: str = Field(..., description="Type of activity")
    description: str = Field(..., description="Activity description")
    actor_id: Optional[str] = Field(None, description="User who performed the action")
    actor_name: Optional[str] = Field(None, description="Name of actor")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional activity data")
    timestamp: datetime = Field(..., description="Activity timestamp")
    
    class Config:
        """Pydantic config."""
        extra = "allow"