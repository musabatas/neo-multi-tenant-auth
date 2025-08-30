"""Action execution response model."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from ....domain.entities.action_execution import ActionStatus


class ExecutionResponse(BaseModel):
    """Response model for action execution data."""
    
    id: UUID = Field(..., description="Execution ID")
    action_id: UUID = Field(..., description="Action ID")
    event_id: Optional[UUID] = Field(None, description="Triggering event ID")
    status: ActionStatus = Field(..., description="Execution status")
    input_data: Dict[str, Any] = Field(..., description="Input data")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    stack_trace: Optional[str] = Field(None, description="Stack trace if failed")
    attempt_number: int = Field(..., description="Attempt number (1-based)")
    parent_execution_id: Optional[UUID] = Field(None, description="Parent execution if retry")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @classmethod
    def from_domain(cls, execution) -> "ExecutionResponse":
        """Create response from domain execution."""
        return cls(
            id=execution.id.value,
            action_id=execution.action_id.value,
            event_id=execution.event_id.value if execution.event_id else None,
            status=execution.status,
            input_data=execution.input_data,
            output_data=execution.output_data,
            error_message=execution.error_message,
            error_details=execution.error_details,
            stack_trace=execution.stack_trace,
            attempt_number=execution.attempt_number,
            parent_execution_id=execution.parent_execution_id.value if execution.parent_execution_id else None,
            execution_time_ms=execution.execution_time_ms,
            memory_usage_mb=execution.memory_usage_mb,
            cpu_usage_percent=execution.cpu_usage_percent,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            created_at=execution.created_at
        )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }