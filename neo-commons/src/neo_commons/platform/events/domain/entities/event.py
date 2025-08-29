"""Core Event entity for event sourcing."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID
from enum import Enum

from ..value_objects.event_id import EventId
from ..value_objects.event_type import EventType
from ..value_objects.correlation_id import CorrelationId
from ..value_objects.aggregate_reference import AggregateReference
from .event_metadata import EventMetadata
from ....utils import generate_uuid_v7


class EventStatus(Enum):
    """Event processing status matching platform_common.event_status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    BLOCKED = "blocked"


class EventPriority(Enum):
    """Event priority matching platform_common.event_priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


@dataclass
class Event:
    """
    Core Event entity for event sourcing.
    
    Represents an immutable event that has occurred in the system.
    Maps to the admin.events and tenant_template.events database tables.
    """
    
    # Core Identity (immutable after creation)
    id: EventId
    event_type: EventType
    aggregate_reference: AggregateReference
    
    # Event Metadata (immutable after creation)
    event_version: int = 1
    correlation_id: Optional[CorrelationId] = None
    causation_id: Optional[EventId] = None
    
    # Content and Context (immutable after creation)
    event_data: Dict[str, Any] = field(default_factory=dict)
    event_metadata: EventMetadata = field(default_factory=EventMetadata.create_empty)
    
    # Processing Information (mutable for state tracking)
    status: EventStatus = EventStatus.PENDING
    priority: EventPriority = EventPriority.NORMAL
    scheduled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Performance and Monitoring (mutable for tracking)
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Error Handling (mutable for error tracking)
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # Context Information (immutable after creation)
    tenant_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    source_service: Optional[str] = None
    source_version: Optional[str] = None
    
    # Queue Integration (mutable for queue tracking)
    queue_name: Optional[str] = None
    message_id: Optional[str] = None
    partition_key: Optional[str] = None
    
    # Audit Fields (immutable after creation)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        event_type: str,
        aggregate_id: UUID,
        aggregate_type: str,
        event_data: Dict[str, Any],
        event_metadata: Optional[EventMetadata] = None,
        correlation_id: Optional[CorrelationId] = None,
        causation_id: Optional[EventId] = None,
        priority: EventPriority = EventPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        tenant_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        source_service: Optional[str] = None,
        source_version: Optional[str] = None
    ) -> 'Event':
        """
        Create a new Event with proper validation.
        
        Args:
            event_type: Event type in format 'category.action' 
            aggregate_id: ID of entity that triggered the event
            aggregate_type: Type of entity (tenant, user, organization, etc.)
            event_data: Event payload data
            event_metadata: Optional event metadata
            correlation_id: Optional correlation ID to group related events
            causation_id: Optional ID of event that caused this event
            priority: Event processing priority
            scheduled_at: When event should be processed
            tenant_id: Optional tenant ID for tenant-scoped events
            organization_id: Optional organization ID for organization-scoped events
            user_id: Optional user ID who triggered the event
            source_service: Optional source service that created the event
            source_version: Optional version of the source service
            
        Returns:
            New Event instance
        """
        return cls(
            id=EventId(generate_uuid_v7()),
            event_type=EventType(event_type),
            aggregate_reference=AggregateReference.create(aggregate_id, aggregate_type),
            event_data=event_data.copy() if event_data else {},
            event_metadata=event_metadata or EventMetadata.create_empty(),
            correlation_id=correlation_id,
            causation_id=causation_id,
            priority=priority,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
            tenant_id=tenant_id,
            organization_id=organization_id,
            user_id=user_id,
            source_service=source_service,
            source_version=source_version
        )
    
    def start_processing(self) -> None:
        """Mark event as started processing."""
        if self.status != EventStatus.PENDING:
            raise ValueError(f"Cannot start processing event in status: {self.status}")
        
        self.status = EventStatus.PROCESSING
        self.processing_started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_processing(self) -> None:
        """Mark event as completed successfully."""
        if self.status != EventStatus.PROCESSING:
            raise ValueError(f"Cannot complete event not in processing status: {self.status}")
        
        now = datetime.now(timezone.utc)
        self.status = EventStatus.COMPLETED
        self.processing_completed_at = now
        self.updated_at = now
        
        # Calculate processing duration
        if self.processing_started_at:
            delta = now - self.processing_started_at
            self.processing_duration_ms = int(delta.total_seconds() * 1000)
    
    def fail_processing(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark event as failed processing."""
        if self.status != EventStatus.PROCESSING:
            raise ValueError(f"Cannot fail event not in processing status: {self.status}")
        
        now = datetime.now(timezone.utc)
        self.status = EventStatus.FAILED
        self.processing_completed_at = now
        self.updated_at = now
        self.error_message = error_message
        self.error_details = error_details.copy() if error_details else {}
        
        # Calculate processing duration even for failures
        if self.processing_started_at:
            delta = now - self.processing_started_at
            self.processing_duration_ms = int(delta.total_seconds() * 1000)
    
    def retry_processing(self) -> None:
        """Prepare event for retry processing."""
        if self.status != EventStatus.FAILED:
            raise ValueError(f"Cannot retry event not in failed status: {self.status}")
        
        if self.retry_count >= self.max_retries:
            raise ValueError(f"Event has exceeded maximum retries: {self.retry_count}/{self.max_retries}")
        
        self.status = EventStatus.PENDING
        self.retry_count += 1
        self.updated_at = datetime.now(timezone.utc)
        
        # Clear previous processing times but keep error info for debugging
        self.processing_started_at = None
        self.processing_completed_at = None
        self.processing_duration_ms = None
    
    def cancel_processing(self) -> None:
        """Cancel event processing."""
        if self.status in [EventStatus.COMPLETED, EventStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel event in status: {self.status}")
        
        self.status = EventStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc)
    
    def can_be_retried(self) -> bool:
        """Check if event can be retried."""
        return self.status == EventStatus.FAILED and self.retry_count < self.max_retries
    
    def is_processing_complete(self) -> bool:
        """Check if event processing is complete (success or failure)."""
        return self.status in [EventStatus.COMPLETED, EventStatus.FAILED, EventStatus.CANCELLED]
    
    def get_processing_duration(self) -> Optional[int]:
        """Get processing duration in milliseconds."""
        return self.processing_duration_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            'id': str(self.id.value),
            'event_type': self.event_type.value,
            'aggregate_id': str(self.aggregate_reference.aggregate_id),
            'aggregate_type': self.aggregate_reference.aggregate_type,
            'event_version': self.event_version,
            'correlation_id': str(self.correlation_id.value) if self.correlation_id else None,
            'causation_id': str(self.causation_id.value) if self.causation_id else None,
            'event_data': self.event_data,
            'event_metadata': self.event_metadata.to_dict(),
            'status': self.status.value,
            'priority': self.priority.value,
            'scheduled_at': self.scheduled_at.isoformat(),
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            'processing_duration_ms': self.processing_duration_ms,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'queue_name': self.queue_name,
            'message_id': self.message_id,
            'partition_key': self.partition_key,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    def __post_init__(self):
        """Validate event after initialization."""
        # Validate retry count
        if self.retry_count < 0 or self.retry_count > self.max_retries:
            raise ValueError(f"Invalid retry count: {self.retry_count} (max: {self.max_retries})")
        
        # Validate processing duration
        if self.processing_duration_ms is not None and self.processing_duration_ms < 0:
            raise ValueError(f"Processing duration cannot be negative: {self.processing_duration_ms}")
        
        # Validate timing consistency
        if self.processing_started_at and self.processing_completed_at:
            if self.processing_completed_at < self.processing_started_at:
                raise ValueError("Processing completed time cannot be before start time")
    
    def __str__(self) -> str:
        return f"Event(id={self.id}, type={self.event_type}, status={self.status.value})"
    
    def __repr__(self) -> str:
        return (f"Event(id={self.id!r}, event_type={self.event_type!r}, "
                f"aggregate_reference={self.aggregate_reference!r}, status={self.status})")