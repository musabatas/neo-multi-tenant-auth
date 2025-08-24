"""Organization request models."""

from typing import Optional

from pydantic import BaseModel, Field, validator
from neo_commons.features.organizations import OrganizationValidationRules


class OrganizationCreateRequest(BaseModel):
    """Request model for creating organizations."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Organization name (slug/identifier)"
    )
    display_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Human-readable display name"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Organization description"
    )
    domain: Optional[str] = Field(
        None,
        description="Primary domain name"
    )
    contact_email: str = Field(
        ...,
        description="Primary contact email"
    )
    plan_id: Optional[str] = Field(
        "starter",
        description="Subscription plan ID"
    )
    
    @validator("name")
    def validate_name(cls, v):
        """Validate organization name format using centralized rules."""
        return OrganizationValidationRules.validate_name(v)
    
    @validator("display_name")
    def validate_display_name(cls, v):
        """Validate display name using centralized rules."""
        return OrganizationValidationRules.validate_display_name(v)
    
    @validator("description")
    def validate_description(cls, v):
        """Validate description using centralized rules."""
        return OrganizationValidationRules.validate_description(v)
    
    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain format using centralized rules."""
        return OrganizationValidationRules.validate_domain(v)


class OrganizationUpdateRequest(BaseModel):
    """Request model for updating organizations."""
    
    display_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=200,
        description="Human-readable display name"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Organization description"
    )
    contact_email: Optional[str] = Field(
        None,
        description="Primary contact email"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Organization active status"
    )
    
    @validator("display_name")
    def validate_display_name(cls, v):
        """Validate display name using centralized rules."""
        if v is None:
            return v
        return OrganizationValidationRules.validate_display_name(v)
    
    @validator("description")
    def validate_description(cls, v):
        """Validate description using centralized rules."""
        return OrganizationValidationRules.validate_description(v)