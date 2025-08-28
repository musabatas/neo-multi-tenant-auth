"""Cache response models.

ONLY cache responses - structures cache operation responses.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class CacheEntryMetadata(BaseModel):
    """Cache entry metadata."""
    
    created_at: datetime = Field(
        ...,
        description="When the cache entry was created"
    )
    
    accessed_at: Optional[datetime] = Field(
        default=None,
        description="When the cache entry was last accessed"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When the cache entry expires"
    )
    
    access_count: int = Field(
        default=0,
        ge=0,
        description="Number of times the entry has been accessed"
    )
    
    size_bytes: int = Field(
        default=0,
        ge=0,
        description="Size of cached value in bytes"
    )
    
    priority: str = Field(
        default="medium",
        pattern=r"^(low|medium|high|critical)$",
        description="Cache priority level"
    )
    
    ttl_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Original TTL in seconds"
    )
    
    namespace: str = Field(
        ...,
        min_length=1,
        description="Cache namespace"
    )


class CacheEntryResponse(BaseModel):
    """Single cache entry response."""
    
    key: str = Field(
        ...,
        description="Cache key"
    )
    
    value: Optional[Any] = Field(
        default=None,
        description="Cached value (null if not found)"
    )
    
    found: bool = Field(
        ...,
        description="Whether the key was found in cache"
    )
    
    metadata: Optional[CacheEntryMetadata] = Field(
        default=None,
        description="Cache entry metadata (if requested)"
    )
    
    lookup_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Time taken for lookup in milliseconds"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "key": "user_profile_123",
                "value": {"name": "John Doe", "email": "john@example.com"},
                "found": True,
                "metadata": {
                    "created_at": "2023-12-01T12:00:00Z",
                    "accessed_at": "2023-12-01T12:05:00Z",
                    "expires_at": "2023-12-01T13:00:00Z",
                    "access_count": 5,
                    "size_bytes": 1024,
                    "priority": "high",
                    "ttl_seconds": 3600,
                    "namespace": "user_data"
                },
                "lookup_time_ms": 0.5
            }
        }


class CacheResponse(BaseModel):
    """Cache operation response."""
    
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    
    data: Optional[CacheEntryResponse] = Field(
        default=None,
        description="Cache entry data (for get operations)"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Operation message or error description"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request tracking ID"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "key": "user_profile_123",
                    "value": {"name": "John Doe"},
                    "found": True,
                    "lookup_time_ms": 0.5
                },
                "message": "Cache entry retrieved successfully",
                "request_id": "req_456",
                "timestamp": "2023-12-01T12:00:00Z"
            }
        }


class MultipleCacheResponse(BaseModel):
    """Multiple cache entries response."""
    
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    
    entries: List[CacheEntryResponse] = Field(
        default_factory=list,
        description="List of cache entry responses"
    )
    
    found_count: int = Field(
        default=0,
        ge=0,
        description="Number of entries found"
    )
    
    total_requested: int = Field(
        default=0,
        ge=0,
        description="Total number of keys requested"
    )
    
    hit_rate_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Cache hit rate for this request"
    )
    
    total_lookup_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total time taken for all lookups"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Operation message or error description"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request tracking ID"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "entries": [
                    {
                        "key": "user_profile_123",
                        "value": {"name": "John Doe"},
                        "found": True,
                        "lookup_time_ms": 0.5
                    },
                    {
                        "key": "user_settings_123",
                        "value": None,
                        "found": False,
                        "lookup_time_ms": 0.3
                    }
                ],
                "found_count": 1,
                "total_requested": 2,
                "hit_rate_percentage": 50.0,
                "total_lookup_time_ms": 0.8,
                "message": "Retrieved 1 out of 2 requested cache entries",
                "request_id": "req_456",
                "timestamp": "2023-12-01T12:00:00Z"
            }
        }
    
    @property
    def miss_count(self) -> int:
        """Get number of cache misses."""
        return self.total_requested - self.found_count
    
    @property
    def miss_rate_percentage(self) -> float:
        """Get cache miss rate percentage."""
        return 100.0 - self.hit_rate_percentage
    
    def get_found_keys(self) -> List[str]:
        """Get list of keys that were found."""
        return [entry.key for entry in self.entries if entry.found]
    
    def get_missing_keys(self) -> List[str]:
        """Get list of keys that were not found."""
        return [entry.key for entry in self.entries if not entry.found]