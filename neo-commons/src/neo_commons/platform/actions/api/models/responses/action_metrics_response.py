"""Action metrics response model."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class ActionMetricsResponse(BaseModel):
    """Response model for action performance metrics."""
    
    action_id: UUID = Field(..., description="Action ID")
    action_name: str = Field(..., description="Action name")
    
    # Execution statistics
    total_executions: int = Field(..., description="Total execution count")
    successful_executions: int = Field(..., description="Successful execution count")
    failed_executions: int = Field(..., description="Failed execution count")
    success_rate: float = Field(..., description="Success rate percentage")
    
    # Performance metrics
    avg_execution_time_ms: Optional[float] = Field(None, description="Average execution time in ms")
    min_execution_time_ms: Optional[int] = Field(None, description="Minimum execution time in ms")
    max_execution_time_ms: Optional[int] = Field(None, description="Maximum execution time in ms")
    p95_execution_time_ms: Optional[float] = Field(None, description="95th percentile execution time in ms")
    p99_execution_time_ms: Optional[float] = Field(None, description="99th percentile execution time in ms")
    
    # Resource usage
    avg_memory_usage_mb: Optional[float] = Field(None, description="Average memory usage in MB")
    max_memory_usage_mb: Optional[float] = Field(None, description="Maximum memory usage in MB")
    avg_cpu_usage_percent: Optional[float] = Field(None, description="Average CPU usage percentage")
    max_cpu_usage_percent: Optional[float] = Field(None, description="Maximum CPU usage percentage")
    
    # Retry statistics
    total_retries: int = Field(..., description="Total retry count")
    retry_success_rate: float = Field(..., description="Retry success rate percentage")
    
    # Time-based metrics
    executions_per_hour: float = Field(..., description="Average executions per hour")
    executions_per_day: float = Field(..., description="Average executions per day")
    
    # Recent activity
    last_execution_at: Optional[datetime] = Field(None, description="Last execution time")
    last_successful_execution_at: Optional[datetime] = Field(None, description="Last successful execution")
    last_failed_execution_at: Optional[datetime] = Field(None, description="Last failed execution")
    
    # Error analysis
    common_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Most common error types")
    
    # Health status
    is_healthy: bool = Field(..., description="Current health status")
    health_score: float = Field(..., description="Health score (0-100)")
    
    # Time range for metrics
    metrics_start_date: datetime = Field(..., description="Start date for metrics calculation")
    metrics_end_date: datetime = Field(..., description="End date for metrics calculation")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }