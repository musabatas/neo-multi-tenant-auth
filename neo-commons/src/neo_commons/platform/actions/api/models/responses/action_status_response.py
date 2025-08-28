"""
Action status response model.

ONLY handles action status data API response formatting.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ActionExecutionResponse(BaseModel):
    """Individual action execution details."""
    
    id: str = Field(..., description="Execution ID")
    event_id: str = Field(..., description="Associated event ID")
    status: str = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    duration_ms: Optional[float] = Field(None, description="Execution duration in ms")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ActionStatusResponse(BaseModel):
    """Response model for action status data."""
    
    action_id: str = Field(
        ...,
        description="Action ID",
        example="act_123456789"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    name: str = Field(
        ...,
        description="Action name",
        example="send_welcome_email"
    )
    
    current_status: str = Field(
        ...,
        description="Current action status",
        example="enabled"
    )
    
    enabled: bool = Field(
        ...,
        description="Whether action is enabled"
    )
    
    health_status: str = Field(
        ...,
        description="Health status based on recent executions",
        example="healthy"
    )
    
    recent_executions: List[ActionExecutionResponse] = Field(
        default_factory=list,
        description="Recent execution details"
    )
    
    execution_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution statistics"
    )
    
    last_executed_at: Optional[datetime] = Field(
        None,
        description="Last execution timestamp"
    )
    
    next_scheduled_at: Optional[datetime] = Field(
        None,
        description="Next scheduled execution"
    )
    
    created_at: datetime = Field(
        ...,
        description="Action creation timestamp"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "action_id": "act_123456789",
                "tenant_id": "tenant_123",
                "name": "send_welcome_email",
                "current_status": "enabled",
                "enabled": True,
                "health_status": "healthy",
                "recent_executions": [
                    {
                        "id": "exec_123456789",
                        "event_id": "evt_123456789",
                        "status": "completed",
                        "started_at": "2024-01-15T10:30:00Z",
                        "completed_at": "2024-01-15T10:30:02Z",
                        "duration_ms": 125.5,
                        "error_message": None
                    }
                ],
                "execution_stats": {
                    "total_executions": 100,
                    "successful_executions": 95,
                    "failed_executions": 5,
                    "success_rate": 95.0,
                    "average_duration_ms": 125.5
                },
                "last_executed_at": "2024-01-15T10:30:00Z",
                "next_scheduled_at": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }