"""
Create action request model.

ONLY handles action creation API request validation and transformation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator

# Value object imports removed since to_domain() now uses strings directly
# These can be re-added later if needed for domain conversion


class ConditionRequest(BaseModel):
    """Condition for action execution."""
    
    field: str = Field(..., description="Field to check in event payload")
    operator: str = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")
    
    @validator('operator')
    def validate_operator(cls, v):
        """Validate operator."""
        valid_operators = ["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains"]
        if v not in valid_operators:
            raise ValueError(f"Operator must be one of: {valid_operators}")
        return v


class ActionConfigRequest(BaseModel):
    """Configuration for action execution."""
    
    webhook_url: Optional[str] = Field(None, description="Webhook URL for webhook actions")
    email_template: Optional[str] = Field(None, description="Email template for email actions")
    slack_channel: Optional[str] = Field(None, description="Slack channel for Slack actions")
    sms_template: Optional[str] = Field(None, description="SMS template for SMS actions")
    retry_count: Optional[int] = Field(3, description="Number of retries on failure")
    timeout_seconds: Optional[int] = Field(30, description="Timeout for action execution")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional headers")


class CreateActionRequest(BaseModel):
    """Request model for creating actions."""
    
    name: str = Field(
        ...,
        description="Name of the action",
        example="send_welcome_email"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the action",
        example="Send welcome email to new users"
    )
    
    event_types: List[str] = Field(
        ...,
        description="Event types that trigger this action",
        example=["user.created", "user.activated"]
    )
    
    handler_type: str = Field(
        ...,
        description="Type of handler for this action",
        example="webhook"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    priority: str = Field(
        default="normal",
        description="Action execution priority",
        example="high"
    )
    
    conditions: Optional[List[ConditionRequest]] = Field(
        default_factory=list,
        description="Conditions for action execution"
    )
    
    configuration: ActionConfigRequest = Field(
        ...,
        description="Action-specific configuration"
    )
    
    enabled: bool = Field(
        default=True,
        description="Whether the action is enabled"
    )
    
    @validator('event_types')
    def validate_event_types(cls, v):
        """Validate event types format."""
        for event_type in v:
            if not event_type or '.' not in event_type:
                raise ValueError("Event types must be in format 'domain.action'")
        return v
    
    @validator('handler_type')
    def validate_handler_type(cls, v):
        """Validate handler type."""
        valid_types = ["webhook", "email", "slack", "sms"]
        if v not in valid_types:
            raise ValueError(f"Handler type must be one of: {valid_types}")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority."""
        valid_priorities = ["critical", "high", "normal", "low", "bulk"]
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Validate action name."""
        if not v.strip():
            raise ValueError("Action name cannot be empty")
        return v.strip()
    
    def to_domain(self) -> Dict[str, Any]:
        """Convert to domain representation."""
        return {
            "name": self.name,
            "description": self.description,
            "event_types": self.event_types,  # Keep as strings for now
            "handler_type": self.handler_type,  # Keep as string for now
            "tenant_id": self.tenant_id,  # Keep as string for now
            "priority": self.priority,  # Keep as string for now
            "conditions": [
                {
                    "field": condition.field,
                    "operator": condition.operator,
                    "value": condition.value
                }
                for condition in (self.conditions or [])
            ],
            "configuration": self.configuration.dict(),
            "enabled": self.enabled,
        }
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "name": "send_welcome_email",
                "description": "Send welcome email to newly created users",
                "event_types": ["user.created"],
                "handler_type": "email",
                "tenant_id": "tenant_123",
                "priority": "high",
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
                "enabled": True
            }
        }