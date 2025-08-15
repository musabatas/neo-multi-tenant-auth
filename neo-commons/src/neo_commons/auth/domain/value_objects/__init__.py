"""
Authorization domain value objects.

Immutable value types for authorization operations.
"""

from .permission_check import PermissionCheck, PermissionResult
from .user_context import UserContext, UserType
from .tenant_context import TenantContext

__all__ = [
    "PermissionCheck",
    "PermissionResult", 
    "UserContext",
    "UserType",
    "TenantContext"
]