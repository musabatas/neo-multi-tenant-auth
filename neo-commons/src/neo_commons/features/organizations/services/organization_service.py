"""Organization service orchestrator using specialized services.

Orchestrates multiple specialized services following single responsibility principle.
Acts as a facade for complex organization operations requiring cross-service coordination.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ....core.value_objects import OrganizationId, UserId
from ....features.pagination.entities import OffsetPaginationRequest, OffsetPaginationResponse

from ..entities.organization import Organization
from ..entities.protocols import (
    OrganizationRepository,
    OrganizationConfigResolver,
    OrganizationNotificationService as LegacyOrganizationNotificationService,
    OrganizationValidationService as LegacyOrganizationValidationService
)

# Import the new specialized services
from .query_service import OrganizationQueryService
from .command_service import OrganizationCommandService
from .status_service import OrganizationStatusService
from .branding_service import OrganizationBrandingService
from .metadata_service import OrganizationMetadataService
from .notification_service import OrganizationNotificationService
from .validation_service import OrganizationValidationService

logger = logging.getLogger(__name__)


class OrganizationService:
    """Organization service orchestrator.
    
    Coordinates multiple specialized services and provides a unified interface
    for complex organization operations. Acts as a facade while delegating
    specific operations to single-responsibility services.
    """
    
    def __init__(
        self,
        repository: OrganizationRepository,
        config_resolver: Optional[OrganizationConfigResolver] = None,
        notification_service: Optional[LegacyOrganizationNotificationService] = None,
        validation_service: Optional[LegacyOrganizationValidationService] = None
    ):
        """Initialize with injected dependencies and create specialized services.
        
        Args:
            repository: Organization repository implementation
            config_resolver: Optional organization config resolver
            notification_service: Optional legacy notification service
            validation_service: Optional legacy validation service
        """
        self._repository = repository
        self._config_resolver = config_resolver
        
        # Create specialized services
        self._query_service = OrganizationQueryService(repository)
        self._command_service = OrganizationCommandService(
            repository, 
            notification_service, 
            validation_service
        )
        self._status_service = OrganizationStatusService(
            repository,
            notification_service
        )
        self._branding_service = OrganizationBrandingService(
            repository,
            validation_service
        )
        self._metadata_service = OrganizationMetadataService(
            repository,
            notification_service
        )
        self._notification_service = OrganizationNotificationService()
        self._validation_service = OrganizationValidationService()
    
    # ===========================================
    # Query Operations (delegate to QueryService)
    # ===========================================
    
    async def get_by_id(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Get organization by ID."""
        return await self._query_service.get_by_id(organization_id)
    
    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        return await self._query_service.get_by_slug(slug)
    
    async def get_by_primary_contact(self, user_id: UserId) -> List[Organization]:
        """Get organizations where user is primary contact."""
        return await self._query_service.get_by_primary_contact(user_id)
    
    async def get_active_organizations(self, limit: Optional[int] = None) -> List[Organization]:
        """Get active organizations."""
        return await self._query_service.get_active_organizations(limit)
    
    async def get_active_organizations_light(self, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with light data."""
        return await self._query_service.get_active_organizations_light(limit, offset)
    
    async def get_active_organizations_full(self, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with full data."""
        return await self._query_service.get_active_organizations_full(limit, offset)
    
    async def list_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[Organization]:
        """List organizations with standardized pagination."""
        return await self._query_service.list_paginated(pagination)
    
    async def search_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[Organization]:
        """Search organizations with pagination."""
        return await self._query_service.search_paginated(pagination)
    
    async def get_active_organizations_paginated(
        self, 
        page: int = 1, 
        per_page: int = 50, 
        order_by: str = "name ASC"
    ) -> tuple[List[Organization], int]:
        """Get active organizations with legacy pagination format."""
        return await self._query_service.get_active_organizations_paginated(page, per_page, order_by)
    
    async def get_verified_organizations(self, limit: Optional[int] = None) -> List[Organization]:
        """Get verified organizations."""
        return await self._query_service.get_verified_organizations(limit)
    
    async def get_by_industry(self, industry: str) -> List[Organization]:
        """Get organizations by industry."""
        return await self._query_service.get_by_industry(industry)
    
    async def get_by_country(self, country_code: str) -> List[Organization]:
        """Get organizations by country code."""
        return await self._query_service.get_by_country(country_code)
    
    async def search_organizations(self, 
                                 query: str, 
                                 filters: Optional[Dict[str, Any]] = None,
                                 limit: Optional[int] = None) -> List[Organization]:
        """Search organizations with flexible filters."""
        return await self._query_service.search_organizations(query, filters, limit)
    
    async def search_organizations_light(self, 
                                        query: str = None, 
                                        filters: Optional[Dict[str, Any]] = None,
                                        limit: int = 20,
                                        offset: int = 0) -> List[Organization]:
        """Search organizations with light data."""
        return await self._query_service.search_organizations_light(query, filters, limit, offset)
    
    async def search_organizations_full(self, 
                                       query: str = None, 
                                       filters: Optional[Dict[str, Any]] = None,
                                       limit: int = 20,
                                       offset: int = 0) -> List[Organization]:
        """Search organizations with full data."""
        return await self._query_service.search_organizations_full(query, filters, limit, offset)
    
    # Admin methods
    async def get_active_organizations_light_admin(self, include_deleted: bool = False, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with light data including deleted ones for admins."""
        return await self._query_service.get_active_organizations_light_admin(include_deleted, limit, offset)
    
    async def get_active_organizations_full_admin(self, include_deleted: bool = False, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with full data including deleted ones for admins."""
        return await self._query_service.get_active_organizations_full_admin(include_deleted, limit, offset)
    
    async def search_organizations_light_admin(self, 
                                              query: str = None, 
                                              filters: Optional[Dict[str, Any]] = None,
                                              include_deleted: bool = False,
                                              limit: int = 20,
                                              offset: int = 0) -> List[Organization]:
        """Search organizations with light data including deleted ones for admins."""
        return await self._query_service.search_organizations_light_admin(query, filters, include_deleted, limit, offset)
    
    async def search_organizations_full_admin(self, 
                                             query: str = None, 
                                             filters: Optional[Dict[str, Any]] = None,
                                             include_deleted: bool = False,
                                             limit: int = 20,
                                             offset: int = 0) -> List[Organization]:
        """Search organizations with full data including deleted ones for admins."""
        return await self._query_service.search_organizations_full_admin(query, filters, include_deleted, limit, offset)
    
    async def organization_exists(self, organization_id: OrganizationId) -> bool:
        """Check if organization exists."""
        return await self._query_service.organization_exists(organization_id)
    
    async def slug_exists(self, slug: str, exclude_id: Optional[OrganizationId] = None) -> bool:
        """Check if slug is already taken."""
        return await self._query_service.slug_exists(slug, exclude_id)
    
    async def batch_get_by_ids(self, organization_ids: List[OrganizationId]) -> Dict[OrganizationId, Optional[Organization]]:
        """Batch get organizations by IDs."""
        return await self._query_service.batch_get_by_ids(organization_ids)
    
    # =============================================
    # Command Operations (delegate to CommandService)
    # =============================================
    
    async def create_organization(
        self,
        name: str,
        slug: Optional[str] = None,
        **kwargs
    ) -> Organization:
        """Create new organization with flexible parameters."""
        return await self._command_service.create_organization(name, slug, **kwargs)
    
    async def update_organization(self, organization: Organization, changes: Optional[Dict[str, Any]] = None) -> Organization:
        """Update organization with change tracking."""
        return await self._command_service.update_organization(organization, changes)
    
    async def delete_organization(self, organization_id: OrganizationId, hard_delete: bool = False) -> Optional[Organization]:
        """Delete organization (soft delete by default)."""
        return await self._command_service.delete_organization(organization_id, hard_delete)
    
    # =============================================
    # Status Operations (delegate to StatusService)
    # =============================================
    
    async def verify_organization(self, 
                                 organization_id: OrganizationId, 
                                 documents: List[str]) -> Organization:
        """Verify organization with documents."""
        return await self._status_service.verify_organization(organization_id, documents)
    
    async def deactivate_organization(self, 
                                     organization_id: OrganizationId, 
                                     reason: Optional[str] = None) -> Organization:
        """Deactivate organization."""
        return await self._status_service.deactivate_organization(organization_id, reason)
    
    async def activate_organization(self, organization_id: OrganizationId) -> Organization:
        """Activate organization."""
        return await self._status_service.activate_organization(organization_id)
    
    # ===============================================
    # Branding Operations (delegate to BrandingService)
    # ===============================================
    
    async def update_organization_branding(self, 
                                          organization_id: OrganizationId, 
                                          logo_url: Optional[str] = None,
                                          brand_colors: Optional[Dict[str, str]] = None) -> Organization:
        """Update organization branding."""
        return await self._branding_service.update_organization_branding(organization_id, logo_url, brand_colors)
    
    async def update_organization_address(self, 
                                         organization_id: OrganizationId,
                                         **address_fields) -> Organization:
        """Update organization address with flexible fields."""
        return await self._branding_service.update_organization_address(organization_id, **address_fields)
    
    # ===============================================
    # Metadata Operations (delegate to MetadataService)
    # ===============================================
    
    async def update_metadata(
        self,
        organization_id: OrganizationId,
        metadata: Dict[str, Any],
        merge: bool = True
    ) -> Organization:
        """Update organization metadata."""
        return await self._metadata_service.update_metadata(organization_id, metadata, merge)
    
    async def get_metadata(self, organization_id: OrganizationId) -> Dict[str, Any]:
        """Get organization metadata."""
        return await self._metadata_service.get_metadata(organization_id)
    
    async def search_by_metadata(
        self,
        metadata_filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0
    ) -> List[Organization]:
        """Search organizations by metadata filters."""
        return await self._metadata_service.search_by_metadata(metadata_filters, limit, offset)
    
    async def set_metadata_value(
        self,
        organization_id: OrganizationId,
        key: str,
        value: Any
    ) -> Organization:
        """Set a single metadata value."""
        return await self._metadata_service.set_metadata_value(organization_id, key, value)
    
    async def remove_metadata_key(
        self,
        organization_id: OrganizationId,
        key: str
    ) -> Organization:
        """Remove a metadata key."""
        return await self._metadata_service.remove_metadata_key(organization_id, key)
    
    # ===============================================
    # Configuration Operations (direct implementation)
    # ===============================================
    
    async def get_organization_config(self, organization_id: OrganizationId, key: str, default: Any = None) -> Any:
        """Get organization-specific configuration using config resolver."""
        if not self._config_resolver:
            logger.warning(f"No config resolver available for organization {organization_id}")
            return default
        
        try:
            return await self._config_resolver.get_config(organization_id, key, default)
        except Exception as e:
            logger.error(f"Failed to get config {key} for organization {organization_id}: {e}")
            return default
    
    async def set_organization_config(self, organization_id: OrganizationId, key: str, value: Any) -> bool:
        """Set organization-specific configuration using config resolver."""
        if not self._config_resolver:
            logger.warning(f"No config resolver available for organization {organization_id}")
            return False
        
        try:
            return await self._config_resolver.set_config(organization_id, key, value)
        except Exception as e:
            logger.error(f"Failed to set config {key} for organization {organization_id}: {e}")
            return False