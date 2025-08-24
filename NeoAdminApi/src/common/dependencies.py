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
    from ..features.auth.services.auth_service import AuthService
    from neo_commons.features.auth import AuthServiceFactory
    from neo_commons.config.manager import get_env_config
    
    # Get database service
    database_service = await get_database_service()
    
    # Get centralized configuration
    env_config = get_env_config()
    
    # Create auth factory using neo-commons with database service
    auth_factory = AuthServiceFactory(
        keycloak_server_url=env_config.keycloak_server_url,
        keycloak_admin_username=env_config.keycloak_admin or "admin",
        keycloak_admin_password=env_config.keycloak_password or "admin",
        redis_url=env_config.redis_url,
        redis_password=env_config.redis_password,
        database_service=database_service,
    )
    
    # Create and return auth service
    return AuthService(auth_factory)

async def get_cache_service():
    """Get cache service for cache management endpoints."""
    from neo_commons.features.auth import AuthServiceFactory
    from neo_commons.config.manager import get_env_config
    
    # Get database service
    database_service = await get_database_service()
    
    # Get centralized configuration
    env_config = get_env_config()
    
    # Create auth factory to get cache service
    auth_factory = AuthServiceFactory(
        keycloak_server_url=env_config.keycloak_server_url,
        keycloak_admin_username=env_config.keycloak_admin or "admin",
        keycloak_admin_password=env_config.keycloak_password or "admin",
        redis_url=env_config.redis_url,
        redis_password=env_config.redis_password,
        database_service=database_service,
    )
    
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