"""Invalidate cache request model.

ONLY invalidation requests - validates pattern-based cache invalidation.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class InvalidateRequest(BaseModel):
    """Request model for invalidating cache entries by pattern."""
    
    pattern: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Invalidation pattern (wildcard, regex, or literal)"
    )
    
    pattern_type: str = Field(
        default="wildcard",
        pattern=r"^(literal|wildcard|regex)$",
        description="Type of pattern matching"
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
    
    reason: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Reason for invalidation"
    )
    
    @validator('pattern')
    def validate_pattern(cls, v):
        """Validate invalidation pattern."""
        if not v or v.isspace():
            raise ValueError("Pattern cannot be empty or whitespace only")
        return v.strip()
    
    @validator('pattern_type')
    def validate_pattern_type(cls, v):
        """Validate pattern type."""
        valid_types = {'literal', 'wildcard', 'regex'}
        if v not in valid_types:
            raise ValueError(f"Pattern type must be one of: {valid_types}")
        return v
    
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
                "pattern": "user_*",
                "pattern_type": "wildcard",
                "namespace": "user_data",
                "tenant_id": "tenant_abc",
                "user_id": "user_123",
                "request_id": "req_456",
                "reason": "User data updated"
            }
        }