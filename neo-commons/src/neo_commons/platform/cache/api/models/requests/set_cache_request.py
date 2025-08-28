"""Set cache request model.

ONLY set cache requests - validates and structures cache set operation data.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class SetCacheRequest(BaseModel):
    """Request model for setting cache entries."""
    
    key: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Cache key identifier"
    )
    
    value: Any = Field(
        ...,
        description="Value to cache (will be serialized)"
    )
    
    namespace: str = Field(
        default="default",
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Cache namespace"
    )
    
    ttl_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        le=86400*365,  # Max 1 year
        description="Time-to-live in seconds (None for no expiration)"
    )
    
    priority: str = Field(
        default="medium",
        pattern=r"^(low|medium|high|critical)$",
        description="Cache priority level"
    )
    
    tenant_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Optional tenant isolation"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Optional user context"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Optional request tracking ID"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the cache entry"
    )
    
    @validator('key')
    def validate_key(cls, v):
        """Validate cache key format."""
        if not v or v.isspace():
            raise ValueError("Cache key cannot be empty or whitespace only")
        
        # Check for forbidden characters
        forbidden_chars = [':', '*', '?', '[', ']', '{', '}', '|', '\\', '/', '<', '>', '"']
        if any(char in v for char in forbidden_chars):
            raise ValueError(f"Cache key contains forbidden characters: {forbidden_chars}")
        
        return v.strip()
    
    @validator('namespace')
    def validate_namespace(cls, v):
        """Validate namespace format."""
        if not v or v.isspace():
            raise ValueError("Namespace cannot be empty or whitespace only")
        
        # Must start with letter, contain only alphanumeric, underscore, hyphen
        if not v[0].isalpha():
            raise ValueError("Namespace must start with a letter")
        
        return v.strip().lower()
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority level."""
        valid_priorities = {'low', 'medium', 'high', 'critical'}
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata size and content."""
        if v is not None:
            # Limit metadata size to prevent abuse
            import json
            try:
                serialized = json.dumps(v)
                if len(serialized) > 10240:  # 10KB limit
                    raise ValueError("Metadata size exceeds 10KB limit")
            except (TypeError, ValueError) as e:
                raise ValueError(f"Metadata must be JSON-serializable: {e}")
        
        return v
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "key": "user_profile_123",
                "value": {"name": "John Doe", "email": "john@example.com"},
                "namespace": "user_data",
                "ttl_seconds": 3600,
                "priority": "high",
                "tenant_id": "tenant_abc",
                "user_id": "user_123",
                "request_id": "req_456",
                "metadata": {"source": "api", "version": "1.0"}
            }
        }
    
    def to_domain_data(self) -> Dict[str, Any]:
        """Convert to domain layer data structure."""
        return {
            "key": self.key,
            "value": self.value,
            "namespace": self.namespace,
            "ttl_seconds": self.ttl_seconds,
            "priority": self.priority,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "metadata": self.metadata
        }
    
    def get_cache_key(self) -> str:
        """Get the formatted cache key."""
        return self.key
    
    def get_namespace_key(self) -> str:
        """Get the formatted namespace."""
        return self.namespace
    
    def has_expiration(self) -> bool:
        """Check if entry has TTL."""
        return self.ttl_seconds is not None and self.ttl_seconds > 0
    
    def is_high_priority(self) -> bool:
        """Check if entry is high priority."""
        return self.priority in {'high', 'critical'}
    
    def get_estimated_size(self) -> int:
        """Estimate serialized size of the value."""
        try:
            import json
            return len(json.dumps(self.value, default=str))
        except:
            return len(str(self.value))