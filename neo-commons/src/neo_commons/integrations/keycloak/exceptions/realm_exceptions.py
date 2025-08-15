"""
Exception classes for realm management operations.

Provides specialized exceptions for realm management errors.
"""
from typing import Optional
from datetime import datetime, timezone


class RealmManagerException(Exception):
    """Custom exception for realm management operations."""
    
    def __init__(self, message: str, realm_name: Optional[str] = None, tenant_id: Optional[str] = None):
        super().__init__(message)
        self.realm_name = realm_name
        self.tenant_id = tenant_id
        self.timestamp = datetime.now(timezone.utc)


class RealmNotConfiguredException(RealmManagerException):
    """Exception raised when tenant has no realm configured."""
    pass


class RealmCreationException(RealmManagerException):
    """Exception raised when realm creation fails."""
    pass