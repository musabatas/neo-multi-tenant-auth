"""Action response model."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from ....domain.value_objects.action_type import ActionType


class ActionResponse(BaseModel):
    """Response model for action data."""
    
    id: UUID = Field(..., description="Action ID")
    name: str = Field(..., description="Action name")
    action_type: ActionType = Field(..., description="Type of action")
    handler_class: str = Field(..., description="Handler class path")
    config: Dict[str, Any] = Field(..., description="Action configuration")
    event_patterns: List[str] = Field(..., description="Event patterns to match")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Additional conditions")
    is_active: bool = Field(..., description="Whether action is active")
    priority: int = Field(..., description="Action priority")
    timeout_seconds: int = Field(..., description="Timeout in seconds")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Retry configuration")
    max_concurrent_executions: int = Field(..., description="Max concurrent executions")
    rate_limit_per_minute: Optional[int] = Field(None, description="Rate limit per minute")
    is_healthy: bool = Field(..., description="Whether action is healthy")
    last_health_check_at: Optional[datetime] = Field(None, description="Last health check time")
    health_check_error: Optional[str] = Field(None, description="Last health check error")
    total_executions: int = Field(..., description="Total execution count")
    successful_executions: int = Field(..., description="Successful execution count")
    failed_executions: int = Field(..., description="Failed execution count")
    avg_execution_time_ms: Optional[float] = Field(None, description="Average execution time in ms")
    description: Optional[str] = Field(None, description="Action description")
    tags: List[str] = Field(..., description="Action tags")
    owner_team: Optional[str] = Field(None, description="Owner team")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    @classmethod
    def from_domain(cls, action) -> "ActionResponse":
        """Create response from domain action."""
        return cls(
            id=action.id.value,
            name=action.name,
            action_type=action.action_type,
            handler_class=action.handler_class,
            config=action.config,
            event_patterns=action.event_patterns,
            conditions=action.conditions,
            is_active=action.is_active,
            priority=action.priority,
            timeout_seconds=action.timeout_seconds,
            retry_policy=action.retry_policy,
            max_concurrent_executions=action.max_concurrent_executions,
            rate_limit_per_minute=action.rate_limit_per_minute,
            is_healthy=action.is_healthy,
            last_health_check_at=action.last_health_check_at,
            health_check_error=action.health_check_error,
            total_executions=action.total_executions,
            successful_executions=action.successful_executions,
            failed_executions=action.failed_executions,
            avg_execution_time_ms=action.avg_execution_time_ms,
            description=action.description,
            tags=action.tags,
            owner_team=action.owner_team,
            metadata=action.metadata,
            created_at=action.created_at,
            updated_at=action.updated_at
        )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }