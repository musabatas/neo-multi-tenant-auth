"""Create event request model.

Handles event creation requests with validation following Maximum Separation
Architecture - single file for single operation type.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from .....core.value_objects import EventType
from ....domain.entities.event import EventPriority


class CreateEventRequest(BaseModel):
    """Request model for creating new events."""
    
    # Core event information
    event_type: str = Field(
        ..., 
        description="Event type in dot notation (e.g., 'tenants.created', 'users.updated')",
        regex=r"^[a-z_]+\.[a-z_]+$"
    )
    aggregate_id: UUID = Field(..., description="ID of the entity that triggered the event")
    aggregate_type: str = Field(..., description="Type of entity (tenant, user, organization)")
    
    # Event data and metadata
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event payload/data")
    event_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Event correlation and causation
    correlation_id: Optional[UUID] = Field(None, description="Group related events together")
    causation_id: Optional[UUID] = Field(None, description="The event that caused this event")
    
    # Processing settings
    priority: EventPriority = Field(EventPriority.NORMAL, description="Event processing priority")
    scheduled_at: Optional[datetime] = Field(None, description="When event should be processed")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    
    # Context information (optional)
    tenant_id: Optional[UUID] = Field(None, description="For tenant-scoped events")
    organization_id: Optional[UUID] = Field(None, description="For organization-scoped events")
    user_id: Optional[UUID] = Field(None, description="User who triggered the event")
    source_service: Optional[str] = Field(None, description="Service that created the event")
    source_version: Optional[str] = Field(None, description="Version of the source service")
    
    # Queue settings
    queue_name: Optional[str] = Field(None, description="Redis stream/queue name")
    partition_key: Optional[str] = Field(None, description="For queue partitioning")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "event_type": "tenants.created",
                "aggregate_id": "01234567-89ab-cdef-0123-456789abcdef",
                "aggregate_type": "tenant",
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
                "priority": "high",
                "tenant_id": "01234567-89ab-cdef-0123-456789abcdef",
                "user_id": "01234567-89ab-cdef-0123-456789abcdef",
                "source_service": "tenant-api",
                "source_version": "1.2.3"
            }
        }
    
    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v):
        """Validate event type format."""
        try:
            EventType(v)
        except ValueError as e:
            raise ValueError(f"Invalid event type format: {e}")
        return v
    
    @field_validator('priority', mode='before')
    @classmethod
    def validate_priority(cls, v):
        """Validate and convert priority to enum."""
        if isinstance(v, str):
            try:
                return EventPriority(v)
            except ValueError:
                raise ValueError(f"Invalid priority: {v}")
        return v
    
    @field_validator('scheduled_at')
    @classmethod
    def validate_scheduled_at(cls, v):
        """Validate scheduled_at is not in the past."""
        if v and v < datetime.now(v.tzinfo):
            raise ValueError("scheduled_at cannot be in the past")
        return v