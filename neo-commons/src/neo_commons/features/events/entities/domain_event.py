"""Domain event entity for neo-commons events feature.

This module defines the DomainEvent entity that represents events
that occur within the domain and should be published to webhook subscribers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from uuid import UUID

from ....core.value_objects import EventId, EventType, UserId


@dataclass
class DomainEvent:
    """Domain event entity representing business events that occur in the system.
    
    This entity captures events that should be published to webhook subscribers.
    Matches the webhook_events table structure in both admin and tenant schemas.
    """
    
    # Event identification
    id: EventId
    event_type: EventType
    
    # Event source  
    aggregate_id: UUID  # ID of the entity that triggered the event
    aggregate_type: str  # Type of entity (organization, user, customer, order, etc.)
    
    # Optional event metadata
    event_name: Optional[str] = None
    aggregate_version: int = 1  # Entity version for event ordering
    
    # Event data
    event_data: Dict[str, Any] = field(default_factory=dict)  # Main event payload
    event_metadata: Dict[str, Any] = field(default_factory=dict)  # Context (user_id, ip, source, etc.)
    
    # Event context
    correlation_id: Optional[UUID] = None  # For tracking related events
    causation_id: Optional[UUID] = None  # The event that caused this event
    
    # Generic context
    triggered_by_user_id: Optional[UserId] = None  # User who triggered this event
    context_id: Optional[UUID] = None  # Generic context (organization_id, team_id, etc.)
    
    # Event lifecycle
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None  # When webhook processing started
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Post-init validation and normalization."""
        from ..utils.validation import DomainEventValidationRules, WebhookValidationRules
        
        # Validate event_type format using centralized validation
        try:
            WebhookValidationRules.validate_event_type(self.event_type.value)
        except ValueError as e:
            raise ValueError(f"Invalid event type: {e}")
        
        # Validate aggregate_type using centralized validation
        try:
            DomainEventValidationRules.validate_aggregate_type(self.aggregate_type)
        except ValueError as e:
            raise ValueError(f"Invalid aggregate type: {e}")
        
        # Validate aggregate_version using centralized validation
        try:
            DomainEventValidationRules.validate_aggregate_version(self.aggregate_version)
        except ValueError as e:
            raise ValueError(f"Invalid aggregate version: {e}")
        
        # Validate event_data using centralized validation
        if self.event_data:
            try:
                DomainEventValidationRules.validate_event_data(self.event_data)
            except ValueError as e:
                raise ValueError(f"Invalid event data: {e}")
        
        # Ensure occurred_at and created_at are timezone-aware
        if self.occurred_at.tzinfo is None:
            self.occurred_at = self.occurred_at.replace(tzinfo=timezone.utc)
        
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
            
        # Ensure aggregate_type is lowercase for consistency
        if self.aggregate_type:
            self.aggregate_type = self.aggregate_type.lower()
    
    def mark_as_processed(self) -> None:
        """Mark the event as processed for webhook delivery."""
        if self.processed_at is None:
            self.processed_at = datetime.now(timezone.utc)
    
    def is_processed(self) -> bool:
        """Check if the event has been processed for webhook delivery."""
        return self.processed_at is not None
    
    def get_event_category(self) -> str:
        """Get the event category (part before the dot in event_type)."""
        return self.event_type.category
    
    def get_event_action(self) -> str:
        """Get the event action (part after the dot in event_type)."""
        return self.event_type.action
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the event."""
        self.event_metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key."""
        return self.event_metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "id": str(self.id.value),
            "event_type": self.event_type.value,
            "event_name": self.event_name,
            "aggregate_id": str(self.aggregate_id),
            "aggregate_type": self.aggregate_type,
            "aggregate_version": self.aggregate_version,
            "event_data": self.event_data,
            "event_metadata": self.event_metadata,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "triggered_by_user_id": str(self.triggered_by_user_id.value) if self.triggered_by_user_id else None,
            "context_id": str(self.context_id) if self.context_id else None,
            "occurred_at": self.occurred_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """Create DomainEvent from dictionary representation."""
        from uuid import UUID
        from datetime import datetime
        
        # Convert string IDs back to value objects
        event_id = EventId(UUID(data["id"]))
        event_type = EventType(data["event_type"])
        triggered_by_user_id = UserId(UUID(data["triggered_by_user_id"])) if data.get("triggered_by_user_id") else None
        
        # Parse datetime fields
        occurred_at = datetime.fromisoformat(data["occurred_at"])
        processed_at = datetime.fromisoformat(data["processed_at"]) if data.get("processed_at") else None
        created_at = datetime.fromisoformat(data["created_at"])
        
        return cls(
            id=event_id,
            event_type=event_type,
            event_name=data.get("event_name"),
            aggregate_id=UUID(data["aggregate_id"]),
            aggregate_type=data["aggregate_type"],
            aggregate_version=data.get("aggregate_version", 1),
            event_data=data.get("event_data", {}),
            event_metadata=data.get("event_metadata", {}),
            correlation_id=UUID(data["correlation_id"]) if data.get("correlation_id") else None,
            causation_id=UUID(data["causation_id"]) if data.get("causation_id") else None,
            triggered_by_user_id=triggered_by_user_id,
            context_id=UUID(data["context_id"]) if data.get("context_id") else None,
            occurred_at=occurred_at,
            processed_at=processed_at,
            created_at=created_at,
        )