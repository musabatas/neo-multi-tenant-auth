"""
API routers exports for platform events system.

Role-based routers for cross-service usage following maximum separation architecture.
"""

from .admin_events_router import admin_events_router
from .internal_events_router import internal_events_router
from .public_events_router import public_events_router
from .tenant_events_router import tenant_events_router

__all__ = [
    "admin_events_router",
    "internal_events_router", 
    "public_events_router",
    "tenant_events_router",
]