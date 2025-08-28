"""
Dispatch event request model.

ONLY handles event dispatch API request validation and transformation.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

from neo_commons.platform.events.core.value_objects.event_type import EventType
from neo_commons.platform.events.core.value_objects.event_id import EventId
from neo_commons.platform.actions.core.value_objects import ExecutionMode
from neo_commons.core.value_objects import UserId, TenantId


class DispatchEventRequest(BaseModel):
    """Request model for dispatching events."""
    
    event_type: str = Field(
        ...,
        description="Type of event being dispatched",
        example="user.created"
    )
    
    payload: Dict[str, Any] = Field(
        ...,
        description="Event payload data",
        example={"user_id": "123", "email": "user@example.com"}
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier for event context",
        example="tenant_123"
    )
    
    user_id: Optional[str] = Field(
        None,
        description="User who triggered the event",
        example="user_456"
    )
    
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracing",
        example="trace_789"
    )
    
    execution_mode: str = Field(
        default="async",
        description="Execution mode for event processing",
        example="async"
    )
    
    scheduled_at: Optional[datetime] = Field(
        None,
        description="When to execute the event (if scheduled)"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata for the event"
    )
    
    @validator('event_type')
    def validate_event_type(cls, v):
        """Validate event type format."""
        if not v or '.' not in v:
            raise ValueError("Event type must be in format 'domain.action'")
        return v
    
    @validator('execution_mode')
    def validate_execution_mode(cls, v):
        """Validate execution mode."""
        valid_modes = ["sync", "async", "scheduled"]
        if v not in valid_modes:
            raise ValueError(f"Execution mode must be one of: {valid_modes}")
        return v
    
    @validator('payload')
    def validate_payload(cls, v):
        """Validate payload is not empty."""
        if not v:
            raise ValueError("Event payload cannot be empty")
        return v
    
    def to_domain(self) -> Dict[str, Any]:
        """Convert to domain representation."""
        return {
            "event_type": EventType(self.event_type),
            "payload": self.payload,
            "tenant_id": TenantId(self.tenant_id),
            "user_id": UserId(self.user_id) if self.user_id else None,
            "correlation_id": self.correlation_id,
            "execution_mode": ExecutionMode(self.execution_mode),
            "scheduled_at": self.scheduled_at,
            "metadata": self.metadata or {},
        }
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "event_type": "user.created",
                "payload": {
                    "user_id": "usr_123456789",
                    "email": "john.doe@example.com",
                    "name": "John Doe"
                },
                "tenant_id": "tenant_123",
                "user_id": "usr_987654321",
                "correlation_id": "trace_abc123",
                "execution_mode": "async",
                "metadata": {
                    "source": "admin_api",
                    "version": "v1"
                }
            }
        }