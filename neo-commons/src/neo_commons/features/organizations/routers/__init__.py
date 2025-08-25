"""Organization routers.

Ready-to-use FastAPI routers for organization functionality that services
can include directly without duplicating routing logic.
"""

from .organization_router import router as organization_router
from .admin_router import admin_router as organization_admin_router
from .dependencies import (
    get_organization_repository,
    get_organization_cache,
    get_organization_service,
    get_basic_organization_service,
    get_admin_organization_service
)

__all__ = [
    # Main routers
    "organization_router",
    "organization_admin_router",
    
    # Dependencies
    "get_organization_repository", 
    "get_organization_cache",
    "get_organization_service",
    "get_basic_organization_service", 
    "get_admin_organization_service"
]