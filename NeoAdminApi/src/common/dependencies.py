"""Common FastAPI dependencies using neo-commons services."""

from typing import Optional

from fastapi import Depends, Request

from neo_commons.core.value_objects.identifiers import TenantId, UserId
from neo_commons.features.auth.entities.auth_context import AuthContext
from neo_commons.features.auth.dependencies import AuthDependencies


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
    """Get auth service with neo-commons auth factory."""
    import os
    from ..features.auth.services.auth_service import AuthService
    from neo_commons.features.auth import AuthServiceFactory
    
    # Get database service
    database_service = await get_database_service()
    
    # Create auth factory using neo-commons with database service
    auth_factory = AuthServiceFactory(
        keycloak_server_url=os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080"),
        keycloak_admin_username=os.getenv("KEYCLOAK_ADMIN", "admin"),
        keycloak_admin_password=os.getenv("KEYCLOAK_PASSWORD", "admin"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        redis_password=os.getenv("REDIS_PASSWORD", "redis"),
        database_service=database_service,
    )
    
    # Create and return auth service
    return AuthService(auth_factory)

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