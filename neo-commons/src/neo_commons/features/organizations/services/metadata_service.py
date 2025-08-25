"""Organization metadata service for JSONB operations.

Handles complex metadata operations including deep merging, dot notation,
and JSONB search operations. Follows single responsibility principle.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import replace

from ....core.value_objects import OrganizationId
from ....core.exceptions import EntityNotFoundError

from ..entities.organization import Organization
from ..entities.protocols import (
    OrganizationRepository,
    OrganizationNotificationService
)
from ..utils.error_handling import handle_organization_service_errors

logger = logging.getLogger(__name__)


# Define organization-specific exceptions
class OrganizationNotFoundError(EntityNotFoundError):
    """Raised when organization is not found."""
    pass


class OrganizationMetadataService:
    """Service for organization metadata operations.
    
    Handles complex JSONB metadata operations including deep merge,
    nested key operations, and metadata-based search.
    """
    
    def __init__(
        self,
        repository: OrganizationRepository,
        notification_service: Optional[OrganizationNotificationService] = None
    ):
        """Initialize with dependencies.
        
        Args:
            repository: Organization repository implementation
            notification_service: Optional notification service
        """
        self._repository = repository
        self._notification_service = notification_service
    
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
            organization = await self._repository.find_by_id(organization_id)
            if not organization:
                raise OrganizationNotFoundError(f"Organization {organization_id} not found")
            
            # Handle metadata update
            if merge and organization.metadata:
                # Deep merge metadata
                updated_metadata = self._deep_merge_metadata(organization.metadata, metadata)
            else:
                # Replace metadata entirely
                updated_metadata = metadata.copy()
            
            # Update organization using dataclass replace
            updated_organization = replace(
                organization,
                metadata=updated_metadata,
                updated_at=datetime.now(timezone.utc)
            )
            
            # Save to repository
            saved = await self._repository.save(updated_organization)
            
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
            organization = await self._repository.find_by_id(organization_id)
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