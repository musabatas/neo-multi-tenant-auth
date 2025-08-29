"""Event response model.

Single event response model following Maximum Separation Architecture.
Contains complete event information for API responses.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from ...domain.entities.event import EventStatus, EventPriority


class EventResponse(BaseModel):
    """Response model for single event operations."""
    
    # Core identity
    id: UUID = Field(..., description="Event unique identifier")
    event_type: str = Field(..., description="Event type in dot notation")
    aggregate_id: UUID = Field(..., description="ID of the entity that triggered the event")
    aggregate_type: str = Field(..., description="Type of entity")
    
    # Event versioning and correlation
    event_version: int = Field(..., description="Event schema version")
    correlation_id: Optional[UUID] = Field(None, description="Group related events together")
    causation_id: Optional[UUID] = Field(None, description="The event that caused this event")
    
    # Content and context
    event_data: Dict[str, Any] = Field(..., description="Event payload/data")
    event_metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    
    # Processing information
    status: EventStatus = Field(..., description="Current event status")
    priority: EventPriority = Field(..., description="Event priority level")
    scheduled_at: datetime = Field(..., description="When event should be processed")
    
    # Performance and monitoring
    processing_started_at: Optional[datetime] = Field(None, description="When processing started")
    processing_completed_at: Optional[datetime] = Field(None, description="When processing completed")
    processing_duration_ms: Optional[int] = Field(None, description="Processing duration in milliseconds")
    
    # Retry handling
    retry_count: int = Field(..., description="Current retry count")
    max_retries: int = Field(..., description="Maximum retry attempts")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed error information")
    
    # Context information
    tenant_id: Optional[UUID] = Field(None, description="For tenant-scoped events")
    organization_id: Optional[UUID] = Field(None, description="For organization-scoped events")
    user_id: Optional[UUID] = Field(None, description="User who triggered the event")
    source_service: Optional[str] = Field(None, description="Service that created the event")
    source_version: Optional[str] = Field(None, description="Version of the source service")
    
    # Queue integration
    queue_name: Optional[str] = Field(None, description="Redis stream/queue name")
    message_id: Optional[str] = Field(None, description="Queue message identifier")
    partition_key: Optional[str] = Field(None, description="For queue partitioning")
    
    # Audit fields
    created_at: datetime = Field(..., description="When event was created")
    updated_at: datetime = Field(..., description="When event was last updated")
    deleted_at: Optional[datetime] = Field(None, description="When event was soft deleted")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            EventStatus: lambda v: v.value,
            EventPriority: lambda v: v.value
        }
        schema_extra = {
            "example": {
                "id": "01234567-89ab-cdef-0123-456789abcdef",
                "event_type": "tenants.created",
                "aggregate_id": "01234567-89ab-cdef-0123-456789abcdef",
                "aggregate_type": "tenant",
                "event_version": 1,
                "correlation_id": "01234567-89ab-cdef-0123-456789abcdef",
                "event_data": {
                    "tenant_name": "Acme Corp",
                    "tenant_slug": "acme-corp",
                    "subscription_plan": "enterprise"
                },
                "event_metadata": {
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0...",
                    "api_version": "v1"
                },
                "status": "completed",
                "priority": "high",
                "scheduled_at": "2023-12-01T10:00:00Z",
                "processing_started_at": "2023-12-01T10:00:01Z",
                "processing_completed_at": "2023-12-01T10:00:05Z",
                "processing_duration_ms": 4500,
                "retry_count": 0,
                "max_retries": 3,
                "tenant_id": "01234567-89ab-cdef-0123-456789abcdef",
                "user_id": "01234567-89ab-cdef-0123-456789abcdef",
                "source_service": "tenant-api",
                "source_version": "1.2.3",
                "queue_name": "events:tenants",
                "created_at": "2023-12-01T10:00:00Z",
                "updated_at": "2023-12-01T10:00:05Z"
            }
        }
    
    @classmethod
    def from_event(cls, event) -> "EventResponse":
        """Create response model from Event entity.
        
        Args:
            event: Event entity from domain layer
            
        Returns:
            EventResponse instance
        """
        return cls(
            id=event.id.value,
            event_type=event.event_type.value,
            aggregate_id=event.aggregate_reference.aggregate_id,
            aggregate_type=event.aggregate_reference.aggregate_type,
            event_version=event.event_version,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            event_data=event.event_data,
            event_metadata=event.event_metadata,
            status=event.status,
            priority=event.priority,
            scheduled_at=event.scheduled_at,
            processing_started_at=event.processing_started_at,
            processing_completed_at=event.processing_completed_at,
            processing_duration_ms=event.processing_duration_ms,
            retry_count=event.retry_count,
            max_retries=event.max_retries,
            error_message=event.error_message,
            error_details=event.error_details,
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            user_id=event.user_id,
            source_service=event.source_service,
            source_version=event.source_version,
            queue_name=event.queue_name,
            message_id=event.message_id,
            partition_key=event.partition_key,
            created_at=event.created_at,
            updated_at=event.updated_at,
            deleted_at=event.deleted_at
        )