"""
Request models for organization API endpoints.
"""

from typing import Optional, Dict, Any, List
from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class OrganizationCreate(BaseModel):
    """Request model for creating a new organization."""
    
    name: str = Field(..., min_length=1, max_length=255,
                     description="Organization display name")
    slug: str = Field(..., min_length=2, max_length=100,
                     pattern=r'^[a-z0-9][a-z0-9-]*[a-z0-9]$',
                     description="URL-safe unique identifier")
    legal_name: Optional[str] = Field(None, max_length=255,
                                     description="Legal entity name")
    
    # Tax & Business Information
    tax_id: Optional[str] = Field(None, max_length=50,
                                 description="Tax identification number")
    business_type: Optional[str] = Field(None, max_length=50,
                                        description="Type of business entity")
    industry: Optional[str] = Field(None, max_length=100,
                                  description="Industry sector")
    company_size: Optional[str] = Field(None, max_length=20,
                                       description="Size category (e.g., 1-10, 11-50)")
    website_url: Optional[str] = Field(None, max_length=2048,
                                      description="Company website URL")
    
    # Contact Information
    primary_contact_id: Optional[UUID] = Field(None,
                                              description="Primary contact user ID")
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country_code: Optional[str] = Field(None, pattern=r'^[A-Z]{2}$',
                                       description="ISO 3166-1 alpha-2 country code")
    
    # Preferences
    default_timezone: str = Field("UTC", max_length=50,
                                description="Default timezone for the organization")
    default_locale: str = Field("en-US", max_length=10,
                              description="Default locale for the organization")
    default_currency: str = Field("USD", pattern=r'^[A-Z]{3}$',
                                description="ISO 4217 currency code")
    
    # Branding
    logo_url: Optional[str] = Field(None, max_length=2048,
                                   description="Organization logo URL")
    brand_colors: Dict[str, Any] = Field(default_factory=dict,
                                        description="Brand color palette")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not v or not v.replace('-', '').isalnum():
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Slug cannot start or end with a hyphen")
        return v.lower()
    
    @field_validator('website_url')
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format."""
        if v:
            if not (v.startswith('http://') or v.startswith('https://')):
                v = f'https://{v}'
        return v
    
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        """Ensure country code is uppercase."""
        return v.upper() if v else None


class OrganizationUpdate(BaseModel):
    """Request model for updating an organization."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    
    # Tax & Business Information
    tax_id: Optional[str] = Field(None, max_length=50)
    business_type: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=20)
    website_url: Optional[str] = Field(None, max_length=2048)
    
    # Contact Information
    primary_contact_id: Optional[UUID] = None
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country_code: Optional[str] = Field(None, pattern=r'^[A-Z]{2}$')
    
    # Preferences
    default_timezone: Optional[str] = Field(None, max_length=50)
    default_locale: Optional[str] = Field(None, max_length=10)
    default_currency: Optional[str] = Field(None, pattern=r'^[A-Z]{3}$')
    
    # Branding
    logo_url: Optional[str] = Field(None, max_length=2048)
    brand_colors: Optional[Dict[str, Any]] = None
    
    # Status
    is_active: Optional[bool] = None
    
    @field_validator('website_url')
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format."""
        if v and v != "":
            if not (v.startswith('http://') or v.startswith('https://')):
                v = f'https://{v}'
        return v
    
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        """Ensure country code is uppercase."""
        return v.upper() if v else None


class OrganizationFilter(BaseModel):
    """Filter parameters for listing organizations."""
    
    search: Optional[str] = Field(None, min_length=1, max_length=100,
                                 description="Search in name, slug, legal_name")
    country_code: Optional[str] = Field(None, pattern=r'^[A-Z]{2}$',
                                       description="Filter by country code")
    industry: Optional[str] = Field(None, description="Filter by industry")
    company_size: Optional[str] = Field(None, description="Filter by company size")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    created_after: Optional[date] = Field(None, description="Filter by creation date")
    created_before: Optional[date] = Field(None, description="Filter by creation date")