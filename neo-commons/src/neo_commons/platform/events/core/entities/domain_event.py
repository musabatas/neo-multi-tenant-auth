"""Domain event entity for platform events infrastructure.

This module defines the DomainEvent entity that represents events
that occur within the domain and should be published to webhook subscribers.

Migrated from features/events to platform/events following enterprise
clean architecture patterns for maximum separation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import UUID

from .....core.value_objects import UserId
from ..value_objects import EventId, EventType
from .....utils import generate_uuid_v7, utc_now, ensure_utc


@dataclass
class DomainEvent:
    """Domain event entity representing business events that occur in the system.
    
    This entity captures events that should be published to webhook subscribers.
    Matches the webhook_events table structure in both admin and tenant schemas.
    
    Pure platform infrastructure - used by all business features.
    """
    
    # Event identification (required fields first)
    event_type: EventType
    aggregate_id: UUID  # ID of the entity that triggered the event (should be UUIDv7)
    aggregate_type: str  # Type of entity (organization, user, customer, order, etc.)
    
    # Event identification (optional/default fields)
    id: EventId = field(default_factory=lambda: EventId(generate_uuid_v7()))
    event_name: Optional[str] = None
    
    # Event source (optional/default fields)
    aggregate_version: int = 1  # Entity version for event ordering
    
    # Event data
    event_data: Dict[str, Any] = field(default_factory=dict)  # Main event payload
    event_metadata: Dict[str, Any] = field(default_factory=dict)  # Context (user_id, ip, source, etc.)
    
    # Event context
    correlation_id: Optional[UUID] = None  # For tracking related events (should be UUIDv7)
    causation_id: Optional[UUID] = None  # The event that caused this event (should be UUIDv7)
    
    # Generic context
    triggered_by_user_id: Optional[UserId] = None  # User who triggered this event
    context_id: Optional[UUID] = None  # Generic context (organization_id, team_id, etc. - should be UUIDv7)
    
    # Event lifecycle
    occurred_at: datetime = field(default_factory=utc_now)
    processed_at: Optional[datetime] = None  # When webhook processing started
    
    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self):
        """Post-init validation and normalization."""
        # Basic event type validation
        if not self.event_type or not self.event_type.value:
            raise ValueError("Event type cannot be empty")
            
        # Basic event type format validation (should contain a dot)
        if '.' not in self.event_type.value:
            raise ValueError(f"Invalid event type format: {self.event_type.value}. Expected format: 'category.action'")
        
        # Basic aggregate type validation
        if not self.aggregate_type or not self.aggregate_type.strip():
            raise ValueError("Aggregate type cannot be empty")
            
        # Basic aggregate version validation
        if self.aggregate_version < 1:
            raise ValueError("Aggregate version must be >= 1")
        
        # Ensure occurred_at and created_at are timezone-aware
        self.occurred_at = ensure_utc(self.occurred_at)
        self.created_at = ensure_utc(self.created_at)
            
        # Ensure aggregate_type is lowercase for consistency
        if self.aggregate_type:
            self.aggregate_type = self.aggregate_type.lower()
    
    def mark_as_processed(self) -> None:
        """Mark the event as processed for webhook delivery."""
        if self.processed_at is None:
            self.processed_at = utc_now()
    
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
    
    @classmethod
    def create_new(cls, 
                   event_type: EventType,
                   aggregate_id: UUID,
                   aggregate_type: str,
                   event_data: Optional[Dict[str, Any]] = None,
                   **kwargs) -> 'DomainEvent':
        """Create a new domain event with UUIDv7 compliance.
        
        This factory method ensures all new events use UUIDv7 for better
        database performance and time-ordering.
        
        Args:
            event_type: Type of the event
            aggregate_id: ID of the entity that triggered the event (should be UUIDv7)
            aggregate_type: Type of entity (organization, user, etc.)
            event_data: Main event payload
            **kwargs: Additional fields (correlation_id, causation_id, etc.)
        """
        # Ensure aggregate_id is UUIDv7 (features should pass UUIDv7)
        if not aggregate_id:
            raise ValueError("aggregate_id is required and should be UUIDv7")
            
        return cls(
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_data=event_data or {},
            **kwargs
        )
    
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
        
        # Convert string IDs back to value objects (UUIDs should be UUIDv7 from database)
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