"""
Event response model.

ONLY handles event data API response formatting.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ActionResponse(BaseModel):
    """Nested response model for event actions."""
    
    id: str = Field(..., description="Action ID")
    name: str = Field(..., description="Action name")
    handler_type: str = Field(..., description="Handler type")
    status: str = Field(..., description="Action execution status")
    created_at: datetime = Field(..., description="Action creation timestamp")


class EventResponse(BaseModel):
    """Response model for event data."""
    
    id: str = Field(
        ...,
        description="Event ID",
        example="evt_123456789"
    )
    
    event_type: str = Field(
        ...,
        description="Type of event",
        example="user.created"
    )
    
    payload: Dict[str, Any] = Field(
        ...,
        description="Event payload data",
        example={"user_id": "123", "email": "user@example.com"}
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    user_id: Optional[str] = Field(
        None,
        description="User who triggered the event",
        example="usr_456"
    )
    
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracing",
        example="trace_789"
    )
    
    status: str = Field(
        ...,
        description="Event processing status",
        example="completed"
    )
    
    execution_mode: str = Field(
        ...,
        description="Event execution mode",
        example="async"
    )
    
    created_at: datetime = Field(
        ...,
        description="Event creation timestamp"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )
    
    scheduled_at: Optional[datetime] = Field(
        None,
        description="Scheduled execution time"
    )
    
    processed_at: Optional[datetime] = Field(
        None,
        description="Processing completion time"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )
    
    actions: List[ActionResponse] = Field(
        default_factory=list,
        description="Associated actions"
    )
    
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts"
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message if failed"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "evt_123456789",
                "event_type": "user.created",
                "payload": {
                    "user_id": "usr_123456789",
                    "email": "john.doe@example.com",
                    "name": "John Doe"
                },
                "tenant_id": "tenant_123",
                "user_id": "usr_987654321",
                "correlation_id": "trace_abc123",
                "status": "completed",
                "execution_mode": "async",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:05Z",
                "scheduled_at": None,
                "processed_at": "2024-01-15T10:30:05Z",
                "metadata": {
                    "source": "admin_api",
                    "version": "v1"
                },
                "actions": [
                    {
                        "id": "act_123456789",
                        "name": "send_welcome_email",
                        "handler_type": "email",
                        "status": "completed",
                        "created_at": "2024-01-15T10:30:01Z"
                    }
                ],
                "retry_count": 0,
                "error_message": None
            }
        }