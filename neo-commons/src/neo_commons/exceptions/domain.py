"""
Domain-specific exceptions for business logic errors.
"""
from typing import Optional
from uuid import UUID

from .base import NeoCommonsException


class TenantError(NeoCommonsException):
    """Base exception for tenant-related errors."""
    
    def __init__(
        self,
        message: str,
        tenant_id: Optional[UUID] = None,
        tenant_slug: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if tenant_id:
            self.details["tenant_id"] = str(tenant_id)
        if tenant_slug:
            self.details["tenant_slug"] = tenant_slug


class TenantProvisioningError(TenantError):
    """Raised when tenant provisioning fails."""
    
    def __init__(
        self,
        message: str = "Tenant provisioning failed",
        step: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=500, **kwargs)
        if step:
            self.details["failed_step"] = step


class QuotaExceededError(NeoCommonsException):
    """Raised when a quota is exceeded."""
    
    def __init__(
        self,
        message: str = "Quota exceeded",
        quota_type: Optional[str] = None,
        current_usage: Optional[int] = None,
        quota_limit: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, status_code=402, **kwargs)
        if quota_type:
            self.details["quota_type"] = quota_type
        if current_usage is not None:
            self.details["current_usage"] = current_usage
        if quota_limit is not None:
            self.details["quota_limit"] = quota_limit


class MigrationError(NeoCommonsException):
    """Raised when migration fails."""
    
    def __init__(
        self,
        message: str = "Migration failed",
        migration_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=500, **kwargs)
        if migration_id:
            self.details["migration_id"] = migration_id


class ConfigurationError(NeoCommonsException):
    """Raised when configuration is invalid."""
    
    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, status_code=500, **kwargs)
        if config_key:
            self.details["config_key"] = config_key