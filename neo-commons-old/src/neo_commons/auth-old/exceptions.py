"""
Authentication and Authorization Exceptions

Standardized exception hierarchy for auth-related errors with:
- Rate limiting violations
- Authentication failures
- Authorization denials
- Token validation errors
- Session management failures
"""

from typing import Optional, Dict, Any
from datetime import datetime


class AuthError(Exception):
    """Base exception for all authentication/authorization errors"""
    
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


class RateLimitError(AuthError):
    """Rate limit exceeded exception"""
    
    def __init__(
        self, 
        message: str,
        reset_time: Optional[datetime] = None,
        limit_type: Optional[str] = None,
        requests_remaining: int = 0
    ):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")
        self.reset_time = reset_time
        self.limit_type = limit_type
        self.requests_remaining = requests_remaining
        
        # Add rate limit details
        self.details.update({
            "reset_time": reset_time.isoformat() if reset_time else None,
            "limit_type": limit_type,
            "requests_remaining": requests_remaining
        })


class AuthenticationError(AuthError):
    """Authentication failed exception"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_FAILED")


class AuthorizationError(AuthError):
    """Authorization failed exception"""
    
    def __init__(
        self, 
        message: str = "Authorization failed",
        required_permissions: Optional[list] = None,
        user_permissions: Optional[list] = None
    ):
        super().__init__(message, "AUTHORIZATION_FAILED")
        self.details.update({
            "required_permissions": required_permissions,
            "user_permissions": user_permissions
        })


class TokenValidationError(AuthError):
    """Token validation failed exception"""
    
    def __init__(
        self, 
        message: str = "Token validation failed",
        token_type: Optional[str] = None
    ):
        super().__init__(message, "TOKEN_VALIDATION_FAILED")
        self.details["token_type"] = token_type


class SessionExpiredError(AuthError):
    """Session expired exception"""
    
    def __init__(self, message: str = "Session expired"):
        super().__init__(message, "SESSION_EXPIRED")


class SessionNotFoundError(AuthError):
    """Session not found exception"""
    
    def __init__(self, message: str = "Session not found"):
        super().__init__(message, "SESSION_NOT_FOUND")


class UserNotFoundError(AuthError):
    """User not found exception"""
    
    def __init__(self, message: str = "User not found", user_id: Optional[str] = None):
        super().__init__(message, "USER_NOT_FOUND")
        self.details["user_id"] = user_id


class PermissionNotFoundError(AuthError):
    """Permission not found exception"""
    
    def __init__(
        self, 
        message: str = "Permission not found", 
        permission_code: Optional[str] = None
    ):
        super().__init__(message, "PERMISSION_NOT_FOUND")
        self.details["permission_code"] = permission_code


class RealmNotFoundError(AuthError):
    """Keycloak realm not found exception"""
    
    def __init__(self, message: str = "Realm not found", realm: Optional[str] = None):
        super().__init__(message, "REALM_NOT_FOUND")
        self.details["realm"] = realm


class ConfigurationError(AuthError):
    """Authentication configuration error"""
    
    def __init__(self, message: str = "Authentication configuration error"):
        super().__init__(message, "CONFIGURATION_ERROR")