"""
Organization entity representing a customer organization.

The Organization entity represents a customer organization that can have
multiple tenants within the NeoMultiTenant platform.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ..value_objects import OrganizationId, TenantId


class OrganizationStatus(Enum):
    """Possible states of an organization."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class OrganizationType(Enum):
    """Type of organization for billing and feature purposes."""
    STARTUP = "startup"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    NON_PROFIT = "non_profit"


@dataclass(frozen=True)
class Organization:
    """
    Core organization entity for the NeoMultiTenant platform.
    
    Represents a customer organization that owns one or more tenants.
    Organizations handle billing, subscription management, and 
    cross-tenant administration.
    
    Attributes:
        id: Unique identifier for the organization
        name: Name of the organization
        slug: URL-friendly identifier for the organization
        organization_type: Type of organization for billing purposes
        status: Current status of the organization
        tenant_ids: List of tenant IDs belonging to this organization
        primary_contact_email: Primary contact email for the organization
        billing_email: Email address for billing communications
        is_active: Whether the organization is active
        max_tenants: Maximum number of tenants allowed
        created_at: When the organization was created
        updated_at: When the organization was last updated
        activated_at: When the organization was activated
        suspended_at: When the organization was suspended (if applicable)
    """
    
    id: OrganizationId
    name: str
    slug: str
    organization_type: OrganizationType = OrganizationType.BUSINESS
    status: OrganizationStatus = OrganizationStatus.PENDING
    tenant_ids: List[TenantId] = None
    primary_contact_email: Optional[str] = None
    billing_email: Optional[str] = None
    is_active: bool = False
    max_tenants: int = 5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate organization data after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Organization must have a non-empty name")
        
        if not self.slug or not self.slug.strip():
            raise ValueError("Organization must have a non-empty slug")
        
        # Validate slug format (URL-friendly)
        import re
        if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', self.slug):
            raise ValueError(
                "Organization slug must contain only lowercase letters, numbers, "
                "and hyphens, and cannot start or end with a hyphen"
            )
        
        # Validate emails if provided
        if self.primary_contact_email and '@' not in self.primary_contact_email:
            raise ValueError("Primary contact email must be a valid email address")
        
        if self.billing_email and '@' not in self.billing_email:
            raise ValueError("Billing email must be a valid email address")
        
        # Initialize tenant_ids if None
        if self.tenant_ids is None:
            object.__setattr__(self, 'tenant_ids', [])
        
        # Validate max_tenants
        if self.max_tenants < 1:
            raise ValueError("Organization must allow at least 1 tenant")
    
    @property
    def is_ready(self) -> bool:
        """
        Check if the organization is ready for use.
        
        Returns:
            bool: True if organization is active and has required configuration
        """
        return (
            self.status == OrganizationStatus.ACTIVE
            and self.is_active
            and self.primary_contact_email is not None
        )
    
    @property
    def is_suspended(self) -> bool:
        """
        Check if the organization is currently suspended.
        
        Returns:
            bool: True if organization status is suspended
        """
        return self.status == OrganizationStatus.SUSPENDED
    
    @property
    def can_be_activated(self) -> bool:
        """
        Check if the organization can be activated.
        
        Returns:
            bool: True if organization is in pending status
        """
        return self.status == OrganizationStatus.PENDING
    
    @property
    def tenant_count(self) -> int:
        """
        Get the number of tenants in this organization.
        
        Returns:
            int: Number of tenants belonging to this organization
        """
        return len(self.tenant_ids)
    
    @property
    def available_tenant_slots(self) -> int:
        """
        Get the number of available tenant slots.
        
        Returns:
            int: Number of additional tenants that can be created
        """
        return max(0, self.max_tenants - self.tenant_count)
    
    @property
    def is_at_tenant_limit(self) -> bool:
        """
        Check if the organization has reached its tenant limit.
        
        Returns:
            bool: True if organization cannot create more tenants
        """
        return self.tenant_count >= self.max_tenants
    
    def can_create_tenant(self) -> bool:
        """
        Check if the organization can create a new tenant.
        
        Returns:
            bool: True if organization can create another tenant
        """
        return (
            self.is_ready
            and not self.is_at_tenant_limit
            and not self.is_suspended
        )
    
    def has_tenant(self, tenant_id: TenantId) -> bool:
        """
        Check if the organization owns a specific tenant.
        
        Args:
            tenant_id: The tenant ID to check
            
        Returns:
            bool: True if organization owns the specified tenant
        """
        return tenant_id in self.tenant_ids
    
    def get_contact_email(self) -> str:
        """
        Get the primary contact email for communications.
        
        Returns:
            str: Primary contact email, or billing email as fallback
            
        Raises:
            ValueError: If no contact email is available
        """
        if self.primary_contact_email:
            return self.primary_contact_email
        elif self.billing_email:
            return self.billing_email
        else:
            raise ValueError("Organization has no contact email configured")
    
    def get_billing_email(self) -> str:
        """
        Get the billing email for financial communications.
        
        Returns:
            str: Billing email, or primary contact email as fallback
            
        Raises:
            ValueError: If no billing email is available
        """
        if self.billing_email:
            return self.billing_email
        elif self.primary_contact_email:
            return self.primary_contact_email
        else:
            raise ValueError("Organization has no billing email configured")