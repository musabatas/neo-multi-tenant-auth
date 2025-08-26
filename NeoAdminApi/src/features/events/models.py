"""Pydantic models for event action management API."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from neo_commons.features.events.entities.event_action import (
    ActionStatus, HandlerType, ActionPriority, ExecutionMode, ActionCondition
)


class ActionConditionModel(BaseModel):
    """Action condition model for API requests/responses."""
    
    field: str = Field(..., description="Event field to check (supports dot notation)")
    operator: str = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_entity(cls, condition: ActionCondition) -> "ActionConditionModel":
        """Create model from entity."""
        return cls(
            field=condition.field,
            operator=condition.operator,
            value=condition.value
        )
    
    def to_entity(self) -> ActionCondition:
        """Convert to entity."""
        return ActionCondition(
            field=self.field,
            operator=self.operator,
            value=self.value
        )


class EventActionCreateRequest(BaseModel):
    """Request model for creating event actions."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Action name")
    description: Optional[str] = Field(None, max_length=1000, description="Action description")
    
    handler_type: HandlerType = Field(HandlerType.WEBHOOK, description="Handler type")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Handler configuration")
    
    event_types: List[str] = Field(..., min_length=1, description="Event types to trigger on")
    conditions: List[ActionConditionModel] = Field(default_factory=list, description="Additional conditions")
    context_filters: Dict[str, Any] = Field(default_factory=dict, description="Context-based filters")
    
    execution_mode: ExecutionMode = Field(ExecutionMode.ASYNC, description="Execution mode")
    priority: ActionPriority = Field(ActionPriority.NORMAL, description="Execution priority")
    timeout_seconds: int = Field(30, ge=1, le=3600, description="Execution timeout")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(5, ge=1, le=300, description="Retry delay")
    
    is_enabled: bool = Field(True, description="Whether action is enabled")
    tags: Dict[str, str] = Field(default_factory=dict, description="Action tags")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant filtering")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "name": "User Registration Webhook",
                "description": "Send webhook when user registers",
                "handler_type": "webhook",
                "configuration": {
                    "url": "https://example.com/webhook",
                    "method": "POST",
                    "headers": {"Authorization": "Bearer token"}
                },
                "event_types": ["user.created"],
                "conditions": [
                    {
                        "field": "data.user.email",
                        "operator": "contains",
                        "value": "@company.com"
                    }
                ],
                "execution_mode": "async",
                "priority": "normal",
                "is_enabled": True
            }
        }
    )


class EventActionUpdateRequest(BaseModel):
    """Request model for updating event actions."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Action name")
    description: Optional[str] = Field(None, max_length=1000, description="Action description")
    
    configuration: Optional[Dict[str, Any]] = Field(None, description="Handler configuration")
    
    event_types: Optional[List[str]] = Field(None, min_length=1, description="Event types to trigger on")
    conditions: Optional[List[ActionConditionModel]] = Field(None, description="Additional conditions")
    context_filters: Optional[Dict[str, Any]] = Field(None, description="Context-based filters")
    
    execution_mode: Optional[ExecutionMode] = Field(None, description="Execution mode")
    priority: Optional[ActionPriority] = Field(None, description="Execution priority")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600, description="Execution timeout")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: Optional[int] = Field(None, ge=1, le=300, description="Retry delay")
    
    status: Optional[ActionStatus] = Field(None, description="Action status")
    is_enabled: Optional[bool] = Field(None, description="Whether action is enabled")
    tags: Optional[Dict[str, str]] = Field(None, description="Action tags")
    
    model_config = ConfigDict(use_enum_values=True)


class EventActionResponse(BaseModel):
    """Response model for event actions."""
    
    id: str = Field(..., description="Action ID")
    name: str = Field(..., description="Action name")
    description: Optional[str] = Field(None, description="Action description")
    
    handler_type: str = Field(..., description="Handler type")
    configuration: Dict[str, Any] = Field(..., description="Handler configuration")
    
    event_types: List[str] = Field(..., description="Event types to trigger on")
    conditions: List[ActionConditionModel] = Field(..., description="Additional conditions")
    context_filters: Dict[str, Any] = Field(..., description="Context-based filters")
    
    execution_mode: str = Field(..., description="Execution mode")
    priority: str = Field(..., description="Execution priority")
    timeout_seconds: int = Field(..., description="Execution timeout")
    max_retries: int = Field(..., description="Maximum retry attempts")
    retry_delay_seconds: int = Field(..., description="Retry delay")
    
    status: str = Field(..., description="Action status")
    is_enabled: bool = Field(..., description="Whether action is enabled")
    
    tags: Dict[str, str] = Field(..., description="Action tags")
    created_by_user_id: Optional[str] = Field(None, description="Creator user ID")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_triggered_at: Optional[datetime] = Field(None, description="Last trigger timestamp")
    
    trigger_count: int = Field(..., description="Total trigger count")
    success_count: int = Field(..., description="Success count")
    failure_count: int = Field(..., description="Failure count")
    success_rate: float = Field(..., description="Success rate percentage")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "01234567-89ab-cdef-0123-456789abcdef",
                "name": "User Registration Webhook",
                "description": "Send webhook when user registers",
                "handler_type": "webhook",
                "configuration": {
                    "url": "https://example.com/webhook",
                    "method": "POST"
                },
                "event_types": ["user.created"],
                "conditions": [],
                "context_filters": {},
                "execution_mode": "async",
                "priority": "normal",
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 5,
                "status": "active",
                "is_enabled": True,
                "tags": {},
                "created_by_user_id": "01234567-89ab-cdef-0123-456789abcdef",
                "tenant_id": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_triggered_at": None,
                "trigger_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0
            }
        }
    )
    
    @classmethod
    def from_entity(cls, action) -> "EventActionResponse":
        """Create response from EventAction entity."""
        return cls(
            id=str(action.id.value),
            name=action.name,
            description=action.description,
            handler_type=action.handler_type.value,
            configuration=action.configuration,
            event_types=action.event_types,
            conditions=[ActionConditionModel.from_entity(c) for c in action.conditions],
            context_filters=action.context_filters,
            execution_mode=action.execution_mode.value,
            priority=action.priority.value,
            timeout_seconds=action.timeout_seconds,
            max_retries=action.max_retries,
            retry_delay_seconds=action.retry_delay_seconds,
            status=action.status.value,
            is_enabled=action.is_enabled,
            tags=action.tags,
            created_by_user_id=str(action.created_by_user_id.value) if action.created_by_user_id else None,
            tenant_id=action.tenant_id,
            created_at=action.created_at,
            updated_at=action.updated_at,
            last_triggered_at=action.last_triggered_at,
            trigger_count=action.trigger_count,
            success_count=action.success_count,
            failure_count=action.failure_count,
            success_rate=action.success_rate
        )


class EventActionListResponse(BaseModel):
    """Response model for listing event actions."""
    
    actions: List[EventActionResponse] = Field(..., description="List of actions")
    total: int = Field(..., description="Total count of actions")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    
    model_config = ConfigDict(from_attributes=True)


class ActionExecutionResponse(BaseModel):
    """Response model for action executions."""
    
    id: str = Field(..., description="Execution ID")
    action_id: str = Field(..., description="Action ID")
    event_id: Optional[str] = Field(None, description="Event ID")
    
    event_type: str = Field(..., description="Event type")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    
    status: str = Field(..., description="Execution status")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    error_message: Optional[str] = Field(None, description="Error message")
    retry_count: int = Field(..., description="Retry count")
    
    execution_context: Dict[str, Any] = Field(..., description="Execution context")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ActionExecutionListResponse(BaseModel):
    """Response model for listing action executions."""
    
    executions: List[ActionExecutionResponse] = Field(..., description="List of executions")
    total: int = Field(..., description="Total count of executions")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    
    model_config = ConfigDict(from_attributes=True)


class ActionTestRequest(BaseModel):
    """Request model for testing actions."""
    
    event_type: str = Field(..., description="Event type to simulate")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event data to simulate")
    dry_run: bool = Field(True, description="Whether to perform dry run (no actual execution)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "user.created",
                "event_data": {
                    "user": {
                        "id": "123",
                        "email": "test@company.com",
                        "name": "Test User"
                    }
                },
                "dry_run": True
            }
        }
    )


class ActionTestResponse(BaseModel):
    """Response model for action testing."""
    
    matched: bool = Field(..., description="Whether action would be triggered")
    reason: str = Field(..., description="Reason for match/no-match")
    conditions_evaluated: List[Dict[str, Any]] = Field(..., description="Condition evaluation results")
    would_execute: bool = Field(..., description="Whether execution would occur")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    
    model_config = ConfigDict(from_attributes=True)


class ActionStatsResponse(BaseModel):
    """Response model for action statistics."""
    
    total_actions: int = Field(..., description="Total number of actions")
    active_actions: int = Field(..., description="Number of active actions")
    enabled_actions: int = Field(..., description="Number of enabled actions")
    
    total_executions: int = Field(..., description="Total executions")
    successful_executions: int = Field(..., description="Successful executions")
    failed_executions: int = Field(..., description="Failed executions")
    
    overall_success_rate: float = Field(..., description="Overall success rate percentage")
    
    by_handler_type: Dict[str, int] = Field(..., description="Actions by handler type")
    by_status: Dict[str, int] = Field(..., description="Actions by status")
    
    model_config = ConfigDict(from_attributes=True)