"""
Authentication and permission repositories.

Base repository implementations for authentication and permission management
with dynamic schema configuration and protocol compliance.
"""

from .base_auth import BaseAuthRepository
from .base_permission import BasePermissionRepository

__all__ = [
    "BaseAuthRepository",
    "BasePermissionRepository",
]
