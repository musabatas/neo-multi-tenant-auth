"""Flush namespace request model.

ONLY namespace flush requests - validates namespace clearing operations.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class FlushNamespaceRequest(BaseModel):
    """Request model for flushing entire namespaces."""
    
    namespace: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Cache namespace to flush"
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
    
    confirmation: bool = Field(
        default=False,
        description="Confirmation flag to prevent accidental flushes"
    )
    
    @validator('namespace')
    def validate_namespace(cls, v):
        """Validate namespace format."""
        if not v or v.isspace():
            raise ValueError("Namespace cannot be empty or whitespace only")
        
        if not v[0].isalpha():
            raise ValueError("Namespace must start with a letter")
        
        return v.strip().lower()
    
    @validator('confirmation')
    def validate_confirmation(cls, v):
        """Validate confirmation flag."""
        if not v:
            raise ValueError("Confirmation must be true to proceed with flush operation")
        return v
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "namespace": "user_data",
                "tenant_id": "tenant_abc",
                "user_id": "admin_123",
                "request_id": "req_456",
                "confirmation": True
            }
        }