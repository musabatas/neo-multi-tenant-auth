"""Common FastAPI dependencies using neo-commons services."""

from typing import Optional

from fastapi import Depends, Request

from neo_commons.core.value_objects.identifiers import TenantId, UserId
from neo_commons.features.auth.entities.auth_context import AuthContext
from neo_commons.features.auth.dependencies import AuthDependencies

from .config import get_config_provider


# Helper functions for extracting user context

async def get_current_user_id(
    current_user: AuthContext = Depends(AuthDependencies.get_current_user),
) -> UserId:
    """Get current user ID."""
    return current_user.user_id


async def get_current_tenant_id(
    current_user: AuthContext = Depends(AuthDependencies.get_current_user),
) -> Optional[TenantId]:
    """Get current tenant ID (may be None for platform admins)."""
    return current_user.tenant_id


# Service Dependencies using neo-commons patterns

async def get_database_service():
    """Get database service instance."""
    from neo_commons.features.database.services import DatabaseManager
    return await DatabaseManager.get_instance()


async def get_organization_service():
    """Get organization service with dependency injection."""
    from ..features.organizations.services.organization_service import OrganizationService
    from ..features.organizations.repositories.organization_repository import OrganizationRepository
    
    # Get database service
    database_service = await get_database_service()
    
    # Create repository
    repository = OrganizationRepository(database_service)
    
    # Create and return service
    return OrganizationService(repository)

async def get_auth_service():
    """Get auth service with centralized configuration."""
    from ..features.auth.services.auth_service import AuthService
    
    # Get services and configuration
    database_service = await get_database_service()
    config_provider = get_config_provider()
    
    # Get auth factory from centralized configuration
    auth_factory = await config_provider.get_auth_factory(database_service)
    
    # Create and return auth service
    return AuthService(auth_factory)

async def get_cache_service():
    """Get cache service with centralized configuration."""
    # Get services and configuration
    database_service = await get_database_service()
    config_provider = get_config_provider()
    
    # Get auth factory from centralized configuration
    auth_factory = await config_provider.get_auth_factory(database_service)
    
    # Return the cache service
    return await auth_factory.get_cache_service()


async def get_user_service():
    """Get user service with dependency injection."""
    from neo_commons.features.users.services.user_service import UserService
    from neo_commons.features.users.repositories.user_repository import UserRepository
    
    # Get database service
    database_service = await get_database_service()
    
    # Create repository
    repository = UserRepository(database_service)
    
    # Create and return service
    return UserService(repository)


async def get_tenant_service():
    """Get tenant service with dependency injection using admin schema."""
    from neo_commons.features.tenants.services import TenantService
    
    # For now, create a minimal service without repository
    # This will be updated when tenant feature is fully integrated
    class MockTenantService:
        async def list_tenants(self, **kwargs):
            return []
        async def count_tenants(self, **kwargs): 
            return 0
        async def create_tenant(self, **kwargs):
            raise NotImplementedError("Tenant creation not yet implemented")
        async def update_tenant(self, **kwargs):
            raise NotImplementedError("Tenant update not yet implemented")
        async def delete_tenant(self, **kwargs):
            raise NotImplementedError("Tenant deletion not yet implemented")
        async def get_tenant_status(self, **kwargs):
            raise NotImplementedError("Tenant status not yet implemented")
        async def provision_tenant(self, **kwargs):
            raise NotImplementedError("Tenant provisioning not yet implemented")
    
    return MockTenantService()


async def get_tenant_dependencies():
    """Get tenant dependencies for router usage."""
    from neo_commons.core.value_objects.identifiers import TenantId
    from fastapi import HTTPException, status
    
    class MockTenantDependencies:
        async def get_tenant_by_id(self, tenant_id: TenantId):
            raise HTTPException(
                status_code=501,
                detail="Tenant operations not yet implemented"
            )
        
        async def get_tenant_by_slug(self, slug: str):
            raise HTTPException(
                status_code=501,
                detail="Tenant operations not yet implemented"
            )
    
    return MockTenantDependencies()

# Request Context Dependencies

async def get_request_context(request: Request) -> dict:
    """Extract request context for logging and audit."""
    return {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request.headers.get("x-request-id"),
    }