"""Configure handler request model for platform actions infrastructure.

This module handles ONLY configure handler request validation following maximum separation architecture.
Single responsibility: Validate and structure configure handler request data.

Pure API layer - no business logic, ONLY request validation and data transformation.
Uses protocols for dependency injection and clean architecture compliance.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator

from ......core.value_objects import TenantId
from ...core.value_objects import ActionId, HandlerType


class ConfigureHandlerRequest(BaseModel):
    """Request model for configuring action handlers."""
    
    action_id: str = Field(
        ...,
        description="ID of the action to configure",
        example="act_123456789"
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    handler_type: str = Field(
        ...,
        description="Type of handler to configure",
        example="webhook"
    )
    
    configuration: Dict[str, Any] = Field(
        ...,
        description="Handler configuration settings",
        example={
            "webhook_url": "https://api.example.com/webhook",
            "timeout_seconds": 30,
            "retry_count": 3
        }
    )
    
    enabled: Optional[bool] = Field(
        None,
        description="Enable or disable the handler"
    )
    
    @validator('action_id')
    def validate_action_id(cls, v):
        """Validate action ID format."""
        if not v.strip():
            raise ValueError("Action ID cannot be empty")
        return v.strip()
    
    @validator('handler_type')
    def validate_handler_type(cls, v):
        """Validate handler type."""
        valid_types = ["webhook", "email", "slack", "sms", "function", "workflow"]
        if v not in valid_types:
            raise ValueError(f"Handler type must be one of: {valid_types}")
        return v
    
    @validator('configuration')
    def validate_configuration(cls, v, values):
        """Validate configuration based on handler type."""
        if not v:
            raise ValueError("Configuration cannot be empty")
        
        handler_type = values.get('handler_type')
        
        if handler_type == 'webhook':
            if 'webhook_url' not in v:
                raise ValueError("Webhook configuration must include 'webhook_url'")
            if not v['webhook_url']:
                raise ValueError("Webhook URL cannot be empty")
        
        elif handler_type == 'email':
            required_fields = ['to', 'subject', 'body']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Email configuration must include '{field}'")
        
        elif handler_type == 'slack':
            if 'webhook_url' not in v:
                raise ValueError("Slack configuration must include 'webhook_url'")
        
        elif handler_type == 'sms':
            required_fields = ['to_number', 'body']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"SMS configuration must include '{field}'")
        
        elif handler_type == 'function':
            required_fields = ['module', 'function']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Function configuration must include '{field}'")
        
        elif handler_type == 'workflow':
            if 'steps' not in v:
                raise ValueError("Workflow configuration must include 'steps'")
        
        return v
    
    def to_domain(self) -> Dict[str, Any]:
        """Convert to domain representation."""
        return {
            "action_id": ActionId(self.action_id),
            "tenant_id": TenantId(self.tenant_id),
            "handler_type": HandlerType(self.handler_type),
            "configuration": self.configuration,
            "enabled": self.enabled,
        }
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "action_id": "act_123456789",
                "tenant_id": "tenant_123",
                "handler_type": "webhook",
                "configuration": {
                    "webhook_url": "https://api.example.com/webhooks/user-events",
                    "secret": "wh_secret_123",
                    "timeout_seconds": 30,
                    "retry_count": 3,
                    "retry_backoff": "exponential",
                    "headers": {
                        "Authorization": "Bearer token_123",
                        "Content-Type": "application/json"
                    }
                },
                "enabled": True
            }
        }