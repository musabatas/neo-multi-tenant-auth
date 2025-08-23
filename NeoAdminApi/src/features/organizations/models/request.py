"""Organization request models."""

from typing import Optional

from pydantic import BaseModel, Field, validator


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
        """Validate organization name format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Organization name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.lower()
    
    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain format."""
        if v is None:
            return v
        
        if not v or "." not in v:
            raise ValueError("Invalid domain format")
        
        return v.lower()


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