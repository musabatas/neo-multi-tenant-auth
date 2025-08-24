"""Tenants feature module - core tenant management using existing neo-commons infrastructure.

This feature provides tenant operations without duplicating existing database,
cache, or configuration services. All implementations use dependency injection
with existing neo-commons infrastructure.
"""

# Domain entities and protocols
from .entities import (
    Tenant,
    TenantRepository,
    TenantCache,
    TenantConfigResolver
)

# Service implementations
from .services import (
    TenantService,
    TenantConfigurationResolver,
    TenantCacheAdapter
)

# Repository implementations
from .repositories import TenantDatabaseRepository

# Router implementations
from .routers import tenant_router, TenantDependencies

# Request/Response models
from .models import (
    TenantCreateRequest,
    TenantUpdateRequest,
    TenantProvisionRequest,
    TenantConfigRequest,
    TenantResponse,
    TenantListResponse,
    TenantStatusResponse,
    TenantConfigResponse,
    TenantHealthResponse
)

__all__ = [
    # Domain entities
    "Tenant",
    
    # Protocols
    "TenantRepository",
    "TenantCache",
    "TenantConfigResolver",
    
    # Services
    "TenantService",
    "TenantConfigurationResolver", 
    "TenantCacheAdapter",
    
    # Repositories
    "TenantDatabaseRepository",
    
    # Routers
    "tenant_router",
    "TenantDependencies",
    
    # Request models
    "TenantCreateRequest",
    "TenantUpdateRequest",
    "TenantProvisionRequest", 
    "TenantConfigRequest",
    
    # Response models
    "TenantResponse",
    "TenantListResponse",
    "TenantStatusResponse",
    "TenantConfigResponse",
    "TenantHealthResponse",
]