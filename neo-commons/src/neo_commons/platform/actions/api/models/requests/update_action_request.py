"""Update action request model."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator

from ....domain.value_objects.action_type import ActionType


class UpdateActionRequest(BaseModel):
    """Request model for updating an existing action."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Action name")
    action_type: Optional[ActionType] = Field(None, description="Type of action")
    handler_class: Optional[str] = Field(None, min_length=1, max_length=500, description="Handler class path")
    config: Optional[Dict[str, Any]] = Field(None, description="Action configuration")
    event_patterns: Optional[List[str]] = Field(None, description="Event patterns to match")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Additional conditions")
    is_active: Optional[bool] = Field(None, description="Whether action is active")
    priority: Optional[int] = Field(None, ge=0, le=1000, description="Action priority")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600, description="Timeout in seconds")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Retry configuration")
    max_concurrent_executions: Optional[int] = Field(None, ge=1, le=100, description="Max concurrent executions")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000, description="Rate limit per minute")
    description: Optional[str] = Field(None, max_length=500, description="Action description")
    tags: Optional[List[str]] = Field(None, description="Action tags")
    owner_team: Optional[str] = Field(None, max_length=100, description="Owner team")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('handler_class')
    def validate_handler_class(cls, v):
        """Validate handler class format."""
        if v is not None and '.' not in v:
            raise ValueError("Handler class must include module path")
        return v
    
    @validator('retry_policy')
    def validate_retry_policy(cls, v):
        """Validate retry policy structure."""
        if v is not None:
            required_fields = ['max_retries', 'backoff_type', 'initial_delay_ms']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Retry policy missing required field: {field}")
            
            if v['backoff_type'] not in ['exponential', 'linear', 'fixed']:
                raise ValueError("Retry backoff_type must be 'exponential', 'linear', or 'fixed'")
                
            if not isinstance(v['max_retries'], int) or v['max_retries'] < 0:
                raise ValueError("max_retries must be a non-negative integer")
                
            if not isinstance(v['initial_delay_ms'], int) or v['initial_delay_ms'] < 100:
                raise ValueError("initial_delay_ms must be at least 100ms")
        return v
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True