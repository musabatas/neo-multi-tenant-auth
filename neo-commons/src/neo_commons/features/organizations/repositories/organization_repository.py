"""Organization repository implementation using existing database infrastructure.

This implementation leverages the existing database service from neo-commons
without duplicating connection management or query logic. Accepts any database
connection and schema name as parameters for maximum flexibility.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ....core.value_objects import OrganizationId, UserId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ....features.pagination.entities import OffsetPaginationRequest, OffsetPaginationResponse
from ....features.pagination.mixins import PaginatedRepositoryMixin
from ....features.pagination.protocols import PaginatedRepository
from ..entities.organization import Organization
from ..utils.queries import (
    ORGANIZATION_INSERT,
    ORGANIZATION_UPDATE, 
    ORGANIZATION_GET_BY_ID,
    ORGANIZATION_GET_BY_SLUG,
    ORGANIZATION_GET_BY_PRIMARY_CONTACT,
    ORGANIZATION_LIST_ALL,
    ORGANIZATION_LIST_PAGINATED,
    ORGANIZATION_COUNT_ALL,
    ORGANIZATION_DELETE_HARD,
    ORGANIZATION_EXISTS_BY_ID,
    ORGANIZATION_EXISTS_BY_SLUG,
    ORGANIZATION_SEARCH_BY_METADATA,
    ORGANIZATION_SEARCH_ADVANCED,
    ORGANIZATION_VALIDATE_UNIQUE_SLUG
)
from ..utils.error_handling import (
    handle_organization_retrieval_error
)



logger = logging.getLogger(__name__)


class OrganizationDatabaseRepository(PaginatedRepositoryMixin[Organization]):
    """Database repository for organization operations with pagination support.
    
    Uses existing database infrastructure without duplication.
    Accepts any database connection and schema via dependency injection.
    Follows DRY principles by reusing existing database patterns.
    Implements PaginatedRepository protocol for standardized pagination.
    """
    
    def __init__(self, database_repository: DatabaseRepository, schema: str):
        """Initialize with existing database repository.
        
        Args:
            database_repository: Database repository from neo-commons
            schema: Database schema name (flexible, not hardcoded)
        """
        self._db = database_repository
        self._schema = schema
        self._table = f"{schema}.organizations"
    
    async def save(self, organization: Organization) -> Organization:
        """Save organization to database."""
        try:
            # Check if organization already exists
            existing = await self.find_by_id(organization.id)
            if existing:
                raise EntityAlreadyExistsError("Organization", str(organization.id.value))
            
            # Check if slug is already taken
            slug_taken = await self.slug_exists(organization.slug)
            if slug_taken:
                raise EntityAlreadyExistsError("Organization", f"slug:{organization.slug}")
            
            query = ORGANIZATION_INSERT.format(schema=self._schema)
            
            import json
            params = [
                str(organization.id.value), organization.name, organization.slug, 
                organization.legal_name, organization.tax_id, organization.business_type,
                organization.industry, organization.company_size, organization.website_url,
                organization.primary_contact_id, organization.address_line1, organization.address_line2,
                organization.city, organization.state_province, organization.postal_code,
                organization.country_code, organization.default_timezone, organization.default_locale,
                organization.default_currency, organization.logo_url, json.dumps(organization.brand_colors or {}),
                organization.is_active, organization.verified_at, 
                organization.verification_documents or [], json.dumps(organization.metadata or {}),
                organization.created_at, organization.updated_at
            ]
            
            result = await self._db.execute_query(query, params)
            if result:
                logger.info(f"Created organization {organization.id} with slug '{organization.slug}'")
                return organization
            
            raise DatabaseError("Failed to create organization")
            
        except Exception as e:
            logger.error(f"Failed to save organization {organization.id}: {e}")
            raise DatabaseError(f"Failed to save organization: {e}")
    
    @handle_organization_retrieval_error
    async def find_by_id(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Find organization by ID."""
        query = ORGANIZATION_GET_BY_ID.format(schema=self._schema)
        result = await self._db.fetch_one(query, [str(organization_id.value)])
        
        if result:
            return self._map_row_to_organization(result)
        
        return None
    
    @handle_organization_retrieval_error
    async def find_by_slug(self, slug: str) -> Optional[Organization]:
        """Find organization by slug."""
        query = ORGANIZATION_GET_BY_SLUG.format(schema=self._schema)
        result = await self._db.fetch_one(query, [slug])
        
        if result:
            return self._map_row_to_organization(result)
        
        return None
    
    async def find_by_primary_contact(self, user_id: UserId) -> List[Organization]:
        """Find organizations where user is primary contact."""
        try:
            query = ORGANIZATION_GET_BY_PRIMARY_CONTACT.format(schema=self._schema)
            results = await self._db.fetch_all(query, [str(user_id.value)])
            
            return [self._map_row_to_organization(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to find organizations for user {user_id}: {e}")
            raise DatabaseError(f"Failed to find organizations for user: {e}")
    
    async def find_active(self, limit: Optional[int] = None) -> List[Organization]:
        """Find active organizations."""
        try:
            query = ORGANIZATION_LIST_ALL.format(schema=self._schema)
            
            if limit:
                results = await self._db.fetch_all(query, [limit, 0])
            else:
                results = await self._db.fetch_all(query, [1000, 0])  # Default limit
            
            return [self._map_row_to_organization(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to find active organizations: {e}")
            raise DatabaseError(f"Failed to find active organizations: {e}")
    
    async def find_paginated(
        self,
        pagination: OffsetPaginationRequest
    ) -> OffsetPaginationResponse[Organization]:
        """Find organizations with standardized pagination.
        
        Args:
            pagination: Pagination request with filters and sorting
            
        Returns:
            Paginated response with organizations and metadata
        """
        # Build base query for active organizations
        base_query = f"SELECT * FROM {{schema}}.organizations WHERE is_active = true AND deleted_at IS NULL"
        count_query = f"SELECT COUNT(*) as count FROM {{schema}}.organizations WHERE is_active = true AND deleted_at IS NULL"
        
        # Use pagination mixin for standardized database-level pagination
        return await super().find_paginated(
            pagination=pagination,
            base_query=base_query,
            count_query=count_query
        )
    
    async def find_active_paginated(
        self, 
        page: int = 1, 
        per_page: int = 50, 
        order_by: str = "name ASC"
    ) -> tuple[List[Organization], int]:
        """Find active organizations with legacy pagination format.
        
        Args:
            page: Page number (1-based)
            per_page: Number of organizations per page
            order_by: SQL ORDER BY clause (e.g., "name ASC", "created_at DESC")
            
        Returns:
            Tuple of (organizations list, total count)
            
        Note:
            This method maintains backward compatibility. New code should use find_paginated().
        """
        from ....features.pagination.entities import OffsetPaginationRequest, SortField, SortOrder
        
        # Convert legacy parameters to new pagination format
        sort_field_name, sort_order = order_by.split()
        pagination = OffsetPaginationRequest(
            page=page,
            per_page=per_page,
            sort_fields=[SortField(
                field=sort_field_name,
                order=SortOrder.ASC if sort_order.upper() == "ASC" else SortOrder.DESC
            )]
        )
        
        response = await self.find_paginated(pagination)
        return response.items, response.total
    
    async def find_verified(self, limit: Optional[int] = None) -> List[Organization]:
        """Find verified organizations."""
        try:
            # Use advanced search with verification filter
            query = ORGANIZATION_SEARCH_ADVANCED.format(schema=self._schema)
            search_limit = limit if limit else 1000
            params = [None, None, None, True, True, search_limit, 0]  # name, industry, country, verified_filter, is_active, limit, offset
            
            results = await self._db.fetch_all(query, params)
            return [self._map_row_to_organization(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to find verified organizations: {e}")
            raise DatabaseError(f"Failed to find verified organizations: {e}")
    
    async def find_by_industry(self, industry: str) -> List[Organization]:
        """Find organizations by industry."""
        try:
            # Use advanced search with industry filter
            query = ORGANIZATION_SEARCH_ADVANCED.format(schema=self._schema)
            params = [None, industry, None, None, True, 1000, 0]  # name, industry, country, verified, active, limit, offset
            
            results = await self._db.fetch_all(query, params)
            return [self._map_row_to_organization(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to find organizations by industry {industry}: {e}")
            raise DatabaseError(f"Failed to find organizations by industry: {e}")
    
    async def find_by_country(self, country_code: str) -> List[Organization]:
        """Find organizations by country code."""
        try:
            # Use advanced search with country filter
            query = ORGANIZATION_SEARCH_ADVANCED.format(schema=self._schema)
            params = [None, None, country_code, None, True, 1000, 0]  # name, industry, country, verified, active, limit, offset
            
            results = await self._db.fetch_all(query, params)
            return [self._map_row_to_organization(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to find organizations by country {country_code}: {e}")
            raise DatabaseError(f"Failed to find organizations by country: {e}")
    
    async def search(self, 
                    query: str, 
                    filters: Optional[Dict[str, Any]] = None,
                    limit: Optional[int] = None) -> List[Organization]:
        """Search organizations by name/slug with optional filters."""
        try:
            # Use advanced search query with filters
            search_query = ORGANIZATION_SEARCH_ADVANCED.format(schema=self._schema)
            
            # Extract filter values
            name_filter = f"%{query}%" if query else None
            industry_filter = filters.get("industry") if filters else None
            country_filter = filters.get("country_code") if filters else None
            verified_filter = filters.get("is_verified") if filters else None
            # Default to active=True if not specified (maintain backward compatibility)
            active_filter = filters.get("is_active", True) if filters else True
            
            # Set limit and offset
            search_limit = limit if limit else 1000
            search_offset = 0
            
            params = [name_filter, industry_filter, country_filter, verified_filter, active_filter, search_limit, search_offset]
            
            results = await self._db.fetch_all(search_query, params)
            return [self._map_row_to_organization(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to search organizations with query '{query}': {e}")
            raise DatabaseError(f"Failed to search organizations: {e}")
    
    async def update(self, organization: Organization) -> Organization:
        """Update organization."""
        try:
            # Update timestamp
            organization.updated_at = datetime.now(organization.updated_at.tzinfo)
            
            query = ORGANIZATION_UPDATE.format(schema=self._schema)
            
            import json
            params = [
                str(organization.id.value), organization.name, organization.legal_name,
                organization.tax_id, organization.business_type, organization.industry, 
                organization.company_size, organization.website_url, organization.primary_contact_id,
                organization.address_line1, organization.address_line2, organization.city,
                organization.state_province, organization.postal_code, organization.country_code,
                organization.default_timezone, organization.default_locale, organization.default_currency,
                organization.logo_url, json.dumps(organization.brand_colors or {}), 
                organization.is_active, organization.deleted_at, json.dumps(organization.metadata or {}),
                organization.updated_at
            ]
            
            result = await self._db.execute_query(query, params)
            if result:
                logger.info(f"Updated organization {organization.id}")
                return organization
            
            raise EntityNotFoundError(f"Organization {organization.id} not found")
            
        except Exception as e:
            logger.error(f"Failed to update organization {organization.id}: {e}")
            raise DatabaseError(f"Failed to update organization: {e}")
    
    async def delete(self, organization_id: OrganizationId) -> bool:
        """Hard delete organization."""
        try:
            query = ORGANIZATION_DELETE_HARD.format(schema=self._schema)
            result = await self._db.execute_query(query, [str(organization_id.value)])
            
            if result:
                logger.info(f"Deleted organization {organization_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete organization {organization_id}: {e}")
            raise DatabaseError(f"Failed to delete organization: {e}")
    
    async def exists(self, organization_id: OrganizationId) -> bool:
        """Check if organization exists."""
        try:
            query = ORGANIZATION_EXISTS_BY_ID.format(schema=self._schema)
            result = await self._db.fetch_one(query, [str(organization_id.value)])
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to check organization existence {organization_id}: {e}")
            raise DatabaseError(f"Failed to check organization existence: {e}")
    
    async def slug_exists(self, slug: str, exclude_id: Optional[OrganizationId] = None) -> bool:
        """Check if slug is already taken."""
        try:
            # ORGANIZATION_EXISTS_BY_SLUG already imported at top
            
            if exclude_id:
                # For exclude_id case, use centralized validation query
                query = ORGANIZATION_VALIDATE_UNIQUE_SLUG.format(schema=self._schema)
                params = [slug, str(exclude_id.value)]
            else:
                # Use centralized query for simple case
                query = ORGANIZATION_EXISTS_BY_SLUG.format(schema=self._schema)
                params = [slug]
            # params already set above based on exclude_id condition
            
            result = await self._db.fetch_one(query, params)
            # EXISTS query returns {"exists": boolean}, not None/row
            return result and (result.get("exists", False) if isinstance(result, dict) else result[0])
            
        except Exception as e:
            logger.error(f"Failed to check slug existence '{slug}': {e}")
            raise DatabaseError(f"Failed to check slug existence: {e}")
    
    def _map_row_to_organization(self, row: Dict[str, Any]) -> Organization:
        """Map database row to Organization entity."""
        return Organization(
            id=OrganizationId(row["id"]),
            name=row["name"],
            slug=row["slug"],
            legal_name=row.get("legal_name"),
            tax_id=row.get("tax_id"),
            business_type=row.get("business_type"),
            industry=row.get("industry"),
            company_size=row.get("company_size"),
            website_url=row.get("website_url"),
            primary_contact_id=row.get("primary_contact_id"),
            address_line1=row.get("address_line1"),
            address_line2=row.get("address_line2"),
            city=row.get("city"),
            state_province=row.get("state_province"),
            postal_code=row.get("postal_code"),
            country_code=row.get("country_code"),
            default_timezone=row.get("default_timezone", "UTC"),
            default_locale=row.get("default_locale", "en-US"),
            default_currency=row.get("default_currency", "USD"),
            logo_url=row.get("logo_url"),
            brand_colors=row.get("brand_colors") or {},
            is_active=row.get("is_active", True),
            verified_at=row.get("verified_at"),
            verification_documents=row.get("verification_documents") or [],
            metadata=row.get("metadata") or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row.get("deleted_at")
        )
    
    def _map_row_to_entity(self, row: Dict[str, Any]) -> Organization:
        """Map database row to entity (required by PaginatedRepositoryMixin)."""
        return self._map_row_to_organization(row)
    
    async def search_by_metadata(
        self,
        metadata_filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0
    ) -> List[Organization]:
        """Search organizations by metadata filters using JSONB operators.
        
        Args:
            metadata_filters: Dictionary of metadata filters
            limit: Maximum results to return
            offset: Results offset for pagination
            
        Returns:
            List of matching organizations
            
        Raises:
            DatabaseError: If query execution fails
        """
        try:
            query = ORGANIZATION_SEARCH_BY_METADATA.format(schema=self._schema)
            
            # Convert metadata filters to JSONB parameter
            import json
            metadata_json = json.dumps(metadata_filters)
            
            rows = await self._db.fetch_all(
                query,
                [metadata_json, limit, offset]
            )
            
            organizations = [self._map_row_to_organization(dict(row)) for row in rows]
            logger.info(f"Found {len(organizations)} organizations matching metadata filters")
            
            return organizations
            
        except Exception as e:
            logger.error(f"Failed to search organizations by metadata: {e}")
            raise DatabaseError(f"Failed to search organizations by metadata: {e}")