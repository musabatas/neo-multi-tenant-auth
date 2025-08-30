"""Action routers."""

from .admin_actions_router import router as admin_actions_router
from .tenant_actions_router import router as tenant_actions_router
from .internal_actions_router import router as internal_actions_router

__all__ = [
    "admin_actions_router",
    "tenant_actions_router", 
    "internal_actions_router",
]