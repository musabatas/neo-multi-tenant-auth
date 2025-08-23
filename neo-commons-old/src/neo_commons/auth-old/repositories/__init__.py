"""
Base repository implementations for authentication and permissions.
"""
from .base_auth import BaseAuthRepository
from .base_permission import BasePermissionRepository

__all__ = [
    "BaseAuthRepository",
    "BasePermissionRepository"
]