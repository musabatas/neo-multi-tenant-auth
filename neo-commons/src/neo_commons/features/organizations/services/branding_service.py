"""Organization branding service for visual identity and contact operations.

Handles organization branding, logos, colors, addresses and related
visual identity operations. Follows single responsibility principle.
"""

import logging
from typing import Optional, Dict, Any

from ....core.value_objects import OrganizationId
from ....core.exceptions import EntityNotFoundError, ValidationError

from ..entities.organization import Organization
from ..entities.protocols import (
    OrganizationRepository,
    OrganizationValidationService
)

logger = logging.getLogger(__name__)


class OrganizationBrandingService:
    """Service for organization branding and visual identity operations.
    
    Handles logo updates, brand colors, address information,
    and other visual/contact identity operations.
    """
    
    def __init__(
        self,
        repository: OrganizationRepository,
        validation_service: Optional[OrganizationValidationService] = None
    ):
        """Initialize with dependencies.
        
        Args:
            repository: Organization repository implementation
            validation_service: Optional validation service for address validation
        """
        self._repository = repository
        self._validation_service = validation_service
    
    async def update_organization_branding(self, 
                                          organization_id: OrganizationId, 
                                          logo_url: Optional[str] = None,
                                          brand_colors: Optional[Dict[str, str]] = None) -> Organization:
        """Update organization branding."""
        try:
            # Get organization
            organization = await self._repository.find_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            # Track changes
            changes = {}
            
            # Update logo URL
            if logo_url is not None:
                organization.logo_url = logo_url
                changes["logo_url"] = logo_url
            
            # Update brand colors
            if brand_colors:
                organization.update_brand_colors(brand_colors)
                changes["brand_colors"] = brand_colors
            
            # Save changes
            updated_organization = await self._repository.update(organization)
            
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
            # Get organization
            organization = await self._repository.find_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            # Validate address if validation service available
            if self._validation_service:
                validation_result = await self._validation_service.validate_address(address_fields)
                if not validation_result.get("valid", True):
                    raise ValidationError(f"Invalid address: {validation_result.get('error', 'Unknown error')}")
            
            # Update address
            organization.update_address(**address_fields)
            updated_organization = await self._repository.update(organization)
            
            logger.info(f"Updated address for organization {organization_id}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to update address for organization {organization_id}: {e}")
            raise