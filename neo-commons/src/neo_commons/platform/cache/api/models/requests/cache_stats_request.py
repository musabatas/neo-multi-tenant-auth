"""Cache stats request model.

ONLY cache statistics requests - validates cache metrics queries.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class CacheStatsRequest(BaseModel):
    """Request model for cache statistics."""
    
    namespace: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Optional namespace filter (all namespaces if not specified)"
    )
    
    tenant_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Optional tenant isolation"
    )
    
    include_detailed: bool = Field(
        default=False,
        description="Include detailed per-namespace statistics"
    )
    
    include_performance: bool = Field(
        default=True,
        description="Include performance metrics (hit rates, response times)"
    )
    
    include_memory: bool = Field(
        default=True,
        description="Include memory usage statistics"
    )
    
    time_range_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=1440,  # Max 24 hours
        description="Time range for statistics in minutes (recent period)"
    )
    
    @validator('namespace')
    def validate_namespace(cls, v):
        """Validate namespace format."""
        if v is not None:
            if not v or v.isspace():
                raise ValueError("Namespace cannot be empty or whitespace only")
            
            if not v[0].isalpha():
                raise ValueError("Namespace must start with a letter")
            
            return v.strip().lower()
        return v
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "namespace": "user_data",
                "tenant_id": "tenant_abc", 
                "include_detailed": True,
                "include_performance": True,
                "include_memory": True,
                "time_range_minutes": 60
            }
        }