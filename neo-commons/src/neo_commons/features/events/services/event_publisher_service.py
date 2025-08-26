"""Event publisher service for creating and publishing domain events.

Handles event creation, validation, and publishing operations.
Follows single responsibility principle for event publishing operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from ....core.value_objects import EventId, EventType, UserId
from ....core.exceptions import ValidationError, EntityAlreadyExistsError
from ....utils import generate_uuid_v7

from ..entities.domain_event import DomainEvent
from ..entities.protocols import EventRepository, EventPublisher
from ..utils.validation import DomainEventValidationRules
from ..utils.error_handling import handle_event_error

logger = logging.getLogger(__name__)


class EventPublisherService:
    """Service for event publishing operations.
    
    Handles creation, validation, and publishing of domain events
    with proper error handling and logging.
    """
    
    def __init__(self, repository: EventRepository):
        """Initialize with repository dependency.
        
        Args:
            repository: Event repository implementation
        """
        self._repository = repository
    
    async def publish(self, event: DomainEvent) -> bool:
        """Publish a domain event.
        
        Args:
            event: Domain event to publish
            
        Returns:
            True if published successfully
        """
        try:
            # Save event to repository
            saved_event = await self._repository.save(event)
            
            logger.info(f"Event published: {saved_event.event_type.value} for {saved_event.aggregate_type}:{saved_event.aggregate_id}")
            return True
            
        except Exception as e:
            handle_event_error("publish", event.id, e, {
                "event_type": event.event_type.value,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": str(event.aggregate_id)
            })
            raise
    
    async def publish_batch(self, events: List[DomainEvent]) -> int:
        """Publish multiple domain events. Returns count of successfully published events.
        
        Args:
            events: List of domain events to publish
            
        Returns:
            Count of successfully published events
        """
        if not events:
            return 0
        
        published_count = 0
        failed_events = []
        
        for event in events:
            try:
                await self.publish(event)
                published_count += 1
            except Exception as e:
                failed_events.append(event.id)
                logger.error(f"Failed to publish event {event.id}: {e}")
        
        if failed_events:
            logger.warning(f"Batch publish completed: {published_count}/{len(events)} events published. Failed: {failed_events}")
        else:
            logger.info(f"Batch publish completed: {published_count}/{len(events)} events published successfully")
        
        return published_count
    
    async def create_and_publish(
        self,
        event_type: str,
        aggregate_type: str, 
        aggregate_id: UUID,
        event_data: Dict[str, Any],
        triggered_by_user_id: Optional[UserId] = None,
        context_id: Optional[UUID] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None,
        event_name: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> DomainEvent:
        """Create and publish a domain event in one operation.
        
        Args:
            event_type: Type of event (e.g., 'organization.created')
            aggregate_type: Type of aggregate that triggered the event
            aggregate_id: ID of the aggregate
            event_data: Event payload data
            triggered_by_user_id: Optional user who triggered the event
            context_id: Optional context ID (organization, tenant, etc.)
            correlation_id: Optional correlation ID for tracking related events
            causation_id: Optional ID of event that caused this event
            event_name: Optional human-readable event name
            event_metadata: Optional event metadata
            
        Returns:
            Created and published domain event
        """
        try:
            # Validate event type
            try:
                DomainEventValidationRules.validate_event_type(event_type)
            except ValueError as e:
                raise ValidationError(f"Invalid event type: {e}")
            
            # Validate aggregate type
            try:
                DomainEventValidationRules.validate_aggregate_type(aggregate_type)
            except ValueError as e:
                raise ValidationError(f"Invalid aggregate type: {e}")
            
            # Validate event data
            if event_data:
                try:
                    DomainEventValidationRules.validate_event_data(event_data)
                except ValueError as e:
                    raise ValidationError(f"Invalid event data: {e}")
            
            # Create event entity
            event_id = EventId(value=generate_uuid_v7())
            
            event = DomainEvent(
                id=event_id,
                event_type=EventType(event_type),
                event_name=event_name,
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                event_data=event_data or {},
                event_metadata=event_metadata or {},
                correlation_id=correlation_id,
                causation_id=causation_id,
                triggered_by_user_id=triggered_by_user_id,
                context_id=context_id,
                occurred_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            
            # Publish the event
            await self.publish(event)
            
            logger.info(f"Created and published event: {event.event_type.value} for {event.aggregate_type}:{event.aggregate_id}")
            return event
            
        except Exception as e:
            handle_event_error("create_and_publish", None, e, {
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": str(aggregate_id)
            })
            raise
    
    async def create_organization_event(
        self,
        event_action: str,
        organization_id: UUID,
        event_data: Dict[str, Any],
        triggered_by_user_id: Optional[UserId] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None
    ) -> DomainEvent:
        """Convenience method to create organization-related events.
        
        Args:
            event_action: Action that occurred (e.g., 'created', 'updated', 'deleted')
            organization_id: Organization ID
            event_data: Event payload data
            triggered_by_user_id: Optional user who triggered the event
            correlation_id: Optional correlation ID
            causation_id: Optional causation ID
            
        Returns:
            Created and published domain event
        """
        event_type = f"organization.{event_action}"
        event_name = f"Organization {event_action.capitalize()}"
        
        return await self.create_and_publish(
            event_type=event_type,
            aggregate_type="organization",
            aggregate_id=organization_id,
            event_data=event_data,
            triggered_by_user_id=triggered_by_user_id,
            context_id=organization_id,  # Organization events use org ID as context
            correlation_id=correlation_id,
            causation_id=causation_id,
            event_name=event_name
        )
    
    async def create_user_event(
        self,
        event_action: str,
        user_id: UUID,
        event_data: Dict[str, Any],
        context_id: Optional[UUID] = None,
        triggered_by_user_id: Optional[UserId] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None
    ) -> DomainEvent:
        """Convenience method to create user-related events.
        
        Args:
            event_action: Action that occurred (e.g., 'created', 'updated', 'login')
            user_id: User ID
            event_data: Event payload data
            context_id: Optional context ID (organization, tenant, etc.)
            triggered_by_user_id: Optional user who triggered the event
            correlation_id: Optional correlation ID
            causation_id: Optional causation ID
            
        Returns:
            Created and published domain event
        """
        event_type = f"user.{event_action}"
        event_name = f"User {event_action.capitalize()}"
        
        return await self.create_and_publish(
            event_type=event_type,
            aggregate_type="user",
            aggregate_id=user_id,
            event_data=event_data,
            triggered_by_user_id=triggered_by_user_id,
            context_id=context_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            event_name=event_name
        )