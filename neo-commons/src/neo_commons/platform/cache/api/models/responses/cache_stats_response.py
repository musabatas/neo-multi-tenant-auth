"""Cache statistics response models.

ONLY cache statistics - structures cache metrics and performance data.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class CacheNamespaceStats(BaseModel):
    """Statistics for a specific cache namespace."""
    
    namespace: str = Field(
        ...,
        description="Namespace name"
    )
    
    total_keys: int = Field(
        default=0,
        ge=0,
        description="Total number of keys in namespace"
    )
    
    memory_usage_bytes: int = Field(
        default=0,
        ge=0,
        description="Memory usage in bytes"
    )
    
    hit_count: int = Field(
        default=0,
        ge=0,
        description="Total cache hits"
    )
    
    miss_count: int = Field(
        default=0,
        ge=0,
        description="Total cache misses"
    )
    
    hit_rate_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Cache hit rate percentage"
    )
    
    average_response_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Average response time in milliseconds"
    )
    
    expired_keys: int = Field(
        default=0,
        ge=0,
        description="Number of expired keys"
    )
    
    evicted_keys: int = Field(
        default=0,
        ge=0,
        description="Number of evicted keys"
    )


class CachePerformanceStats(BaseModel):
    """Cache performance statistics."""
    
    total_operations: int = Field(
        default=0,
        ge=0,
        description="Total cache operations"
    )
    
    operations_per_second: float = Field(
        default=0.0,
        ge=0.0,
        description="Operations per second"
    )
    
    average_response_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Average response time in milliseconds"
    )
    
    p95_response_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="95th percentile response time in milliseconds"
    )
    
    p99_response_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="99th percentile response time in milliseconds"
    )
    
    error_rate_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Error rate percentage"
    )


class CacheMemoryStats(BaseModel):
    """Cache memory usage statistics."""
    
    total_memory_bytes: int = Field(
        default=0,
        ge=0,
        description="Total memory used by cache"
    )
    
    max_memory_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum memory limit"
    )
    
    memory_usage_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Memory usage percentage"
    )
    
    average_entry_size_bytes: float = Field(
        default=0.0,
        ge=0.0,
        description="Average cache entry size in bytes"
    )
    
    largest_entry_size_bytes: int = Field(
        default=0,
        ge=0,
        description="Size of largest cache entry in bytes"
    )
    
    fragmentation_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Memory fragmentation percentage"
    )


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    
    success: bool = Field(
        ...,
        description="Whether the statistics request was successful"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Statistics timestamp"
    )
    
    time_range_minutes: Optional[int] = Field(
        default=None,
        description="Time range covered by statistics"
    )
    
    # Overall statistics
    total_keys: int = Field(
        default=0,
        ge=0,
        description="Total keys across all namespaces"
    )
    
    total_namespaces: int = Field(
        default=0,
        ge=0,
        description="Total number of namespaces"
    )
    
    overall_hit_rate_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall cache hit rate"
    )
    
    # Detailed statistics (optional)
    namespace_stats: Optional[List[CacheNamespaceStats]] = Field(
        default=None,
        description="Per-namespace statistics"
    )
    
    performance_stats: Optional[CachePerformanceStats] = Field(
        default=None,
        description="Performance statistics"
    )
    
    memory_stats: Optional[CacheMemoryStats] = Field(
        default=None,
        description="Memory usage statistics"
    )
    
    # Metadata
    repository_type: str = Field(
        default="unknown",
        description="Cache repository type (redis, memory, etc.)"
    )
    
    uptime_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Cache service uptime in seconds"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Additional information or warnings"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "timestamp": "2023-12-01T12:00:00Z",
                "time_range_minutes": 60,
                "total_keys": 15000,
                "total_namespaces": 8,
                "overall_hit_rate_percentage": 89.5,
                "namespace_stats": [
                    {
                        "namespace": "user_data",
                        "total_keys": 5000,
                        "memory_usage_bytes": 10485760,
                        "hit_count": 8950,
                        "miss_count": 1050,
                        "hit_rate_percentage": 89.5,
                        "average_response_time_ms": 0.8,
                        "expired_keys": 150,
                        "evicted_keys": 25
                    }
                ],
                "performance_stats": {
                    "total_operations": 125000,
                    "operations_per_second": 2083.3,
                    "average_response_time_ms": 0.9,
                    "p95_response_time_ms": 2.1,
                    "p99_response_time_ms": 4.8,
                    "error_rate_percentage": 0.1
                },
                "memory_stats": {
                    "total_memory_bytes": 104857600,
                    "max_memory_bytes": 536870912,
                    "memory_usage_percentage": 19.5,
                    "average_entry_size_bytes": 6990.5,
                    "largest_entry_size_bytes": 1048576,
                    "fragmentation_percentage": 12.3
                },
                "repository_type": "redis",
                "uptime_seconds": 86400,
                "message": "Statistics collected successfully"
            }
        }