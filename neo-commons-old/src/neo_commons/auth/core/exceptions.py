"""
Authentication and authorization exceptions.

Comprehensive exception hierarchy for auth-related errors with structured
error codes, details, and context information for better debugging and
error handling in the authentication system.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class AuthError(Exception):
    """
    Base exception for all authentication and authorization errors.
    
    Provides structured error information including error codes, details,
    and context for consistent error handling across the auth system.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error context and metadata
        timestamp: When the error occurred
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        
        # Add timestamp to details for logging
        self.details["timestamp"] = self.timestamp.isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class AuthenticationError(AuthError):
    """
    Authentication failed exception.
    
    Raised when user credentials are invalid, tokens are malformed,
    or authentication process fails for any reason.
    """
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        reason: Optional[str] = None,
        provider: Optional[str] = None
    ):
        super().__init__(message, "AUTHENTICATION_FAILED")
        if reason:
            self.details["reason"] = reason
        if provider:
            self.details["provider"] = provider


class AuthorizationError(AuthError):
    """
    Authorization failed exception.
    
    Raised when authenticated user lacks required permissions
    to perform the requested operation.
    """
    
    def __init__(
        self, 
        message: str = "Authorization failed",
        required_permissions: Optional[List[str]] = None,
        user_permissions: Optional[List[str]] = None,
        resource: Optional[str] = None
    ):
        super().__init__(message, "AUTHORIZATION_FAILED")
        self.details.update({
            "required_permissions": required_permissions or [],
            "user_permissions": user_permissions or [],
            "resource": resource
        })


class TokenValidationError(AuthError):
    """
    Token validation failed exception.
    
    Raised when JWT tokens are invalid, expired, malformed,
    or fail signature verification.
    """
    
    def __init__(
        self, 
        message: str = "Token validation failed",
        token_type: Optional[str] = None,
        reason: Optional[str] = None,
        realm: Optional[str] = None
    ):
        super().__init__(message, "TOKEN_VALIDATION_FAILED")
        self.details.update({
            "token_type": token_type,
            "reason": reason,
            "realm": realm
        })


class PermissionDeniedError(AuthError):
    """
    Permission denied exception.
    
    Raised when user explicitly lacks permission for a specific operation,
    providing detailed context about the denied permission.
    """
    
    def __init__(
        self, 
        message: str = "Permission denied",
        permission: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None
    ):
        super().__init__(message, "PERMISSION_DENIED")
        self.details.update({
            "permission": permission,
            "resource": resource,
            "action": action
        })


class SessionError(AuthError):
    """Base exception for session-related errors."""
    
    def __init__(
        self, 
        message: str,
        error_code: str,
        session_id: Optional[str] = None
    ):
        super().__init__(message, error_code)
        if session_id:
            self.details["session_id"] = session_id


class SessionExpiredError(SessionError):
    """
    Session expired exception.
    
    Raised when user session has expired and requires re-authentication.
    """
    
    def __init__(
        self, 
        message: str = "Session expired",
        session_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        super().__init__(message, "SESSION_EXPIRED", session_id)
        if expires_at:
            self.details["expires_at"] = expires_at.isoformat()


class SessionNotFoundError(SessionError):
    """
    Session not found exception.
    
    Raised when attempting to access a session that doesn't exist.
    """
    
    def __init__(
        self, 
        message: str = "Session not found",
        session_id: Optional[str] = None
    ):
        super().__init__(message, "SESSION_NOT_FOUND", session_id)


class RateLimitError(AuthError):
    """
    Rate limit exceeded exception.
    
    Raised when user or application exceeds configured rate limits
    for authentication operations.
    """
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        reset_time: Optional[datetime] = None,
        limit_type: Optional[str] = None,
        requests_remaining: int = 0,
        limit: Optional[int] = None
    ):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")
        self.reset_time = reset_time
        self.limit_type = limit_type
        self.requests_remaining = requests_remaining
        
        # Add rate limit details
        self.details.update({
            "reset_time": reset_time.isoformat() if reset_time else None,
            "limit_type": limit_type,
            "requests_remaining": requests_remaining,
            "limit": limit
        })


class UserNotFoundError(AuthError):
    """
    User not found exception.
    
    Raised when attempting to access a user that doesn't exist
    in the authentication system.
    """
    
    def __init__(
        self, 
        message: str = "User not found", 
        user_id: Optional[str] = None,
        external_id: Optional[str] = None,
        provider: Optional[str] = None
    ):
        super().__init__(message, "USER_NOT_FOUND")
        self.details.update({
            "user_id": user_id,
            "external_id": external_id,
            "provider": provider
        })


class PermissionNotFoundError(AuthError):
    """
    Permission not found exception.
    
    Raised when attempting to check a permission that doesn't exist
    in the permission registry.
    """
    
    def __init__(
        self, 
        message: str = "Permission not found", 
        permission_code: Optional[str] = None,
        scope: Optional[str] = None
    ):
        super().__init__(message, "PERMISSION_NOT_FOUND")
        self.details.update({
            "permission_code": permission_code,
            "scope": scope
        })


class RealmNotFoundError(AuthError):
    """
    Keycloak realm not found exception.
    
    Raised when attempting to access a Keycloak realm that doesn't exist
    or is not configured for the tenant.
    """
    
    def __init__(
        self, 
        message: str = "Realm not found", 
        realm: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        super().__init__(message, "REALM_NOT_FOUND")
        self.details.update({
            "realm": realm,
            "tenant_id": tenant_id
        })


class ConfigurationError(AuthError):
    """
    Authentication configuration error.
    
    Raised when authentication system is misconfigured or
    required configuration is missing.
    """
    
    def __init__(
        self, 
        message: str = "Authentication configuration error",
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None
    ):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.details.update({
            "config_key": config_key,
            "expected_type": expected_type
        })


class ExternalServiceError(AuthError):
    """
    External service error.
    
    Raised when external authentication services (like Keycloak)
    are unavailable or return errors.
    """
    
    def __init__(
        self, 
        message: str = "External service error",
        service: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")
        self.details.update({
            "service": service,
            "status_code": status_code,
            "response_data": response_data
        })


class CacheError(AuthError):
    """
    Cache operation error.
    
    Raised when cache operations fail, affecting performance
    but not necessarily blocking authentication.
    """
    
    def __init__(
        self, 
        message: str = "Cache operation failed",
        operation: Optional[str] = None,
        cache_key: Optional[str] = None
    ):
        super().__init__(message, "CACHE_ERROR")
        self.details.update({
            "operation": operation,
            "cache_key": cache_key
        })


class ValidationError(AuthError):
    """
    Input validation error.
    
    Raised when authentication input data fails validation rules.
    """
    
    def __init__(
        self, 
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[str] = None,
        constraint: Optional[str] = None
    ):
        super().__init__(message, "VALIDATION_ERROR")
        self.details.update({
            "field": field,
            "value": value,
            "constraint": constraint
        })


class ConflictError(AuthError):
    """
    Resource conflict error.
    
    Raised when attempting to create or modify a resource that conflicts
    with existing resources (e.g., duplicate user, permission already exists).
    """
    
    def __init__(
        self, 
        message: str = "Resource conflict",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        conflict_field: Optional[str] = None
    ):
        super().__init__(message, "RESOURCE_CONFLICT")
        self.details.update({
            "resource_type": resource_type,
            "resource_id": resource_id,
            "conflict_field": conflict_field
        })


__all__ = [
    # Base exception
    "AuthError",
    
    # Authentication errors
    "AuthenticationError",
    "AuthorizationError", 
    "TokenValidationError",
    "PermissionDeniedError",
    
    # Session errors
    "SessionError",
    "SessionExpiredError",
    "SessionNotFoundError",
    
    # Rate limiting
    "RateLimitError",
    
    # Resource not found
    "UserNotFoundError",
    "PermissionNotFoundError",
    "RealmNotFoundError",
    
    # System errors
    "ConfigurationError",
    "ExternalServiceError",
    "CacheError",
    "ValidationError",
    "ConflictError",
]