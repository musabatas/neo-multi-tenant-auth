"""Create action request model."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import timedelta

from ....domain.value_objects.action_type import ActionType


class CreateActionRequest(BaseModel):
    """Request model for creating a new action."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Action name")
    action_type: ActionType = Field(..., description="Type of action to create")
    handler_class: str = Field(..., min_length=1, max_length=500, description="Handler class path")
    config: Dict[str, Any] = Field(default_factory=dict, description="Action configuration")
    event_patterns: List[str] = Field(default_factory=list, description="Event patterns to match")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Additional conditions")
    is_active: bool = Field(True, description="Whether action is active")
    priority: int = Field(default=100, ge=0, le=1000, description="Action priority")
    timeout_seconds: int = Field(default=300, ge=1, le=3600, description="Timeout in seconds")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Retry configuration")
    max_concurrent_executions: int = Field(default=1, ge=1, le=100, description="Max concurrent executions")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000, description="Rate limit per minute")
    description: Optional[str] = Field(None, max_length=500, description="Action description")
    tags: List[str] = Field(default_factory=list, description="Action tags")
    owner_team: Optional[str] = Field(None, max_length=100, description="Owner team")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('event_patterns')
    def validate_event_patterns(cls, v):
        """Validate event patterns are not empty."""
        if not v:
            raise ValueError("At least one event pattern is required")
        return v
    
    @validator('handler_class')
    def validate_handler_class(cls, v):
        """Validate handler class format."""
        if '.' not in v:
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
        json_encoders = {
            timedelta: lambda v: int(v.total_seconds())
        }