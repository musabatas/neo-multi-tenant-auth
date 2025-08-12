"""
Domain models for organizations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class Organization(BaseModel):
    """Organization domain model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Identity
    id: UUID
    name: str
    slug: str
    legal_name: Optional[str] = None
    
    # Tax & Business Information
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website_url: Optional[str] = None
    
    # Contact Information
    primary_contact_id: Optional[UUID] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    
    # Preferences
    default_timezone: str = "UTC"
    default_locale: str = "en-US"
    default_currency: str = "USD"
    
    # Branding
    logo_url: Optional[str] = None
    brand_colors: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    is_active: bool = True
    verified_at: Optional[datetime] = None
    verification_documents: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    @property
    def is_verified(self) -> bool:
        """Check if organization is verified."""
        return self.verified_at is not None
    
    @property
    def is_deleted(self) -> bool:
        """Check if organization is soft deleted."""
        return self.deleted_at is not None
    
    @property
    def full_address(self) -> Optional[str]:
        """Get formatted full address."""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.city:
            parts.append(self.city)
        if self.state_province:
            parts.append(self.state_province)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country_code:
            parts.append(self.country_code)
        
        return ", ".join(parts) if parts else None