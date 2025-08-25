"""Organization status service for lifecycle and verification operations.

Handles organization status changes including verification, activation, and deactivation.
Follows single responsibility principle for status management operations only.
"""

import logging
from typing import Optional, List

from ....core.value_objects import OrganizationId
from ....core.exceptions import EntityNotFoundError

from ..entities.organization import Organization
from ..entities.protocols import (
    OrganizationRepository,
    OrganizationNotificationService
)

logger = logging.getLogger(__name__)


class OrganizationStatusService:
    """Service for organization status and lifecycle operations.
    
    Handles verification, activation, deactivation and related
    status change operations with notifications.
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
    
    async def verify_organization(self, 
                                 organization_id: OrganizationId, 
                                 documents: List[str]) -> Organization:
        """Verify organization with documents."""
        try:
            # Get organization
            organization = await self._repository.find_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            # Perform verification
            organization.verify(documents)
            updated_organization = await self._repository.update(organization)
            
            # Send notification if available
            if self._notification_service:
                try:
                    await self._notification_service.notify_verification_completed(updated_organization)
                    logger.info(f"Verification notification sent for organization {organization_id}")
                except Exception as e:
                    logger.error(f"Failed to send verification notification for organization {organization_id}: {e}")
            
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
            # Get organization
            organization = await self._repository.find_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            # Perform deactivation
            organization.deactivate()
            updated_organization = await self._repository.update(organization)
            
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
            # Get organization
            organization = await self._repository.find_by_id(organization_id)
            if not organization:
                raise EntityNotFoundError(f"Organization {organization_id} not found")
            
            # Perform activation
            organization.activate()
            updated_organization = await self._repository.update(organization)
            
            logger.info(f"Activated organization {organization_id}")
            return updated_organization
            
        except Exception as e:
            logger.error(f"Failed to activate organization {organization_id}: {e}")
            raise