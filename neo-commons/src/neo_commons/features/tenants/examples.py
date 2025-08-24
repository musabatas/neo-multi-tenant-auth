"""Example usage of the rebuilt tenants feature.

Demonstrates how to use the tenant feature with existing neo-commons
infrastructure without code duplication.
"""

from typing import Optional

# Import existing neo-commons infrastructure
from ...features.database.services import DatabaseService
from ...features.cache.services import CacheService
from ...infrastructure.configuration.services import ConfigurationService

# Import rebuilt tenant feature
from . import (
    Tenant,
    TenantService,
    TenantDatabaseRepository,
    TenantCacheAdapter,
    TenantConfigurationResolver
)
from ...core.value_objects import TenantId, OrganizationId


async def create_tenant_service_example() -> TenantService:
    """Example of creating TenantService using existing infrastructure.
    
    This shows how the rebuilt tenant feature integrates with existing
    neo-commons services without duplication.
    """
    
    # Use existing database service (accepts any connection)
    database_service = DatabaseService()
    await database_service.initialize()
    
    # Create tenant repository using existing database infrastructure
    tenant_repository = TenantDatabaseRepository(
        database_repository=database_service.repository,
        schema="admin"  # Can use any schema
    )
    
    # Use existing cache service
    cache_service = CacheService()
    await cache_service.initialize()
    
    # Create tenant cache adapter using existing cache
    tenant_cache = TenantCacheAdapter(
        cache=cache_service.cache,
        ttl=3600
    )
    
    # Use existing configuration service
    config_service = ConfigurationService()
    await config_service.initialize()
    
    # Create tenant config resolver using existing config infrastructure
    tenant_config_resolver = TenantConfigurationResolver(
        config_provider=config_service.provider
    )
    
    # Create tenant service with all dependencies injected
    tenant_service = TenantService(
        repository=tenant_repository,
        cache=tenant_cache,
        config_resolver=tenant_config_resolver
    )
    
    return tenant_service


async def tenant_operations_example():
    """Example of common tenant operations."""
    
    # Create tenant service
    tenant_service = await create_tenant_service_example()
    
    # Create a new tenant
    org_id = OrganizationId.generate()
    tenant = await tenant_service.create_tenant(
        organization_id=org_id,
        slug="acme-corp",
        name="Acme Corporation",
        description="Leading provider of widgets",
        custom_domain="acme.example.com"
    )
    
    print(f"Created tenant: {tenant.id} with slug '{tenant.slug}'")
    print(f"Schema name: {tenant.schema_name}")
    
    # Get tenant by ID (uses cache automatically)
    cached_tenant = await tenant_service.get_by_id(tenant.id)
    print(f"Retrieved tenant: {cached_tenant.name}")
    
    # Get tenant by slug
    tenant_by_slug = await tenant_service.get_by_slug("acme-corp")
    print(f"Found by slug: {tenant_by_slug.name}")
    
    # Set tenant-specific configuration
    await tenant_service.set_tenant_config(tenant.id, "max_users", 100)
    await tenant_service.set_tenant_config(tenant.id, "features.analytics", True)
    
    # Get tenant configuration with fallback
    max_users = await tenant_service.get_tenant_config(tenant.id, "max_users", default=50)
    analytics_enabled = await tenant_service.get_tenant_config(tenant.id, "features.analytics", default=False)
    
    print(f"Max users: {max_users}")
    print(f"Analytics enabled: {analytics_enabled}")
    
    # Start provisioning
    provisioning_tenant = await tenant_service.provision_tenant(tenant.id)
    print(f"Tenant status: {provisioning_tenant.status.value}")
    
    # Activate tenant
    active_tenant = await tenant_service.activate_tenant(tenant.id)
    print(f"Tenant status: {active_tenant.status.value}")
    
    # Get all tenants for organization
    org_tenants = await tenant_service.get_by_organization(org_id)
    print(f"Organization has {len(org_tenants)} tenants")
    
    # Update tenant activity
    await tenant_service.update_tenant_activity(tenant.id)
    
    return tenant


async def tenant_with_custom_database_example():
    """Example showing how to use tenant feature with custom database connection."""
    
    # Create custom database service with specific connection
    custom_db_service = DatabaseService()
    await custom_db_service.initialize()
    
    # Add custom connection (this would typically be done at startup)
    # await custom_db_service.add_connection("tenant_db", "postgresql://...")
    
    # Create tenant repository using custom connection
    tenant_repository = TenantDatabaseRepository(
        database_repository=custom_db_service.repository,
        schema="custom_tenant_schema"  # Can use any schema
    )
    
    # Create minimal tenant service (no cache or config)
    tenant_service = TenantService(repository=tenant_repository)
    
    # Use the service
    tenant = await tenant_service.create_tenant(
        organization_id=OrganizationId.generate(),
        slug="custom-tenant",
        name="Custom Tenant"
    )
    
    print(f"Created tenant in custom database: {tenant.id}")
    
    return tenant


# This example shows the key benefits of the rebuilt tenant feature:
#
# 1. **DRY Compliance**: No duplication of database, cache, or config logic
# 2. **Flexible Integration**: Works with any database connection/schema
# 3. **Protocol-Based**: Uses dependency injection for testability
# 4. **Existing Infrastructure**: Leverages all existing neo-commons services
# 5. **Clean Architecture**: Clear separation between domain, service, and infrastructure
#
# The tenant feature is now a true "feature" that orchestrates existing
# infrastructure rather than reimplementing it.