"""Auth dependencies configuration for NeoAdminApi.

Simple configuration that lets neo-commons handle everything.
Only passes the required realm and database configuration.
"""

import logging
from typing import Optional

from fastapi import Request
from neo_commons.core.value_objects.identifiers import TenantId
from neo_commons.features.auth import AuthServiceFactory

logger = logging.getLogger(__name__)

# Global auth factory instance
_auth_factory: Optional[AuthServiceFactory] = None


def initialize_auth_factory(
    keycloak_server_url: str,
    keycloak_admin_username: str,
    keycloak_admin_password: str,
    redis_url: str,
    redis_password: Optional[str],
    database_service,
) -> None:
    """Initialize the global auth factory instance."""
    global _auth_factory
    
    _auth_factory = AuthServiceFactory(
        keycloak_server_url=keycloak_server_url,
        keycloak_admin_username=keycloak_admin_username,
        keycloak_admin_password=keycloak_admin_password,
        redis_url=redis_url,
        redis_password=redis_password,
        database_service=database_service,
    )
    
    logger.info("Auth factory initialized for admin context")


async def get_auth_dependencies():
    """Get auth dependencies configured for admin context."""
    if not _auth_factory:
        raise RuntimeError(
            "Auth factory not initialized. Call initialize_auth_factory() first."
        )
    return await _auth_factory.get_auth_dependencies()


async def get_auth_dependencies_with_admin_defaults():
    """Get auth dependencies configured for admin context with require_tenant=False default."""
    if not _auth_factory:
        raise RuntimeError(
            "Auth factory not initialized. Call initialize_auth_factory() first."
        )
    
    auth_deps = await _auth_factory.get_auth_dependencies()
    
    # Monkey patch the get_current_user method to change the default
    original_get_current_user = auth_deps.get_current_user
    
    async def get_current_user_admin_default(request, credentials, require_tenant=False):
        return await original_get_current_user(request, credentials, require_tenant)
    
    # Replace the method
    auth_deps.get_current_user = get_current_user_admin_default
    
    return auth_deps


async def extract_tenant_id(request: Request) -> Optional[TenantId]:
    """Extract tenant ID from request headers for admin context."""
    tenant_header = request.headers.get("x-tenant-id")
    if tenant_header:
        return TenantId(tenant_header)
    return None


async def get_realm_name(tenant_id: Optional[TenantId]) -> str:
    """Get realm name for tenant - admin uses default realm if no tenant."""
    if tenant_id:
        return f"tenant-{tenant_id.value}"
    return "platform-admin"