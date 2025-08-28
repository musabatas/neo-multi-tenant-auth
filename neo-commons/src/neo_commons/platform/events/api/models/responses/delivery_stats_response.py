"""
Delivery statistics response model.

ONLY handles delivery statistics API response formatting.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DeliveryStatsBreakdownResponse(BaseModel):
    """Breakdown statistics by category."""
    
    total: int = Field(..., description="Total count")
    successful: int = Field(..., description="Successful count")
    failed: int = Field(..., description="Failed count")
    pending: int = Field(..., description="Pending count")
    success_rate: float = Field(..., description="Success rate as percentage")


class DeliveryStatsTimeSeriesResponse(BaseModel):
    """Time series data point."""
    
    timestamp: datetime = Field(..., description="Data point timestamp")
    total_deliveries: int = Field(..., description="Total deliveries in period")
    successful_deliveries: int = Field(..., description="Successful deliveries in period")
    failed_deliveries: int = Field(..., description="Failed deliveries in period")
    average_duration_ms: float = Field(..., description="Average delivery duration in ms")


class DeliveryStatsResponse(BaseModel):
    """Response model for delivery statistics."""
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    period_start: datetime = Field(
        ...,
        description="Statistics period start"
    )
    
    period_end: datetime = Field(
        ...,
        description="Statistics period end"
    )
    
    overall_stats: DeliveryStatsBreakdownResponse = Field(
        ...,
        description="Overall delivery statistics"
    )
    
    stats_by_event_type: Dict[str, DeliveryStatsBreakdownResponse] = Field(
        default_factory=dict,
        description="Statistics broken down by event type"
    )
    
    stats_by_handler_type: Dict[str, DeliveryStatsBreakdownResponse] = Field(
        default_factory=dict,
        description="Statistics broken down by handler type"
    )
    
    time_series: List[DeliveryStatsTimeSeriesResponse] = Field(
        default_factory=list,
        description="Time series delivery data"
    )
    
    top_failing_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top failing event types with counts"
    )
    
    average_delivery_time_ms: float = Field(
        ...,
        description="Average delivery time in milliseconds",
        example=125.5
    )
    
    p50_delivery_time_ms: float = Field(
        ...,
        description="50th percentile delivery time in ms"
    )
    
    p95_delivery_time_ms: float = Field(
        ...,
        description="95th percentile delivery time in ms"
    )
    
    p99_delivery_time_ms: float = Field(
        ...,
        description="99th percentile delivery time in ms"
    )
    
    total_volume: int = Field(
        ...,
        description="Total delivery volume in period"
    )
    
    generated_at: datetime = Field(
        ...,
        description="When statistics were generated"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "tenant_id": "tenant_123",
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2024-01-31T23:59:59Z",
                "overall_stats": {
                    "total": 1500,
                    "successful": 1425,
                    "failed": 75,
                    "pending": 0,
                    "success_rate": 95.0
                },
                "stats_by_event_type": {
                    "user.created": {
                        "total": 800,
                        "successful": 780,
                        "failed": 20,
                        "pending": 0,
                        "success_rate": 97.5
                    },
                    "user.updated": {
                        "total": 700,
                        "successful": 645,
                        "failed": 55,
                        "pending": 0,
                        "success_rate": 92.1
                    }
                },
                "stats_by_handler_type": {
                    "webhook": {
                        "total": 900,
                        "successful": 855,
                        "failed": 45,
                        "pending": 0,
                        "success_rate": 95.0
                    },
                    "email": {
                        "total": 600,
                        "successful": 570,
                        "failed": 30,
                        "pending": 0,
                        "success_rate": 95.0
                    }
                },
                "time_series": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "total_deliveries": 50,
                        "successful_deliveries": 48,
                        "failed_deliveries": 2,
                        "average_duration_ms": 125.5
                    }
                ],
                "top_failing_events": [
                    {
                        "event_type": "user.password_reset",
                        "failure_count": 25,
                        "failure_rate": 15.5
                    }
                ],
                "average_delivery_time_ms": 125.5,
                "p50_delivery_time_ms": 98.2,
                "p95_delivery_time_ms": 250.0,
                "p99_delivery_time_ms": 500.0,
                "total_volume": 1500,
                "generated_at": "2024-02-01T10:00:00Z"
            }
        }