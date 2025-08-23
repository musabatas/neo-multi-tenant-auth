"""
Organizations feature module.
"""

from .routers.v1 import router as organizations_router

__all__ = ["organizations_router"]