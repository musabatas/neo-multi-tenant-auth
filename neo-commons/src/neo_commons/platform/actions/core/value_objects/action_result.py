"""Action result value object for platform events infrastructure.

This module defines the ActionResult value object that represents immutable execution results
for platform event actions with success/failure status and contextual data.

Pure platform infrastructure - used by all business features.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum


class ActionResultStatus(Enum):
    """Status enumeration for action execution results."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ActionResult:
    """Immutable value object representing the result of an action execution.
    
    Captures comprehensive execution context including status, output data,
    error details, performance metrics, and metadata for audit and debugging.
    """
    
    status: ActionResultStatus
    output_data: Dict[str, Any]
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    execution_duration_ms: Optional[int] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not isinstance(self.status, ActionResultStatus):
            raise ValueError("Status must be an ActionResultStatus enum value")
            
        if not isinstance(self.output_data, dict):
            raise ValueError("Output data must be a dictionary")
            
        if self.execution_duration_ms is not None and self.execution_duration_ms < 0:
            raise ValueError("Execution duration must be non-negative")
            
        if self.retry_count < 0:
            raise ValueError("Retry count must be non-negative")
    
    @classmethod
    def success(
        cls, 
        output_data: Dict[str, Any] = None, 
        execution_duration_ms: int = None,
        metadata: Dict[str, Any] = None
    ) -> 'ActionResult':
        """Create a successful action result.
        
        Args:
            output_data: Data produced by the action execution
            execution_duration_ms: Time taken to execute the action
            metadata: Additional metadata about the execution
            
        Returns:
            ActionResult with success status
        """
        return cls(
            status=ActionResultStatus.SUCCESS,
            output_data=output_data or {},
            execution_duration_ms=execution_duration_ms,
            metadata=metadata
        )
    
    @classmethod
    def failure(
        cls,
        error_message: str,
        error_code: str = None,
        output_data: Dict[str, Any] = None,
        execution_duration_ms: int = None,
        retry_count: int = 0,
        metadata: Dict[str, Any] = None
    ) -> 'ActionResult':
        """Create a failed action result.
        
        Args:
            error_message: Human-readable error description
            error_code: Machine-readable error code
            output_data: Any partial data produced before failure
            execution_duration_ms: Time taken before failure
            retry_count: Number of retries attempted
            metadata: Additional metadata about the failure
            
        Returns:
            ActionResult with failure status
        """
        return cls(
            status=ActionResultStatus.FAILURE,
            output_data=output_data or {},
            error_message=error_message,
            error_code=error_code,
            execution_duration_ms=execution_duration_ms,
            retry_count=retry_count,
            metadata=metadata
        )
    
    @property
    def is_success(self) -> bool:
        """Check if the action execution was successful."""
        return self.status == ActionResultStatus.SUCCESS
    
    @property
    def is_failure(self) -> bool:
        """Check if the action execution failed."""
        return self.status == ActionResultStatus.FAILURE
    
    @property
    def has_error(self) -> bool:
        """Check if the result contains error information."""
        return self.error_message is not None or self.error_code is not None