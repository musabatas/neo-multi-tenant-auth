"""Webhook event type service for event type management operations.

Handles webhook event type creation, updates, validation, and management.
Follows single responsibility principle for event type operations.
"""

import logging
from typing import List, Optional, Dict, Any

from ....core.value_objects import WebhookEventTypeId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, ValidationError
from ....utils import generate_uuid_v7

from ..entities.webhook_event_type import WebhookEventType
from ..entities.protocols import WebhookEventTypeRepository
from ..utils.validation import WebhookValidationRules
from ..utils.error_handling import handle_event_type_error

logger = logging.getLogger(__name__)


class WebhookEventTypeService:
    """Service for webhook event type operations.
    
    Handles event type creation, updates, validation, and management
    with proper validation and error handling.
    """
    
    def __init__(self, repository: WebhookEventTypeRepository):
        """Initialize with repository dependency.
        
        Args:
            repository: Webhook event type repository implementation
        """
        self._repository = repository
    
    async def create_event_type(
        self,
        event_type: str,
        display_name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        is_enabled: bool = True,
        requires_verification: bool = False,
        payload_schema: Optional[Dict[str, Any]] = None,
        example_payload: Optional[Dict[str, Any]] = None
    ) -> WebhookEventType:
        """Create a new webhook event type.
        
        Args:
            event_type: Event type identifier (e.g., 'organization.created')
            display_name: Human-readable display name
            description: Optional description
            category: Optional category (auto-extracted from event_type if not provided)
            is_enabled: Whether event type is enabled
            requires_verification: Whether endpoints must be verified to subscribe
            payload_schema: Optional JSON schema for payload validation
            example_payload: Optional example payload
            
        Returns:
            Created webhook event type
        """
        try:
            # Validate inputs
            validated_event_type = WebhookValidationRules.validate_event_type(event_type)
            
            if not display_name or not display_name.strip():
                raise ValidationError("Display name cannot be empty")
            
            # Check if event type already exists
            existing = await self._repository.get_by_event_type(validated_event_type)
            if existing:
                raise EntityAlreadyExistsError("WebhookEventType", f"event_type={validated_event_type}")
            
            # Create event type entity
            type_id = WebhookEventTypeId(value=generate_uuid_v7())
            
            webhook_event_type = WebhookEventType(
                id=type_id,
                event_type=validated_event_type,
                category=category,  # Will be auto-extracted in __post_init__
                display_name=display_name.strip(),
                description=description,
                is_enabled=is_enabled,
                requires_verification=requires_verification,
                payload_schema=payload_schema,
                example_payload=example_payload
            )
            
            # Save event type
            saved_event_type = await self._repository.save(webhook_event_type)
            
            logger.info(f"Created webhook event type {type_id}: {validated_event_type}")
            return saved_event_type
            
        except Exception as e:
            handle_event_type_error("create_event_type", None, e, {
                "event_type": event_type,
                "display_name": display_name
            })
            raise
    
    async def update_event_type(
        self,
        type_id: WebhookEventTypeId,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        requires_verification: Optional[bool] = None,
        payload_schema: Optional[Dict[str, Any]] = None,
        example_payload: Optional[Dict[str, Any]] = None
    ) -> WebhookEventType:
        """Update a webhook event type.
        
        Args:
            type_id: ID of event type to update
            display_name: Optional new display name
            description: Optional new description
            is_enabled: Optional new enabled status
            requires_verification: Optional new verification requirement
            payload_schema: Optional new payload schema
            example_payload: Optional new example payload
            
        Returns:
            Updated webhook event type
        """
        try:
            # Get existing event type
            event_type = await self._repository.get_by_id(type_id)
            if not event_type:
                raise EntityNotFoundError("WebhookEventType", str(type_id.value))
            
            # Update fields
            if display_name is not None:
                if not display_name or not display_name.strip():
                    raise ValidationError("Display name cannot be empty")
                event_type.display_name = display_name.strip()
            
            if description is not None:
                event_type.description = description
            
            if is_enabled is not None:
                if is_enabled != event_type.is_enabled:
                    if is_enabled:
                        event_type.enable()
                    else:
                        event_type.disable()
            
            if requires_verification is not None:
                if requires_verification != event_type.requires_verification:
                    if requires_verification:
                        event_type.require_verification()
                    else:
                        event_type.remove_verification_requirement()
            
            if payload_schema is not None or example_payload is not None:
                event_type.update_schema(payload_schema, example_payload)
            
            # Save updated event type (using update method from repository)
            # Note: The repository update method should exist, following organizations pattern
            try:
                updated_event_type = await self._repository.update(event_type)
            except AttributeError:
                # Fallback if update method not implemented - use save
                updated_event_type = await self._repository.save(event_type)
            
            logger.info(f"Updated webhook event type {type_id}")
            return updated_event_type
            
        except Exception as e:
            handle_event_type_error("update_event_type", type_id, e, {})
            raise
    
    async def delete_event_type(self, type_id: WebhookEventTypeId) -> bool:
        """Delete a webhook event type.
        
        Args:
            type_id: ID of event type to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            result = await self._repository.delete(type_id)
            
            if result:
                logger.info(f"Deleted webhook event type {type_id}")
            else:
                logger.warning(f"Webhook event type {type_id} not found for deletion")
            
            return result
            
        except Exception as e:
            handle_event_type_error("delete_event_type", type_id, e, {})
            raise
    
    async def enable_event_type(self, type_id: WebhookEventTypeId) -> WebhookEventType:
        """Enable a webhook event type.
        
        Args:
            type_id: ID of event type to enable
            
        Returns:
            Updated webhook event type
        """
        try:
            event_type = await self._repository.get_by_id(type_id)
            if not event_type:
                raise EntityNotFoundError("WebhookEventType", str(type_id.value))
            
            if not event_type.is_enabled:
                event_type.enable()
                
                try:
                    event_type = await self._repository.update(event_type)
                except AttributeError:
                    event_type = await self._repository.save(event_type)
                
                logger.info(f"Enabled webhook event type {type_id}")
            
            return event_type
            
        except Exception as e:
            handle_event_type_error("enable_event_type", type_id, e, {})
            raise
    
    async def disable_event_type(self, type_id: WebhookEventTypeId) -> WebhookEventType:
        """Disable a webhook event type.
        
        Args:
            type_id: ID of event type to disable
            
        Returns:
            Updated webhook event type
        """
        try:
            event_type = await self._repository.get_by_id(type_id)
            if not event_type:
                raise EntityNotFoundError("WebhookEventType", str(type_id.value))
            
            if event_type.is_enabled:
                event_type.disable()
                
                try:
                    event_type = await self._repository.update(event_type)
                except AttributeError:
                    event_type = await self._repository.save(event_type)
                
                logger.info(f"Disabled webhook event type {type_id}")
            
            return event_type
            
        except Exception as e:
            handle_event_type_error("disable_event_type", type_id, e, {})
            raise
    
    async def get_enabled_types(self) -> List[WebhookEventType]:
        """Get all enabled webhook event types.
        
        Returns:
            List of enabled webhook event types
        """
        try:
            return await self._repository.get_enabled_types()
            
        except Exception as e:
            handle_event_type_error("get_enabled_types", None, e, {})
            raise
    
    async def get_by_category(
        self, 
        category: str, 
        enabled_only: bool = True
    ) -> List[WebhookEventType]:
        """Get webhook event types by category.
        
        Args:
            category: Category to filter by
            enabled_only: Whether to return only enabled types
            
        Returns:
            List of webhook event types in category
        """
        try:
            return await self._repository.get_by_category(category, enabled_only)
            
        except Exception as e:
            handle_event_type_error("get_by_category", None, e, {
                "category": category,
                "enabled_only": enabled_only
            })
            raise
    
    async def get_available_categories(self) -> List[str]:
        """Get all available event type categories.
        
        Returns:
            List of unique categories
        """
        try:
            # Get all enabled event types and extract unique categories
            event_types = await self._repository.get_enabled_types()
            categories = list(set(et.category for et in event_types if et.category))
            categories.sort()
            
            logger.debug(f"Found {len(categories)} event type categories")
            return categories
            
        except Exception as e:
            handle_event_type_error("get_available_categories", None, e, {})
            raise
    
    async def validate_subscription_allowed(
        self, 
        type_id: WebhookEventTypeId, 
        endpoint_is_verified: bool
    ) -> bool:
        """Check if subscription is allowed for an event type.
        
        Args:
            type_id: Event type ID
            endpoint_is_verified: Whether the subscribing endpoint is verified
            
        Returns:
            True if subscription is allowed
        """
        try:
            event_type = await self._repository.get_by_id(type_id)
            if not event_type:
                raise EntityNotFoundError("WebhookEventType", str(type_id.value))
            
            return event_type.is_subscription_allowed(endpoint_is_verified)
            
        except Exception as e:
            handle_event_type_error("validate_subscription_allowed", type_id, e, {
                "endpoint_is_verified": endpoint_is_verified
            })
            raise