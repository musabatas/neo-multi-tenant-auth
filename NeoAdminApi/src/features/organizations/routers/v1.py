"""Organizations API v1 router using neo-commons.

This module integrates neo-commons organization routers with NeoAdminApi-specific 
database configuration and dependency injection.
"""

from fastapi import FastAPI
from neo_commons.features.organizations import (
    organization_router,
    organization_admin_router,
    get_organization_repository,
    get_organization_service,
    get_basic_organization_service,
    get_admin_organization_service
)
from neo_commons.features.organizations.repositories import OrganizationDatabaseRepository
from ..adapters import DatabaseServiceAdapter
from neo_commons.features.organizations.services import OrganizationService


# Create our specific dependencies for NeoAdminApi
async def get_admin_organization_repository():
    """Get organization repository configured for admin schema."""
    from ....common.dependencies import get_database_service
    
    database_service = await get_database_service()
    # Use adapter to bridge DatabaseService and DatabaseRepository interfaces
    database_adapter = DatabaseServiceAdapter(database_service, connection_name="admin")
    return OrganizationDatabaseRepository(database_adapter, schema="admin")


async def get_admin_organization_service_impl():
    """Get organization service configured for admin operations."""
    repository = await get_admin_organization_repository()
    # No cache needed - organizations use database queries directly
    return OrganizationService(repository)


# Create routers with dependency overrides
def setup_organization_routers(app: FastAPI) -> None:
    """Setup organization routers with NeoAdminApi-specific dependencies."""
    
    # Override neo-commons dependencies with our implementations
    app.dependency_overrides.update({
        get_organization_repository: get_admin_organization_repository,
        get_organization_service: get_admin_organization_service_impl,
        get_basic_organization_service: get_admin_organization_service_impl,
        get_admin_organization_service: get_admin_organization_service_impl,
    })
    
    # Include both routers - they serve different purposes with no overlap
    # Basic router: CRUD operations at /organizations/
    app.include_router(
        organization_router, 
        prefix="/api/v1"
    )
    
    # Admin router: Administrative operations at /admin/organizations/ 
    app.include_router(
        organization_admin_router, 
        prefix="/api/v1"
    )


# Export the routers for direct use if needed
__all__ = [
    "setup_organization_routers",
    "get_admin_organization_repository", 
    "get_admin_organization_service_impl"
]