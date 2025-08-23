"""
Protocol interfaces for exception handling components.

Protocol-based interfaces for exception handling, error reporting,
and error response formatting across platform services.
"""
from typing import Protocol, Any, Dict, List, Optional, Type
from fastapi import Request, HTTPException
from starlette.responses import Response


class ExceptionProtocol(Protocol):
    """Protocol for base exception operations."""
    
    status_code: int
    error_code: str
    message: str
    details: Optional[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        ...
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        ...


class DomainExceptionProtocol(Protocol):
    """Protocol for domain-specific exception operations."""
    
    domain: str
    operation: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    
    def get_domain_context(self) -> Dict[str, Any]:
        """Get domain-specific context information."""
        ...


class ServiceExceptionProtocol(Protocol):
    """Protocol for service-layer exception operations."""
    
    service_name: str
    operation_name: str
    upstream_error: Optional[Exception]
    
    def get_service_context(self) -> Dict[str, Any]:
        """Get service-specific context information."""
        ...
    
    def is_retryable(self) -> bool:
        """Check if the operation can be retried."""
        ...


class ExceptionHandlerProtocol(Protocol):
    """Protocol for exception handler operations."""
    
    async def handle_exception(
        self,
        request: Request,
        exc: Exception
    ) -> Response:
        """Handle exception and return appropriate response."""
        ...
    
    def should_handle(self, exc_type: Type[Exception]) -> bool:
        """Check if handler should process this exception type."""
        ...
    
    def get_error_response_format(self, exc: Exception) -> Dict[str, Any]:
        """Get standardized error response format."""
        ...


class ValidationExceptionProtocol(Protocol):
    """Protocol for validation exception operations."""
    
    field_errors: List[Dict[str, Any]]
    
    def add_field_error(
        self,
        field: str,
        message: str,
        value: Any = None,
        error_type: str = "validation_error"
    ) -> None:
        """Add field-specific validation error."""
        ...
    
    def get_field_errors(self) -> List[Dict[str, Any]]:
        """Get all field validation errors."""
        ...


class ErrorReporterProtocol(Protocol):
    """Protocol for error reporting and logging operations."""
    
    def report_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error"
    ) -> None:
        """Report error with context information."""
        ...
    
    def report_validation_errors(
        self,
        errors: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Report validation errors."""
        ...
    
    def get_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        ...