"""Organization request models with override capability.

Provides base Pydantic models that can be used across services and
extended/overridden for service-specific requirements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

from ..utils.validation import OrganizationValidationRules


class CreateOrganizationRequest(BaseModel):
    """Request model for creating organization.
    
    Base model that can be extended by services for additional fields.
    """
    
    name: str = Field(..., description="Organization display name")
    slug: Optional[str] = Field(None, description="Organization slug (auto-generated if not provided)")
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
    
    # Localization
    default_timezone: str = Field("UTC", description="Default timezone")
    default_locale: str = Field("en-US", description="Default locale")
    default_currency: str = Field("USD", description="Default currency")
    
    # Branding
    logo_url: Optional[str] = Field(None, description="Logo URL")
    brand_colors: Optional[Dict[str, str]] = Field(default_factory=dict, description="Brand color scheme")
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator("name")
    def validate_name(cls, v):
        """Validate organization display name."""
        return OrganizationValidationRules.validate_display_name(v)
    
    @validator("slug")
    def validate_slug(cls, v):
        """Validate organization slug if provided."""
        if v is not None:
            return OrganizationValidationRules.validate_slug(v)
        return v
    
    @validator("country_code")
    def validate_country_code(cls, v):
        """Validate country code format."""
        if v is not None and len(v) != 2:
            raise ValueError("Country code must be 2 characters")
        return v.upper() if v else v
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for service-specific extensions
        json_schema_extra = {
            "example": {
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
                "default_timezone": "America/Los_Angeles",
                "brand_colors": {
                    "primary": "#007bff",
                    "secondary": "#6c757d"
                },
                "metadata": {
                    "source": "api",
                    "classification": "enterprise",
                    "custom_fields": {
                        "department": "engineering",
                        "priority": "high"
                    }
                }
            }
        }


class UpdateOrganizationRequest(BaseModel):
    """Request model for updating organization.
    
    All fields optional for partial updates.
    """
    
    name: Optional[str] = Field(None, description="Organization display name")
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
    
    # Localization
    default_timezone: Optional[str] = Field(None, description="Default timezone")
    default_locale: Optional[str] = Field(None, description="Default locale")
    default_currency: Optional[str] = Field(None, description="Default currency")
    
    # Branding
    logo_url: Optional[str] = Field(None, description="Logo URL")
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand color scheme")
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator("name")
    def validate_name(cls, v):
        """Validate organization display name."""
        if v is not None:
            return OrganizationValidationRules.validate_display_name(v)
        return v
    
    @validator("country_code")
    def validate_country_code(cls, v):
        """Validate country code format."""
        if v is not None and len(v) != 2:
            raise ValueError("Country code must be 2 characters")
        return v.upper() if v else v
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for service-specific extensions


class UpdateOrganizationBrandingRequest(BaseModel):
    """Request model for updating organization branding."""
    
    logo_url: Optional[str] = Field(None, description="Logo URL")
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand color scheme")
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "logo_url": "https://cdn.acme.com/logo.png",
                "brand_colors": {
                    "primary": "#007bff",
                    "secondary": "#6c757d",
                    "accent": "#28a745"
                }
            }
        }


class UpdateOrganizationAddressRequest(BaseModel):
    """Request model for updating organization address."""
    
    address_line1: Optional[str] = Field(None, description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: Optional[str] = Field(None, description="City")
    state_province: Optional[str] = Field(None, description="State or province")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country_code: Optional[str] = Field(None, description="ISO 2-letter country code")
    
    @validator("country_code")
    def validate_country_code(cls, v):
        """Validate country code format."""
        if v is not None and len(v) != 2:
            raise ValueError("Country code must be 2 characters")
        return v.upper() if v else v
    
    class Config:
        """Pydantic config."""
        extra = "allow"


class VerifyOrganizationRequest(BaseModel):
    """Request model for verifying organization."""
    
    verification_documents: List[str] = Field(..., description="List of verification document URLs")
    notes: Optional[str] = Field(None, description="Verification notes")
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "verification_documents": [
                    "https://docs.acme.com/business-license.pdf",
                    "https://docs.acme.com/tax-certificate.pdf"
                ],
                "notes": "All documents verified successfully"
            }
        }


class OrganizationSearchRequest(BaseModel):
    """Request model for searching organizations."""
    
    query: str = Field(..., description="Search query for name/slug")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Search filters")
    limit: Optional[int] = Field(50, ge=1, le=100, description="Maximum results")
    offset: Optional[int] = Field(0, ge=0, description="Results offset")
    sort_by: Optional[str] = Field("name", description="Sort field")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort order")
    
    # Common filters as direct fields for convenience
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    industry: Optional[str] = Field(None, description="Filter by industry")
    country_code: Optional[str] = Field(None, description="Filter by country")
    
    def get_combined_filters(self) -> Dict[str, Any]:
        """Get combined filters including direct fields."""
        combined_filters = self.filters.copy() if self.filters else {}
        
        # Add direct filter fields if they're set
        if self.is_active is not None:
            combined_filters["is_active"] = self.is_active
        if self.is_verified is not None:
            combined_filters["is_verified"] = self.is_verified
        if self.industry is not None:
            combined_filters["industry"] = self.industry
        if self.country_code is not None:
            combined_filters["country_code"] = self.country_code
        
        return combined_filters
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "query": "tech",
                "filters": {
                    "is_active": True,
                    "industry": "Technology"
                },
                "limit": 20,
                "sort_by": "name",
                "sort_order": "asc"
            }
        }


class OrganizationMetadataRequest(BaseModel):
    """Request model for organization metadata operations."""
    
    metadata: Dict[str, Any] = Field(..., description="Metadata to set or update")
    merge: bool = Field(True, description="Whether to merge with existing metadata or replace")
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
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
                "merge": True
            }
        }


class OrganizationSearchByMetadataRequest(BaseModel):
    """Request model for searching organizations by metadata."""
    
    metadata_filters: Dict[str, Any] = Field(..., description="Metadata filters using JSONB operators")
    limit: Optional[int] = Field(50, ge=1, le=100, description="Maximum results")
    offset: Optional[int] = Field(0, ge=0, description="Results offset")
    
    class Config:
        """Pydantic config."""
        extra = "allow"
        json_schema_extra = {
            "example": {
                "metadata_filters": {
                    "tags": ["enterprise"],
                    "integration.crm": "salesforce"
                },
                "limit": 20,
                "offset": 0
            }
        }


class OrganizationConfigRequest(BaseModel):
    """Request model for organization configuration operations."""
    
    key: str = Field(..., description="Configuration key")
    value: Optional[Any] = Field(None, description="Configuration value")
    namespace: Optional[str] = Field(None, description="Configuration namespace")
    
    class Config:
        """Pydantic config."""
        extra = "allow"