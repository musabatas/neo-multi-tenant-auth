"""Cache health response models.

ONLY health check responses - structures cache system health status.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status for a cache component."""
    
    component: str = Field(
        ...,
        description="Component name"
    )
    
    status: HealthStatus = Field(
        ...,
        description="Component health status"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Health status message"
    )
    
    response_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Component response time in milliseconds"
    )
    
    last_checked: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last health check timestamp"
    )
    
    details: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional health details"
    )


class CacheHealthResponse(BaseModel):
    """Cache system health response."""
    
    success: bool = Field(
        ...,
        description="Whether the health check was successful"
    )
    
    status: HealthStatus = Field(
        ...,
        description="Overall cache system health status"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    
    uptime_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Cache service uptime in seconds"
    )
    
    # Component health checks
    repository_health: ComponentHealth = Field(
        ...,
        description="Cache repository health"
    )
    
    serializer_health: Optional[ComponentHealth] = Field(
        default=None,
        description="Cache serializer health"
    )
    
    distribution_health: Optional[ComponentHealth] = Field(
        default=None,
        description="Distribution service health"
    )
    
    invalidation_health: Optional[ComponentHealth] = Field(
        default=None,
        description="Invalidation service health"
    )
    
    event_publisher_health: Optional[ComponentHealth] = Field(
        default=None,
        description="Event publisher health"
    )
    
    # Overall metrics
    total_response_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total health check response time"
    )
    
    healthy_components: int = Field(
        default=0,
        ge=0,
        description="Number of healthy components"
    )
    
    total_components: int = Field(
        default=0,
        ge=0,
        description="Total number of components checked"
    )
    
    health_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall health percentage"
    )
    
    # Additional information
    warnings: Optional[List[str]] = Field(
        default=None,
        description="Health warnings"
    )
    
    errors: Optional[List[str]] = Field(
        default=None,
        description="Health errors"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Overall health message"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "success": True,
                "status": "healthy",
                "timestamp": "2023-12-01T12:00:00Z",
                "uptime_seconds": 86400,
                "repository_health": {
                    "component": "redis_repository",
                    "status": "healthy",
                    "message": "Redis connection active",
                    "response_time_ms": 0.5,
                    "last_checked": "2023-12-01T12:00:00Z",
                    "details": {
                        "redis_version": "7.0.5",
                        "memory_usage": "45MB",
                        "connected_clients": "12"
                    }
                },
                "serializer_health": {
                    "component": "json_serializer",
                    "status": "healthy",
                    "message": "Serializer functioning normally",
                    "response_time_ms": 0.1,
                    "last_checked": "2023-12-01T12:00:00Z"
                },
                "distribution_health": {
                    "component": "redis_distributor",
                    "status": "healthy",
                    "message": "Distribution service active",
                    "response_time_ms": 1.2,
                    "last_checked": "2023-12-01T12:00:00Z"
                },
                "invalidation_health": {
                    "component": "pattern_invalidator",
                    "status": "healthy",
                    "message": "Invalidation service operational",
                    "response_time_ms": 0.3,
                    "last_checked": "2023-12-01T12:00:00Z"
                },
                "event_publisher_health": {
                    "component": "cache_event_publisher",
                    "status": "healthy",
                    "message": "Event publishing active",
                    "response_time_ms": 0.8,
                    "last_checked": "2023-12-01T12:00:00Z",
                    "details": {
                        "events_published": "1250",
                        "success_rate": "99.8%"
                    }
                },
                "total_response_time_ms": 2.9,
                "healthy_components": 5,
                "total_components": 5,
                "health_percentage": 100.0,
                "warnings": None,
                "errors": None,
                "message": "All cache components are healthy"
            }
        }
    
    def is_healthy(self) -> bool:
        """Check if cache system is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    def is_degraded(self) -> bool:
        """Check if cache system is degraded."""
        return self.status == HealthStatus.DEGRADED
    
    def is_unhealthy(self) -> bool:
        """Check if cache system is unhealthy."""
        return self.status == HealthStatus.UNHEALTHY
    
    def get_unhealthy_components(self) -> List[str]:
        """Get list of unhealthy component names."""
        unhealthy = []
        
        if self.repository_health.status == HealthStatus.UNHEALTHY:
            unhealthy.append(self.repository_health.component)
        
        for component_health in [
            self.serializer_health,
            self.distribution_health,
            self.invalidation_health,
            self.event_publisher_health
        ]:
            if component_health and component_health.status == HealthStatus.UNHEALTHY:
                unhealthy.append(component_health.component)
        
        return unhealthy
    
    def get_degraded_components(self) -> List[str]:
        """Get list of degraded component names."""
        degraded = []
        
        if self.repository_health.status == HealthStatus.DEGRADED:
            degraded.append(self.repository_health.component)
        
        for component_health in [
            self.serializer_health,
            self.distribution_health,
            self.invalidation_health,
            self.event_publisher_health
        ]:
            if component_health and component_health.status == HealthStatus.DEGRADED:
                degraded.append(component_health.component)
        
        return degraded