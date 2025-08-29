"""Events API layer exports.

This module provides reusable API components for event operations including
request/response models, routers for different roles (admin, tenant, internal),
and dependency injection components.

Follows Maximum Separation Architecture with role-based router separation.
"""

from .models import CreateEventRequest, EventResponse

__all__ = [
    "CreateEventRequest", 
    "EventResponse",
]