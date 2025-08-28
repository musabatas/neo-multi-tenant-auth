"""
Action response model.

ONLY handles action data API response formatting.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ActionConditionResponse(BaseModel):
    """Nested response model for action conditions."""
    
    field: str = Field(..., description="Condition field")
    operator: str = Field(..., description="Condition operator")
    value: Any = Field(..., description="Condition value")


class ActionResponse(BaseModel):
    """Response model for action data."""
    
    id: str = Field(
        ...,
        description="Action ID",
        example="act_123456789"
    )
    
    name: str = Field(
        ...,
        description="Action name",
        example="send_welcome_email"
    )
    
    description: Optional[str] = Field(
        None,
        description="Action description",
        example="Send welcome email to new users"
    )
    
    event_types: List[str] = Field(
        ...,
        description="Event types that trigger this action",
        example=["user.created", "user.activated"]
    )
    
    handler_type: str = Field(
        ...,
        description="Handler type",
        example="email"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    priority: str = Field(
        ...,
        description="Action priority",
        example="high"
    )
    
    status: str = Field(
        ...,
        description="Action status",
        example="enabled"
    )
    
    conditions: List[ActionConditionResponse] = Field(
        default_factory=list,
        description="Action execution conditions"
    )
    
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action configuration"
    )
    
    enabled: bool = Field(
        ...,
        description="Whether action is enabled"
    )
    
    created_at: datetime = Field(
        ...,
        description="Action creation timestamp"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )
    
    last_executed_at: Optional[datetime] = Field(
        None,
        description="Last execution timestamp"
    )
    
    execution_count: int = Field(
        default=0,
        description="Total execution count"
    )
    
    success_count: int = Field(
        default=0,
        description="Successful execution count"
    )
    
    failure_count: int = Field(
        default=0,
        description="Failed execution count"
    )
    
    average_execution_time_ms: Optional[float] = Field(
        None,
        description="Average execution time in milliseconds"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "act_123456789",
                "name": "send_welcome_email",
                "description": "Send welcome email to newly created users",
                "event_types": ["user.created"],
                "handler_type": "email",
                "tenant_id": "tenant_123",
                "priority": "high",
                "status": "enabled",
                "conditions": [
                    {
                        "field": "user.status",
                        "operator": "eq",
                        "value": "active"
                    }
                ],
                "configuration": {
                    "email_template": "welcome_template",
                    "retry_count": 3,
                    "timeout_seconds": 30
                },
                "enabled": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "last_executed_at": "2024-01-15T10:30:00Z",
                "execution_count": 15,
                "success_count": 14,
                "failure_count": 1,
                "average_execution_time_ms": 250.5
            }
        }