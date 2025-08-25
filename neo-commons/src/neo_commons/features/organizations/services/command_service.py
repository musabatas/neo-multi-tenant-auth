"""Organization command service for write operations.

Handles create, update, and delete operations with validation and notifications.
Follows single responsibility principle for command operations only.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from ....core.value_objects import OrganizationId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, ValidationError
from ....utils import generate_uuid_v7

from ..entities.organization import Organization
from ..entities.protocols import (
    OrganizationRepository,
    OrganizationNotificationService,
    OrganizationValidationService
)
from ..utils.validation import OrganizationValidationRules
from ..utils.error_handling import (
    organization_error_handler,
    log_organization_operation
)

logger = logging.getLogger(__name__)


class OrganizationCommandService:
    """Service for organization write operations.
    
    Handles create, update, and delete operations with validation,
    notifications, and webhook integration.
    """
    
    def __init__(
        self,
        repository: OrganizationRepository,
        notification_service: Optional[OrganizationNotificationService] = None,
        validation_service: Optional[OrganizationValidationService] = None
    ):
        """Initialize with dependencies.
        
        Args:
            repository: Organization repository implementation
            notification_service: Optional notification service
            validation_service: Optional validation service
        """
        self._repository = repository
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
            # Validate name
            validated_name = OrganizationValidationRules.validate_display_name(name)
            
            # Generate or validate slug
            if not slug:
                slug = OrganizationValidationRules.name_to_slug(validated_name)
            else:
                slug = OrganizationValidationRules.validate_slug(slug)
            
            # Check if slug already exists
            existing = await self._repository.find_by_slug(slug)
            if existing:
                raise EntityAlreadyExistsError("Organization", f"slug:{slug}")
            
            # Validate additional fields if validation service available
            if self._validation_service:
                await self._validate_organization_data(kwargs)
            
            # Create organization entity
            org_id = OrganizationId(value=str(generate_uuid_v7()))
            organization = Organization(
                id=org_id,
                name=validated_name,
                slug=slug,
                **kwargs
            )
            
            # Save to repository
            saved_organization = await self._repository.save(organization)
            
            # Send notification if available
            if self._notification_service:
                try:
                    await self._notification_service.notify_organization_created(saved_organization)
                    logger.info(f"Organization creation notification sent for {saved_organization.id}")
                except Exception as e:
                    logger.error(f"Failed to send creation notification for organization {saved_organization.id}: {e}")
            
            # Send webhook notification
            try:
                await self._send_organization_webhook("created", saved_organization)
            except Exception as e:
                # Webhook failures shouldn't block organization creation
                logger.error(f"Failed to send webhook for organization creation {saved_organization.id}: {e}")
            
            logger.info(f"Created organization {saved_organization.id} with slug '{slug}'")
            return saved_organization
            
        except Exception as e:
            logger.error(f"Failed to create organization with slug '{slug}': {e}")
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
                # Soft delete - get organization first
                organization = await self._repository.find_by_id(organization_id)
                if not organization:
                    raise EntityNotFoundError("Organization", str(organization_id.value))
                
                organization.soft_delete()
                deleted_org = await self._repository.update(organization)
            
            logger.info(f"Deleted organization {organization_id} (hard={hard_delete})")
            return deleted_org
            
        except EntityNotFoundError:
            # Re-raise without logging - this is expected behavior for 404 responses
            raise
        except Exception as e:
            logger.error(f"Failed to delete organization {organization_id}: {e}")
            raise
    
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
    
    async def _send_organization_webhook(self, event_type: str, organization: Organization):
        """Send webhook notification for organization events.
        
        Args:
            event_type: Type of event (created, updated, verified, deleted)
            organization: Organization entity
        """
        try:
            # Simulate webhook payload creation
            webhook_payload = {
                "event": f"organization.{event_type}",
                "data": {
                    "id": str(organization.id.value),
                    "name": organization.name,
                    "slug": organization.slug,
                    "is_active": organization.is_active,
                    "verified_at": organization.verified_at.isoformat() if organization.verified_at else None,
                    "created_at": organization.created_at.isoformat(),
                    "updated_at": organization.updated_at.isoformat()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Send webhook
            await self._send_webhook_request(webhook_payload)
            
            logger.info(f"Webhook sent for organization {event_type}: {organization.id}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook for organization {event_type} {organization.id}: {e}")
            # Don't re-raise - webhook failures shouldn't break business logic
    
    async def _send_webhook_request(self, payload: Dict[str, Any]) -> bool:
        """Simulate sending webhook request to external service.
        
        This would typically make an HTTP request to configured webhook URLs.
        """
        import asyncio
        import random
        
        # Simulate network delay and potential failures
        await asyncio.sleep(0.1 + random.random() * 0.2)  # 100-300ms delay
        
        # Simulate occasional failures (10% failure rate)
        if random.random() < 0.1:
            raise Exception("Webhook service temporarily unavailable")
        
        logger.debug(f"Webhook request sent successfully: {payload.get('event', 'unknown')}")
        return True