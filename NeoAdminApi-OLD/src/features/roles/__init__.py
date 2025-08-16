"""
Roles feature module for platform role management.
"""

from .routers.v1 import router as roles_router

__all__ = ["roles_router"]