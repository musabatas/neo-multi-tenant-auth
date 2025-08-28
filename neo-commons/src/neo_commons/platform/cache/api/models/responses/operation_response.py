"""Operation response models.

ONLY operation responses - structures generic cache operation results.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class OperationResponse(BaseModel):
    """Generic cache operation response."""
    
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Operation message or error description"
    )
    
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional operation data"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request tracking ID"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    
    operation_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Time taken for operation in milliseconds"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "message": "Cache entry deleted successfully",
                "data": {"deleted": True, "existed": True},
                "request_id": "req_456",
                "timestamp": "2023-12-01T12:00:00Z",
                "operation_time_ms": 1.2
            }
        }


class BulkOperationResponse(BaseModel):
    """Bulk cache operation response."""
    
    success: bool = Field(
        ...,
        description="Whether all operations were successful"
    )
    
    total_operations: int = Field(
        ...,
        ge=0,
        description="Total number of operations requested"
    )
    
    successful_operations: int = Field(
        ...,
        ge=0,
        description="Number of successful operations"
    )
    
    failed_operations: int = Field(
        ...,
        ge=0,
        description="Number of failed operations"
    )
    
    success_rate_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Success rate percentage"
    )
    
    results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed results per operation"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Overall operation message"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request tracking ID"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    
    total_operation_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total time for all operations in milliseconds"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "total_operations": 10,
                "successful_operations": 8,
                "failed_operations": 2,
                "success_rate_percentage": 80.0,
                "results": {
                    "deleted_keys": ["key1", "key2", "key3"],
                    "failed_keys": ["key4", "key5"],
                    "errors": ["Key not found", "Permission denied"]
                },
                "message": "Bulk delete completed with 80% success rate",
                "request_id": "req_456",
                "timestamp": "2023-12-01T12:00:00Z",
                "total_operation_time_ms": 15.6
            }
        }
    
    @property
    def failure_rate_percentage(self) -> float:
        """Get failure rate percentage."""
        return 100.0 - self.success_rate_percentage