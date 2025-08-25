"""Organization query service for read operations.

Handles all read-only operations including get, find, list, search, and existence checks.
Follows single responsibility principle for query operations only.
"""

import logging
from typing import List, Optional, Dict, Any

from ....core.value_objects import OrganizationId, UserId
from ...pagination.entities import OffsetPaginationRequest, OffsetPaginationResponse

from ..entities.organization import Organization
from ..entities.protocols import OrganizationRepository
from ..utils.error_handling import (
    organization_error_handler,
    log_organization_operation
)

logger = logging.getLogger(__name__)


class OrganizationQueryService:
    """Service for organization read operations.
    
    Handles all query operations including single/batch retrieval,
    search, filtering, and existence checks.
    """
    
    def __init__(self, repository: OrganizationRepository):
        """Initialize with repository dependency.
        
        Args:
            repository: Organization repository implementation
        """
        self._repository = repository
    
    # Single entity retrieval methods
    
    @organization_error_handler("get organization by ID", reraise=False, default_return=None)
    @log_organization_operation("get organization by ID", include_timing=True)
    async def get_by_id(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Get organization by ID."""
        try:
            return await self._repository.find_by_id(organization_id)
        except Exception as e:
            logger.error(f"Failed to get organization {organization_id}: {e}")
            raise
    
    @organization_error_handler("get organization by slug", reraise=False, default_return=None)
    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        try:
            return await self._repository.find_by_slug(slug)
        except Exception as e:
            logger.error(f"Failed to get organization by slug '{slug}': {e}")
            raise
    
    @organization_error_handler("get organizations by primary contact", reraise=False, default_return=[])
    async def get_by_primary_contact(self, user_id: UserId) -> List[Organization]:
        """Get organizations where user is primary contact."""
        try:
            return await self._repository.find_by_primary_contact(user_id)
        except Exception as e:
            logger.error(f"Failed to get organizations for user {user_id}: {e}")
            raise
    
    # Active organizations retrieval methods
    
    async def get_active_organizations(self, limit: Optional[int] = None) -> List[Organization]:
        """Get active organizations."""
        try:
            return await self._repository.find_active(limit)
        except Exception as e:
            logger.error(f"Failed to get active organizations: {e}")
            raise
    
    # Light vs Full data methods for performance optimization
    async def get_active_organizations_light(self, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with light data (9 fields) for efficient listing."""
        try:
            return await self._repository.find_active_light(limit, offset)
        except Exception as e:
            logger.error(f"Failed to get active organizations (light): {e}")
            raise
    
    async def get_active_organizations_full(self, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with full data (20+ fields) for complete listing."""
        try:
            return await self._repository.find_active_full(limit, offset)
        except Exception as e:
            logger.error(f"Failed to get active organizations (full): {e}")
            raise
    
    # Pagination methods
    
    async def list_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[Organization]:
        """List organizations with standardized pagination.
        
        Args:
            pagination: Pagination request with filters and sorting
            
        Returns:
            Paginated response with organizations and metadata
        """
        try:
            return await self._repository.find_paginated(pagination)
        except Exception as e:
            logger.error(f"Failed to list paginated organizations: {e}")
            raise
    
    async def search_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[Organization]:
        """Search organizations with pagination.
        
        Args:
            pagination: Pagination request with search query
            
        Returns:
            Paginated search results
        """
        try:
            # For now, delegate to list_paginated
            # TODO: Implement search-specific logic when needed
            return await self._repository.find_paginated(pagination)
        except Exception as e:
            logger.error(f"Failed to search paginated organizations: {e}")
            raise
    
    async def get_active_organizations_paginated(
        self, 
        page: int = 1, 
        per_page: int = 50, 
        order_by: str = "name ASC"
    ) -> tuple[List[Organization], int]:
        """Get active organizations with legacy pagination format.
        
        Args:
            page: Page number (1-based)
            per_page: Number of organizations per page
            order_by: SQL ORDER BY clause (e.g., "name ASC", "created_at DESC")
            
        Returns:
            Tuple of (organizations list, total count)
            
        Note:
            This method maintains backward compatibility. New code should use list_paginated().
        """
        try:
            return await self._repository.find_active_paginated(page, per_page, order_by)
        except Exception as e:
            logger.error(f"Failed to get paginated active organizations: {e}")
            raise
    
    # Specialized filtering methods
    
    async def get_verified_organizations(self, limit: Optional[int] = None) -> List[Organization]:
        """Get verified organizations."""
        try:
            return await self._repository.find_verified(limit)
        except Exception as e:
            logger.error(f"Failed to get verified organizations: {e}")
            raise
    
    async def get_by_industry(self, industry: str) -> List[Organization]:
        """Get organizations by industry."""
        try:
            return await self._repository.find_by_industry(industry)
        except Exception as e:
            logger.error(f"Failed to get organizations by industry '{industry}': {e}")
            raise
    
    async def get_by_country(self, country_code: str) -> List[Organization]:
        """Get organizations by country code."""
        try:
            return await self._repository.find_by_country(country_code)
        except Exception as e:
            logger.error(f"Failed to get organizations by country '{country_code}': {e}")
            raise
    
    # Search methods
    
    @organization_error_handler("search organizations", reraise=False, default_return=[])
    @log_organization_operation("search organizations", include_args=True, include_result_summary=True)
    async def search_organizations(self, 
                                 query: str, 
                                 filters: Optional[Dict[str, Any]] = None,
                                 limit: Optional[int] = None) -> List[Organization]:
        """Search organizations with flexible filters."""
        try:
            return await self._repository.search(query, filters, limit)
        except Exception as e:
            logger.error(f"Failed to search organizations with query '{query}': {e}")
            raise
    
    # Light vs Full search methods for performance optimization
    async def search_organizations_light(self, 
                                        query: str = None, 
                                        filters: Optional[Dict[str, Any]] = None,
                                        limit: int = 20,
                                        offset: int = 0) -> List[Organization]:
        """Search organizations with light data (9 fields) for efficient results."""
        try:
            return await self._repository.search_light(query, filters, limit, offset)
        except Exception as e:
            logger.error(f"Failed to search organizations (light) with query '{query}': {e}")
            raise
    
    async def search_organizations_full(self, 
                                       query: str = None, 
                                       filters: Optional[Dict[str, Any]] = None,
                                       limit: int = 20,
                                       offset: int = 0) -> List[Organization]:
        """Search organizations with full data (20+ fields) for complete results."""
        try:
            return await self._repository.search_full(query, filters, limit, offset)
        except Exception as e:
            logger.error(f"Failed to search organizations (full) with query '{query}': {e}")
            raise
    
    # Admin methods with include_deleted option
    async def get_active_organizations_light_admin(self, include_deleted: bool = False, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with light data including deleted ones for admins."""
        try:
            return await self._repository.find_active_light_admin(include_deleted, limit, offset)
        except Exception as e:
            logger.error(f"Failed to get active organizations (light admin): {e}")
            raise
    
    async def get_active_organizations_full_admin(self, include_deleted: bool = False, limit: int = 20, offset: int = 0) -> List[Organization]:
        """Get active organizations with full data including deleted ones for admins."""
        try:
            return await self._repository.find_active_full_admin(include_deleted, limit, offset)
        except Exception as e:
            logger.error(f"Failed to get active organizations (full admin): {e}")
            raise
    
    async def search_organizations_light_admin(self, 
                                              query: str = None, 
                                              filters: Optional[Dict[str, Any]] = None,
                                              include_deleted: bool = False,
                                              limit: int = 20,
                                              offset: int = 0) -> List[Organization]:
        """Search organizations with light data including deleted ones for admins."""
        try:
            return await self._repository.search_light_admin(query, filters, include_deleted, limit, offset)
        except Exception as e:
            logger.error(f"Failed to search organizations (light admin) with query '{query}': {e}")
            raise
    
    async def search_organizations_full_admin(self, 
                                             query: str = None, 
                                             filters: Optional[Dict[str, Any]] = None,
                                             include_deleted: bool = False,
                                             limit: int = 20,
                                             offset: int = 0) -> List[Organization]:
        """Search organizations with full data including deleted ones for admins."""
        try:
            return await self._repository.search_full_admin(query, filters, include_deleted, limit, offset)
        except Exception as e:
            logger.error(f"Failed to search organizations (full admin) with query '{query}': {e}")
            raise
    
    # Existence check methods
    
    async def organization_exists(self, organization_id: OrganizationId) -> bool:
        """Check if organization exists."""
        try:
            return await self._repository.exists(organization_id)
        except Exception as e:
            logger.error(f"Failed to check organization existence {organization_id}: {e}")
            return False
    
    async def slug_exists(self, slug: str, exclude_id: Optional[OrganizationId] = None) -> bool:
        """Check if slug is already taken."""
        try:
            return await self._repository.slug_exists(slug, exclude_id)
        except Exception as e:
            logger.error(f"Failed to check slug existence '{slug}': {e}")
            return False
    
    # Batch operations
    
    async def batch_get_by_ids(self, organization_ids: List[OrganizationId]) -> Dict[OrganizationId, Optional[Organization]]:
        """Batch get organizations by IDs.
        
        Retrieves multiple organizations from database in a single operation.
        
        Args:
            organization_ids: List of organization IDs to retrieve
            
        Returns:
            Dictionary mapping organization IDs to organizations (or None if not found)
        """
        if not organization_ids:
            return {}
        
        try:
            return await self._repository.batch_find_by_ids(organization_ids)
        except Exception as e:
            logger.error(f"Batch get by IDs failed: {e}")
            return {org_id: None for org_id in organization_ids}