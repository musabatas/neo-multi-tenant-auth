"""Example usage of organization routers in services.

This file demonstrates how services can use neo-commons organization routers
without duplicating routing logic. Services override the placeholder dependencies
with their actual implementations.
"""

from fastapi import FastAPI, Depends
from fastapi.routing import APIRouter

# Import the ready-to-use routers from neo-commons
from .routers import (
    organization_router,
    organization_admin_router,
    get_organization_repository,
    get_organization_service,
    get_basic_organization_service,
    get_admin_organization_service
)

# Example service implementations
from .repositories import OrganizationDatabaseRepository
from .services import OrganizationService


def create_example_service_app() -> FastAPI:
    """Example of how a service would integrate organization routers.
    
    This shows the pattern services should follow:
    1. Override dependency functions with actual implementations
    2. Include the routers in the FastAPI app
    3. Configure any service-specific middleware or settings
    """
    app = FastAPI(title="Example Service with Organization Routes")
    
    # Override dependency functions with actual implementations
    async def get_actual_organization_repository():
        """Service-specific repository implementation."""
        # In a real service, this would get the database service
        # and return a configured repository
        database_service = None  # await get_database_service()
        return OrganizationDatabaseRepository(database_service)
    
    async def get_actual_organization_service():
        """Service-specific service implementation."""
        repository = await get_actual_organization_repository()
        cache_service = None  # await get_cache_service()
        return OrganizationService(repository, cache_service)
    
    # Override the dependency functions
    app.dependency_overrides.update({
        get_organization_repository: get_actual_organization_repository,
        get_organization_service: get_actual_organization_service,
        get_basic_organization_service: get_actual_organization_service,
        get_admin_organization_service: get_actual_organization_service,
    })
    
    # Include the neo-commons routers
    app.include_router(organization_router, prefix="/api/v1")
    app.include_router(organization_admin_router, prefix="/api/v1/admin")
    
    return app


# Alternative approach using router groups
def create_router_group_example() -> APIRouter:
    """Example of grouping organization routes within a larger API.
    
    This approach is useful when the service has multiple feature areas
    and wants to organize routes hierarchically.
    """
    api_router = APIRouter(prefix="/api/v1")
    
    # Include organization routes as a sub-group
    api_router.include_router(organization_router, prefix="/organizations")
    api_router.include_router(organization_admin_router, prefix="/admin/organizations")
    
    # Could include other feature routers here
    # api_router.include_router(user_router, prefix="/users")
    # api_router.include_router(tenant_router, prefix="/tenants")
    
    return api_router


# Service-specific customizations
def create_customized_organization_router() -> APIRouter:
    """Example of customizing organization routes for specific service needs.
    
    Services can create their own router that includes the base organization
    functionality plus service-specific endpoints.
    """
    custom_router = APIRouter(prefix="/organizations", tags=["Organizations"])
    
    # Include all the standard organization routes
    custom_router.include_router(organization_router, prefix="")
    
    # Add service-specific endpoints
    @custom_router.get("/health")
    async def organization_health():
        """Service-specific health check for organization functionality."""
        return {"status": "healthy", "feature": "organizations"}
    
    @custom_router.get("/stats")
    async def organization_stats():
        """Service-specific statistics endpoint."""
        return {"total": 0, "active": 0, "verified": 0}
    
    return custom_router


if __name__ == "__main__":
    """Example of running the service with organization routes."""
    import uvicorn
    
    app = create_example_service_app()
    
    # The service now has all organization CRUD operations available:
    # POST   /api/v1/organizations/              - Create organization
    # GET    /api/v1/organizations/              - List organizations  
    # GET    /api/v1/organizations/{id}          - Get organization by ID
    # PUT    /api/v1/organizations/{id}          - Update organization
    # DELETE /api/v1/organizations/{id}          - Delete organization
    # GET    /api/v1/organizations/slug/{slug}   - Get by slug
    # POST   /api/v1/organizations/search        - Search organizations
    # And all admin routes under /api/v1/admin/organizations/
    
    uvicorn.run(app, host="0.0.0.0", port=8000)