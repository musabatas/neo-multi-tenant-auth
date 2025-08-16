"""
Base exception classes for the application.
"""
from typing import Optional, Any, Dict, List


class NeoAdminException(Exception):
    """Base exception for all application exceptions."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
            "status_code": self.status_code
        }


class ValidationError(NeoAdminException):
    """Raised when validation fails."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message, status_code=400, **kwargs)
        self.details["errors"] = errors or []


class NotFoundError(NeoAdminException):
    """Raised when a resource is not found."""
    
    def __init__(
        self,
        resource: str,
        identifier: Optional[Any] = None,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            if identifier:
                message = f"{resource} with id '{identifier}' not found"
            else:
                message = f"{resource} not found"
        
        super().__init__(message, status_code=404, **kwargs)
        self.details["resource"] = resource
        if identifier:
            self.details["identifier"] = str(identifier)


class ConflictError(NeoAdminException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        conflicting_field: Optional[str] = None,
        conflicting_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, status_code=409, **kwargs)
        if conflicting_field:
            self.details["field"] = conflicting_field
        if conflicting_value:
            self.details["value"] = str(conflicting_value)


class UnauthorizedError(NeoAdminException):
    """Raised when authentication is required but not provided."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        **kwargs
    ):
        super().__init__(message, status_code=401, **kwargs)


class ForbiddenError(NeoAdminException):
    """Raised when user doesn't have permission."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=403, **kwargs)
        if required_permission:
            self.details["required_permission"] = required_permission
        if resource:
            self.details["resource"] = resource


class BadRequestError(NeoAdminException):
    """Raised when request is malformed or invalid."""
    
    def __init__(
        self,
        message: str = "Bad request",
        **kwargs
    ):
        super().__init__(message, status_code=400, **kwargs)


class RateLimitError(NeoAdminException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, status_code=429, **kwargs)
        if retry_after:
            self.details["retry_after"] = retry_after


class ExternalServiceError(NeoAdminException):
    """Raised when an external service call fails."""
    
    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=503, **kwargs)
        if service:
            self.details["service"] = service






