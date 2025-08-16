"""
Authentication and authorization decorators.
"""
from .permissions import require_permission, RequirePermission

__all__ = [
    "require_permission",
    "RequirePermission"
]