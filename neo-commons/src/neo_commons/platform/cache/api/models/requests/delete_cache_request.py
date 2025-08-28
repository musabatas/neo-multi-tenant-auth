"""Delete cache request model.

ONLY delete cache requests - validates cache deletion operations.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class DeleteCacheRequest(BaseModel):
    """Request model for deleting cache entries."""
    
    key: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Cache key to delete"
    )
    
    namespace: str = Field(
        default="default",
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Cache namespace"
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
    
    @validator('key')
    def validate_key(cls, v):
        """Validate cache key format."""
        if not v or v.isspace():
            raise ValueError("Cache key cannot be empty or whitespace only")
        
        forbidden_chars = [':', '*', '?', '[', ']', '{', '}', '|', '\\', '/', '<', '>', '"']
        if any(char in v for char in forbidden_chars):
            raise ValueError(f"Cache key contains forbidden characters: {forbidden_chars}")
        
        return v.strip()
    
    @validator('namespace')
    def validate_namespace(cls, v):
        """Validate namespace format."""
        if not v or v.isspace():
            raise ValueError("Namespace cannot be empty or whitespace only")
        
        if not v[0].isalpha():
            raise ValueError("Namespace must start with a letter")
        
        return v.strip().lower()
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "key": "user_profile_123",
                "namespace": "user_data",
                "tenant_id": "tenant_abc",
                "user_id": "user_123",
                "request_id": "req_456"
            }
        }