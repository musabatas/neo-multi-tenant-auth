"""
Event history response model.

ONLY handles event history data API response formatting.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class EventHistoryEntryResponse(BaseModel):
    """Individual event history entry."""
    
    id: str = Field(..., description="History entry ID")
    event_id: str = Field(..., description="Event ID")
    action_type: str = Field(..., description="Type of action performed")
    description: str = Field(..., description="Description of what happened")
    old_values: Optional[Dict[str, Any]] = Field(None, description="Previous values")
    new_values: Optional[Dict[str, Any]] = Field(None, description="New values")
    user_id: Optional[str] = Field(None, description="User who made the change")
    created_at: datetime = Field(..., description="When the change occurred")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EventHistoryResponse(BaseModel):
    """Response model for event history data."""
    
    event_id: str = Field(
        ...,
        description="Event ID",
        example="evt_123456789"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    event_type: str = Field(
        ...,
        description="Event type",
        example="user.created"
    )
    
    history_entries: List[EventHistoryEntryResponse] = Field(
        ...,
        description="Chronological list of history entries"
    )
    
    total_entries: int = Field(
        ...,
        description="Total number of history entries"
    )
    
    first_activity_at: datetime = Field(
        ...,
        description="Timestamp of first activity"
    )
    
    last_activity_at: datetime = Field(
        ...,
        description="Timestamp of last activity"
    )
    
    activity_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Summary of activity types and counts"
    )
    
    retrieved_at: datetime = Field(
        ...,
        description="When this history was retrieved"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "event_id": "evt_123456789",
                "tenant_id": "tenant_123",
                "event_type": "user.created",
                "history_entries": [
                    {
                        "id": "hist_123456789",
                        "event_id": "evt_123456789",
                        "action_type": "event_created",
                        "description": "Event was created",
                        "old_values": None,
                        "new_values": {
                            "status": "pending",
                            "execution_mode": "async"
                        },
                        "user_id": "usr_987654321",
                        "created_at": "2024-01-15T10:30:00Z",
                        "metadata": {
                            "source": "admin_api",
                            "ip_address": "192.168.1.100"
                        }
                    },
                    {
                        "id": "hist_123456790",
                        "event_id": "evt_123456789",
                        "action_type": "status_updated",
                        "description": "Event status changed from pending to processing",
                        "old_values": {"status": "pending"},
                        "new_values": {"status": "processing"},
                        "user_id": None,
                        "created_at": "2024-01-15T10:30:01Z",
                        "metadata": {
                            "automated": True,
                            "processor_id": "worker_01"
                        }
                    }
                ],
                "total_entries": 5,
                "first_activity_at": "2024-01-15T10:30:00Z",
                "last_activity_at": "2024-01-15T10:30:05Z",
                "activity_summary": {
                    "event_created": 1,
                    "status_updated": 3,
                    "action_executed": 1
                },
                "retrieved_at": "2024-01-15T15:00:00Z"
            }
        }