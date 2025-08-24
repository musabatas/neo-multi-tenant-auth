"""Organization domain entity.

This module defines the Organization entity and related business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ....core.value_objects import OrganizationId


@dataclass
class Organization:
    """Organization domain entity.
    
    Represents a customer organization that can have multiple tenants.
    Matches admin.organizations table structure.
    """
    
    id: OrganizationId
    name: str
    slug: str
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website_url: Optional[str] = None
    primary_contact_id: Optional[str] = None  # UUID references admin.users
    
    # Address fields
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    
    # Defaults and localization
    default_timezone: str = "UTC"
    default_locale: str = "en-US"
    default_currency: str = "USD"
    
    # Branding
    logo_url: Optional[str] = None
    brand_colors: Dict[str, Any] = field(default_factory=dict)
    
    # Status and verification
    is_active: bool = True
    verified_at: Optional[datetime] = None
    verification_documents: List[str] = field(default_factory=list)
    
    # Audit fields
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        from ..utils.validation import OrganizationValidationRules
        
        # Validate slug format using centralized validation
        try:
            OrganizationValidationRules.validate_slug(self.slug)
        except ValueError as e:
            raise ValueError(f"Invalid slug: {e}")
        
        # Validate name format using centralized validation
        try:
            OrganizationValidationRules.validate_display_name(self.name)
        except ValueError as e:
            raise ValueError(f"Invalid name: {e}")
    
    @property
    def is_deleted(self) -> bool:
        """Check if organization is soft deleted."""
        return self.deleted_at is not None
    
    @property
    def is_verified(self) -> bool:
        """Check if organization is verified."""
        return self.verified_at is not None
    
    @property
    def full_address(self) -> str:
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
        return ", ".join(parts)
    
    def update_brand_colors(self, colors: Dict[str, str]) -> None:
        """Update brand colors."""
        self.brand_colors.update(colors)
        self.updated_at = datetime.now(timezone.utc)
    
    def verify(self, documents: List[str]) -> None:
        """Mark organization as verified."""
        self.verified_at = datetime.now(timezone.utc)
        self.verification_documents = documents
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate organization."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate organization."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self) -> None:
        """Soft delete organization."""
        self.is_active = False
        self.deleted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_address(self, 
                      line1: Optional[str] = None,
                      line2: Optional[str] = None,
                      city: Optional[str] = None,
                      state_province: Optional[str] = None,
                      postal_code: Optional[str] = None,
                      country_code: Optional[str] = None) -> None:
        """Update address information."""
        if line1 is not None:
            self.address_line1 = line1
        if line2 is not None:
            self.address_line2 = line2
        if city is not None:
            self.city = city
        if state_province is not None:
            self.state_province = state_province
        if postal_code is not None:
            self.postal_code = postal_code
        if country_code is not None:
            self.country_code = country_code
        self.updated_at = datetime.now(timezone.utc)