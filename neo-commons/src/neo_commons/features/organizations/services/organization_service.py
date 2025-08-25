"""Organization service implementation using existing neo-commons infrastructure.

This service orchestrates organization operations using dependency injection
without duplicating existing cache, database, or configuration logic.
Accepts flexible parameters and follows DRY principles throughout.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import replace

from ....core.value_objects import OrganizationId, UserId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, ValidationError
from ....features.pagination.entities import OffsetPaginationRequest, OffsetPaginationResponse
from ....features.pagination.protocols import PaginatedService

# Define organization-specific exceptions
class OrganizationNotFoundError(EntityNotFoundError):
    """Raised when organization is not found."""
    pass
from ..entities.organization import Organization
from ..entities.protocols import (
    OrganizationRepository, 
    OrganizationCache, 
    OrganizationConfigResolver,
    OrganizationNotificationService,
    OrganizationValidationService
)
from ..utils.validation import OrganizationValidationRules
from ..utils.error_handling import (
    organization_error_handler,
    handle_organization_service_errors, 
    log_organization_operation,
    OrganizationOperationContext
)
from ..utils.validation import OrganizationValidationRules
from ....utils import generate_uuid_v7


logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for organization operations using existing infrastructure.
    
    Orchestrates organization repository, cache, and configuration without
    duplicating existing neo-commons services. Accepts flexible parameters
    and handles all business logic with comprehensive error handling.
    """
    
    def __init__(
        self,
        repository: OrganizationRepository,
        cache: Optional[OrganizationCache] = None,
        config_resolver: Optional[OrganizationConfigResolver] = None,
        notification_service: Optional[OrganizationNotificationService] = None,
        validation_service: Optional[OrganizationValidationService] = None
    ):
        """Initialize with injected dependencies.
        
        Args:
            repository: Organization repository implementation
            cache: Optional organization cache implementation  
            config_resolver: Optional organization config resolver
            notification_service: Optional notification service
            validation_service: Optional validation service
        """
        self._repository = repository
        self._cache = cache
        self._config_resolver = config_resolver
        self._notification_service = notification_service
        self._validation_service = validation_service
    
    @organization_error_handler("create organization")
    @log_organization_operation("create organization", include_timing=True, include_result_summary=True)
    async def create_organization(
        self,
        name: str,
        slug: Optional[str] = None,
        **kwargs
    ) -> Organization:
        """Create new organization with flexible parameters."""
        try:
            # Generate slug from name if not provided
            if not slug:
                slug = OrganizationValidationRules.name_to_slug(name)
            else:
                slug = OrganizationValidationRules.validate_slug(slug)
            
            # Check if slug already exists
            existing = await self.get_by_slug(slug)
            if existing:
                raise EntityAlreadyExistsError("Organization", f"slug:{slug}")
            
            # Validate additional fields if validation service available
            if self._validation_service:
                await self._validate_organization_data(kwargs)
            
            # Create organization entity with validation
            org_id = OrganizationId(value=str(generate_uuid_v7()))
            validated_name = OrganizationValidationRules.validate_display_name(name)
            
            # Generate slug if not provided
            if slug is None:
                slug = OrganizationValidationRules.name_to_slug(validated_name)
            else:
                slug = OrganizationValidationRules.validate_slug(slug)
            
            # Create entity directly
            organization = Organization(
                id=org_id,
                name=validated_name,
                slug=slug,
                **kwargs
            )
            
            # Save to repository
            saved_organization = await self._repository.save(organization)
            
            # Cache if available
            if self._cache:
                await self._cache.set(saved_organization)
            
            # Send notification if available
            if self._notification_service:
                await self._notification_service.notify_organization_created(saved_organization)
            
            logger.info(f"Created organization {saved_organization.id} with slug '{slug}'")
            return saved_organization
            
        except Exception as e:
            logger.error(f"Failed to create organization with slug '{slug}': {e}")
            raise
    
    @organization_error_handler("get organization by ID", reraise=False, default_return=None)
    @log_organization_operation("get organization by ID", include_timing=True)
    async def get_by_id(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Get organization by ID with caching."""
        try:
            # Check cache first
            if self._cache:
                cached = await self._cache.get(organization_id)
                if cached:
                    return cached
            
            # Get from repository
            organization = await self._repository.find_by_id(organization_id)
            
            # Cache if found
            if organization and self._cache:
                await self._cache.set(organization)
            
            return organization
            
        except Exception as e:
            logger.error(f"Failed to get organization {organization_id}: {e}")
            raise
    
    @organization_error_handler("get organization by slug", reraise=False, default_return=None)
    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug with caching."""
        try:
            # Check cache first
            if self._cache:
                cached = await self._cache.get_by_slug(slug)
                if cached:
                    return cached
            
            # Get from repository
            organization = await self._repository.find_by_slug(slug)
            
            # Cache if found
            if organization and self._cache:
                await self._cache.set(organization)
            
            return organization
            
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
    
    async def get_active_organizations(self, limit: Optional[int] = None) -> List[Organization]:
        """Get active organizations."""
        try:
            return await self._repository.find_active(limit)
            
        except Exception as e:
            logger.error(f"Failed to get active organizations: {e}")
            raise
    
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
    
    @organization_error_handler("update organization")
    async def update_organization(self, organization: Organization, changes: Optional[Dict[str, Any]] = None) -> Organization:
        """Update organization with change tracking."""
        try:
            # Validate changes if validation service available
            if self._validation_service and changes:
                await self._validate_organization_data(changes)
            
            # Update in repository
            updated_organization = await self._repository.update(organization)
            
            # Invalidate cache
            if self._cache:
                await self._cache.delete(organization.id)
            
            # Send notification if available
            if self._notification_service and changes:
                await self._notification_service.notify_organization_updated(updated_organization, changes)
            
            logger.info(f"Updated organization {organization.id}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to update organization {organization.id}: {e}")
            raise
    
    @organization_error_handler("delete organization", reraise=True)
    async def delete_organization(self, organization_id: OrganizationId, hard_delete: bool = False) -> Optional[Organization]:
        """Delete organization (soft delete by default).
        
        Returns:
            Organization: The deleted organization for soft delete, None for hard delete
        """
        try:
            if hard_delete:
                # Hard delete
                result = await self._repository.delete(organization_id)
                if not result:
                    raise EntityNotFoundError("Organization", str(organization_id.value))
                deleted_org = None
            else:
                # Soft delete
                organization = await self.get_by_id(organization_id)
                if not organization:
                    raise EntityNotFoundError("Organization", str(organization_id.value))
                
                organization.soft_delete()
                deleted_org = await self._repository.update(organization)
            
            # Clear from cache
            if self._cache:
                await self._cache.delete(organization_id)
            
            logger.info(f"Deleted organization {organization_id} (hard={hard_delete})")
            return deleted_org
            
        except EntityNotFoundError:
            # Re-raise without logging - this is expected behavior for 404 responses
            raise
        except Exception as e:
            logger.error(f"Failed to delete organization {organization_id}: {e}")
            raise
    
    async def verify_organization(self, 
                                 organization_id: OrganizationId, 
                                 documents: List[str]) -> Organization:
        """Verify organization with documents."""
        try:
            organization = await self.get_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            # Perform verification
            organization.verify(documents)
            updated_organization = await self.update_organization(organization)
            
            # Send notification if available
            if self._notification_service:
                await self._notification_service.notify_verification_completed(updated_organization)
            
            logger.info(f"Verified organization {organization_id}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to verify organization {organization_id}: {e}")
            raise
    
    async def deactivate_organization(self, 
                                     organization_id: OrganizationId, 
                                     reason: Optional[str] = None) -> Organization:
        """Deactivate organization."""
        try:
            organization = await self.get_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            organization.deactivate()
            updated_organization = await self.update_organization(organization)
            
            # Send notification if available
            if self._notification_service:
                await self._notification_service.notify_organization_deactivated(updated_organization, reason)
            
            logger.info(f"Deactivated organization {organization_id}: {reason}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to deactivate organization {organization_id}: {e}")
            raise
    
    async def activate_organization(self, organization_id: OrganizationId) -> Organization:
        """Activate organization."""
        try:
            organization = await self.get_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            organization.activate()
            updated_organization = await self.update_organization(organization)
            
            logger.info(f"Activated organization {organization_id}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to activate organization {organization_id}: {e}")
            raise
    
    async def update_organization_branding(self, 
                                          organization_id: OrganizationId, 
                                          logo_url: Optional[str] = None,
                                          brand_colors: Optional[Dict[str, str]] = None) -> Organization:
        """Update organization branding."""
        try:
            organization = await self.get_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            changes = {}
            if logo_url is not None:
                organization.logo_url = logo_url
                changes["logo_url"] = logo_url
            
            if brand_colors:
                organization.update_brand_colors(brand_colors)
                changes["brand_colors"] = brand_colors
            
            updated_organization = await self.update_organization(organization, changes)
            
            logger.info(f"Updated branding for organization {organization_id}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to update branding for organization {organization_id}: {e}")
            raise
    
    async def update_organization_address(self, 
                                         organization_id: OrganizationId,
                                         **address_fields) -> Organization:
        """Update organization address with flexible fields."""
        try:
            organization = await self.get_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            # Validate address if validation service available
            if self._validation_service:
                validation_result = await self._validation_service.validate_address(address_fields)
                if not validation_result.get("valid", True):
                    raise ValidationError(f"Invalid address: {validation_result.get('error', 'Unknown error')}")
            
            organization.update_address(**address_fields)
            updated_organization = await self.update_organization(organization, {"address": address_fields})
            
            logger.info(f"Updated address for organization {organization_id}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to update address for organization {organization_id}: {e}")
            raise
    
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
    
    async def _validate_organization_data(self, data: Dict[str, Any]) -> None:
        """Validate organization data using validation service."""
        if not self._validation_service:
            return
        
        # Validate tax ID if provided
        if "tax_id" in data and "country_code" in data:
            tax_id = data["tax_id"]
            country_code = data["country_code"]
            if tax_id and country_code:
                is_valid = await self._validation_service.validate_tax_id(tax_id, country_code)
                if not is_valid:
                    raise ValidationError(f"Invalid tax ID '{tax_id}' for country '{country_code}'")
        
        # Validate website URL if provided
        if "website_url" in data and data["website_url"]:
            is_valid = await self._validation_service.validate_website(data["website_url"])
            if not is_valid:
                raise ValidationError(f"Invalid or inaccessible website URL: {data['website_url']}")
        
        # Validate business registration if all required fields present
        if all(field in data for field in ["legal_name", "tax_id", "country_code"]):
            legal_name = data["legal_name"]
            tax_id = data["tax_id"]
            country_code = data["country_code"]
            
            if legal_name and tax_id and country_code:
                result = await self._validation_service.validate_business_registration(
                    legal_name, tax_id, country_code
                )
                if not result.get("valid", True):
                    raise ValidationError(f"Business registration validation failed: {result.get('error', 'Unknown error')}")

    # Metadata-specific methods
    
    @handle_organization_service_errors
    async def update_metadata(
        self,
        organization_id: OrganizationId,
        metadata: Dict[str, Any],
        merge: bool = True
    ) -> Organization:
        """Update organization metadata.
        
        Args:
            organization_id: Organization ID
            metadata: Metadata to set or update
            merge: Whether to merge with existing metadata or replace completely
            
        Returns:
            Updated organization entity
            
        Raises:
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If metadata validation fails
        """
        try:
            # Get existing organization
            organization = await self.get_by_id(organization_id)
            if not organization:
                raise OrganizationNotFoundError(f"Organization {organization_id} not found")
            
            # Handle metadata update
            if merge and organization.metadata:
                # Deep merge metadata
                updated_metadata = self._deep_merge_metadata(organization.metadata, metadata)
            else:
                # Replace metadata entirely
                updated_metadata = metadata.copy()
            
            # Update organization with new metadata
            updates = {
                "metadata": updated_metadata,
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Update organization using dataclass replace
            updated_organization = replace(
                organization,
                metadata=updated_metadata,
                updated_at=datetime.now(timezone.utc)
            )
            
            # Save to repository
            saved = await self._repository.save(updated_organization)
            
            # Invalidate cache
            if self._cache:
                await self._cache.delete(organization_id)
            
            # Send notification
            if self._notification_service:
                await self._notification_service.on_organization_metadata_updated(saved)
            
            return saved
            
        except Exception as e:
            logger.error(f"Failed to update metadata for organization {organization_id}: {e}")
            raise
    
    @handle_organization_service_errors
    async def get_metadata(self, organization_id: OrganizationId) -> Dict[str, Any]:
        """Get organization metadata.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Organization metadata dictionary
            
        Raises:
            OrganizationNotFoundError: If organization doesn't exist
        """
        try:
            organization = await self.get_by_id(organization_id)
            if not organization:
                raise OrganizationNotFoundError(f"Organization {organization_id} not found")
            
            return organization.metadata or {}
            
        except Exception as e:
            logger.error(f"Failed to get metadata for organization {organization_id}: {e}")
            raise
    
    @handle_organization_service_errors
    async def search_by_metadata(
        self,
        metadata_filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0
    ) -> List[Organization]:
        """Search organizations by metadata filters.
        
        Args:
            metadata_filters: JSONB filters to apply
            limit: Maximum results to return
            offset: Results offset for pagination
            
        Returns:
            List of matching organizations
        """
        try:
            return await self._repository.search_by_metadata(metadata_filters, limit, offset)
            
        except Exception as e:
            logger.error(f"Failed to search organizations by metadata: {e}")
            raise
    
    @handle_organization_service_errors
    async def set_metadata_value(
        self,
        organization_id: OrganizationId,
        key: str,
        value: Any
    ) -> Organization:
        """Set a single metadata value.
        
        Args:
            organization_id: Organization ID
            key: Metadata key (supports dot notation for nested values)
            value: Value to set
            
        Returns:
            Updated organization entity
        """
        try:
            # Get current metadata
            current_metadata = await self.get_metadata(organization_id)
            
            # Set value using dot notation
            self._set_nested_value(current_metadata, key, value)
            
            # Update metadata
            return await self.update_metadata(organization_id, current_metadata, merge=False)
            
        except Exception as e:
            logger.error(f"Failed to set metadata value {key} for organization {organization_id}: {e}")
            raise
    
    @handle_organization_service_errors
    async def remove_metadata_key(
        self,
        organization_id: OrganizationId,
        key: str
    ) -> Organization:
        """Remove a metadata key.
        
        Args:
            organization_id: Organization ID
            key: Metadata key to remove (supports dot notation)
            
        Returns:
            Updated organization entity
        """
        try:
            # Get current metadata
            current_metadata = await self.get_metadata(organization_id)
            
            # Remove key using dot notation
            self._remove_nested_key(current_metadata, key)
            
            # Update metadata
            return await self.update_metadata(organization_id, current_metadata, merge=False)
            
        except Exception as e:
            logger.error(f"Failed to remove metadata key {key} for organization {organization_id}: {e}")
            raise
    
    def _deep_merge_metadata(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two metadata dictionaries.
        
        Args:
            existing: Existing metadata
            new: New metadata to merge
            
        Returns:
            Merged metadata dictionary
        """
        result = existing.copy()
        
        for key, value in new.items():
            if (
                key in result 
                and isinstance(result[key], dict) 
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge_metadata(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set a nested value using dot notation.
        
        Args:
            data: Dictionary to modify
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split('.')
        current = data
        
        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        
        # Set the final value
        current[keys[-1]] = value
    
    def _remove_nested_key(self, data: Dict[str, Any], key: str) -> None:
        """Remove a nested key using dot notation.
        
        Args:
            data: Dictionary to modify
            key: Dot-separated key path to remove
        """
        keys = key.split('.')
        current = data
        
        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                return  # Key doesn't exist
            current = current[k]
        
        # Remove the final key if it exists
        if keys[-1] in current:
            del current[keys[-1]]