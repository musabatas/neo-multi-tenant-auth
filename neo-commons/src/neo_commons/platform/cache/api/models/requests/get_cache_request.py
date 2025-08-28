"""Get cache request model.

ONLY get cache requests - validates and structures cache get operation data.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator


class GetCacheRequest(BaseModel):
    """Request model for getting cache entries."""
    
    key: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Cache key identifier"
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
    
    include_metadata: bool = Field(
        default=False,
        description="Whether to include cache entry metadata in response"
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
                "request_id": "req_456",
                "include_metadata": True
            }
        }
    
    def to_domain_data(self) -> dict:
        """Convert to domain layer data structure."""
        return {
            "key": self.key,
            "namespace": self.namespace,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_id": self.request_id
        }


class GetMultipleCacheRequest(BaseModel):
    """Request model for getting multiple cache entries."""
    
    keys: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of cache keys to retrieve"
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
    
    include_metadata: bool = Field(
        default=False,
        description="Whether to include cache entry metadata in response"
    )
    
    @validator('keys')
    def validate_keys(cls, v):
        """Validate cache keys format."""
        if not v:
            raise ValueError("Keys list cannot be empty")
        
        forbidden_chars = [':', '*', '?', '[', ']', '{', '}', '|', '\\', '/', '<', '>', '"']
        
        validated_keys = []
        for key in v:
            if not key or key.isspace():
                raise ValueError("Cache key cannot be empty or whitespace only")
            
            if any(char in key for char in forbidden_chars):
                raise ValueError(f"Cache key '{key}' contains forbidden characters: {forbidden_chars}")
            
            validated_keys.append(key.strip())
        
        # Check for duplicates
        if len(validated_keys) != len(set(validated_keys)):
            raise ValueError("Duplicate keys are not allowed")
        
        return validated_keys
    
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
                "keys": ["user_profile_123", "user_settings_123", "user_preferences_123"],
                "namespace": "user_data",
                "tenant_id": "tenant_abc",
                "user_id": "user_123",
                "request_id": "req_456",
                "include_metadata": False
            }
        }
    
    def to_domain_data(self) -> dict:
        """Convert to domain layer data structure."""
        return {
            "keys": self.keys,
            "namespace": self.namespace,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_id": self.request_id
        }
    
    def get_key_count(self) -> int:
        """Get number of keys to retrieve."""
        return len(self.keys)