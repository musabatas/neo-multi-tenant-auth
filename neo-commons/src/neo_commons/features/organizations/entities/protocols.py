"""Protocol interfaces for organization-specific operations.

Defines contracts for organization repositories and services following 
protocol-based dependency injection patterns used across neo-commons.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable, List, Optional, Dict, Any
from datetime import datetime

from ....core.value_objects import OrganizationId, UserId
from ....features.pagination.entities import OffsetPaginationRequest, OffsetPaginationResponse
from .organization import Organization


@runtime_checkable
class OrganizationRepository(Protocol):
    """Protocol for organization data persistence operations."""
    
    @abstractmethod
    async def save(self, organization: Organization) -> Organization:
        """Save organization to persistent storage."""
        ...
    
    @abstractmethod
    async def find_by_id(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Find organization by ID."""
        ...
    
    @abstractmethod
    async def find_by_slug(self, slug: str) -> Optional[Organization]:
        """Find organization by slug."""
        ...
    
    @abstractmethod
    async def find_by_primary_contact(self, user_id: UserId) -> List[Organization]:
        """Find organizations where user is primary contact."""
        ...
    
    @abstractmethod
    async def find_active(self, limit: Optional[int] = None) -> List[Organization]:
        """Find active organizations."""
        ...
    
    @abstractmethod
    async def find_verified(self, limit: Optional[int] = None) -> List[Organization]:
        """Find verified organizations."""
        ...
    
    @abstractmethod
    async def find_by_industry(self, industry: str) -> List[Organization]:
        """Find organizations by industry."""
        ...
    
    @abstractmethod
    async def find_by_country(self, country_code: str) -> List[Organization]:
        """Find organizations by country code."""
        ...
    
    @abstractmethod
    async def search(self, 
                    query: str, 
                    filters: Optional[Dict[str, Any]] = None,
                    limit: Optional[int] = None) -> List[Organization]:
        """Search organizations by name/slug with optional filters."""
        ...
    
    @abstractmethod
    async def update(self, organization: Organization) -> Organization:
        """Update organization."""
        ...
    
    @abstractmethod
    async def delete(self, organization_id: OrganizationId) -> bool:
        """Hard delete organization."""
        ...
    
    @abstractmethod
    async def exists(self, organization_id: OrganizationId) -> bool:
        """Check if organization exists."""
        ...
    
    @abstractmethod
    async def slug_exists(self, slug: str, exclude_id: Optional[OrganizationId] = None) -> bool:
        """Check if slug is already taken."""
        ...
    
    # Batch operations for performance optimization
    @abstractmethod
    async def find_by_ids(self, organization_ids: List[OrganizationId]) -> List[Organization]:
        """Find multiple organizations by IDs in a single query to prevent N+1."""
        ...
    
    @abstractmethod
    async def batch_save(self, organizations: List[Organization]) -> List[Organization]:
        """Save multiple organizations in batch for improved performance."""
        ...
    
    @abstractmethod
    async def batch_update(self, organizations: List[Organization]) -> List[Organization]:
        """Update multiple organizations in batch for improved performance."""
        ...
    
    @abstractmethod
    async def batch_exists(self, organization_ids: List[OrganizationId]) -> Dict[OrganizationId, bool]:
        """Check existence of multiple organizations in a single query."""
        ...
    
    @abstractmethod
    async def batch_find_by_ids(self, organization_ids: List[OrganizationId]) -> Dict[OrganizationId, Optional[Organization]]:
        """Batch get organizations by IDs returning dict with ID mapping."""
        ...
    
    # Pagination operations
    @abstractmethod
    async def find_paginated(self, pagination: OffsetPaginationRequest) -> OffsetPaginationResponse[Organization]:
        """Find organizations with standardized pagination."""
        ...
    
    @abstractmethod
    async def find_active_paginated(self, page: int, per_page: int, order_by: str) -> tuple[List[Organization], int]:
        """Find active organizations with legacy pagination format."""
        ...
    
    # Light vs Full data queries for performance optimization
    @abstractmethod
    async def find_active_light(self, limit: int, offset: int) -> List[Organization]:
        """Find active organizations with light data (9 fields)."""
        ...
    
    @abstractmethod
    async def find_active_full(self, limit: int, offset: int) -> List[Organization]:
        """Find active organizations with full data (20+ fields)."""
        ...
    
    @abstractmethod
    async def search_light(self, query: str, filters: Optional[Dict[str, Any]], limit: int, offset: int) -> List[Organization]:
        """Search organizations with light data."""
        ...
    
    @abstractmethod
    async def search_full(self, query: str, filters: Optional[Dict[str, Any]], limit: int, offset: int) -> List[Organization]:
        """Search organizations with full data."""
        ...
    
    # Admin operations with include_deleted parameter
    @abstractmethod
    async def find_active_light_admin(self, include_deleted: bool, limit: int, offset: int) -> List[Organization]:
        """Find active organizations with light data including deleted ones for admins."""
        ...
    
    @abstractmethod
    async def find_active_full_admin(self, include_deleted: bool, limit: int, offset: int) -> List[Organization]:
        """Find active organizations with full data including deleted ones for admins."""
        ...
    
    @abstractmethod
    async def search_light_admin(self, query: str, filters: Optional[Dict[str, Any]], include_deleted: bool, limit: int, offset: int) -> List[Organization]:
        """Search organizations with light data including deleted ones for admins."""
        ...
    
    @abstractmethod
    async def search_full_admin(self, query: str, filters: Optional[Dict[str, Any]], include_deleted: bool, limit: int, offset: int) -> List[Organization]:
        """Search organizations with full data including deleted ones for admins."""
        ...
    
    # Metadata operations
    @abstractmethod
    async def search_by_metadata(self, metadata_filters: Dict[str, Any], limit: int, offset: int) -> List[Organization]:
        """Search organizations by metadata filters."""
        ...


# OrganizationCache protocol removed - organizations are not cached
# Database queries are sufficient for the occasional access patterns


@runtime_checkable
class OrganizationConfigResolver(Protocol):
    """Protocol for resolving organization-specific configurations.
    
    Integrates with existing configuration infrastructure to provide
    organization-specific config resolution without duplication.
    """
    
    @abstractmethod
    async def get_config(self, organization_id: OrganizationId, key: str, default: Any = None) -> Any:
        """Get organization-specific configuration value."""
        ...
    
    @abstractmethod
    async def get_configs(self, organization_id: OrganizationId, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get all organization configurations, optionally filtered by namespace."""
        ...
    
    @abstractmethod
    async def set_config(self, organization_id: OrganizationId, key: str, value: Any) -> bool:
        """Set organization-specific configuration."""
        ...
    
    @abstractmethod
    async def delete_config(self, organization_id: OrganizationId, key: str) -> bool:
        """Delete organization-specific configuration."""
        ...


@runtime_checkable
class OrganizationNotificationService(Protocol):
    """Protocol for organization-related notifications."""
    
    @abstractmethod
    async def notify_verification_pending(self, organization: Organization) -> bool:
        """Notify about pending verification."""
        ...
    
    @abstractmethod
    async def notify_verification_completed(self, organization: Organization) -> bool:
        """Notify about completed verification."""
        ...
    
    @abstractmethod
    async def notify_organization_created(self, organization: Organization) -> bool:
        """Notify about new organization creation."""
        ...
    
    @abstractmethod
    async def notify_organization_updated(self, organization: Organization, changes: Dict[str, Any]) -> bool:
        """Notify about organization updates."""
        ...
    
    @abstractmethod
    async def notify_organization_deactivated(self, organization: Organization, reason: Optional[str]) -> bool:
        """Notify about organization deactivation."""
        ...
    
    @abstractmethod
    async def on_organization_metadata_updated(self, organization: Organization) -> bool:
        """Notify about organization metadata updates."""
        ...


@runtime_checkable
class OrganizationValidationService(Protocol):
    """Protocol for organization validation operations."""
    
    @abstractmethod
    async def validate_tax_id(self, tax_id: str, country_code: str) -> bool:
        """Validate tax ID format for given country."""
        ...
    
    @abstractmethod
    async def validate_website(self, website_url: str) -> bool:
        """Validate website URL accessibility."""
        ...
    
    @abstractmethod
    async def validate_address(self, address_components: Dict[str, str]) -> Dict[str, Any]:
        """Validate address components and return standardized format."""
        ...
    
    @abstractmethod
    async def validate_business_registration(self, 
                                            legal_name: str, 
                                            tax_id: str, 
                                            country_code: str) -> Dict[str, Any]:
        """Validate business registration details."""
        ...