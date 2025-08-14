"""
API module for neo-commons.

This module provides FastAPI-related utilities and components.
"""

from .endpoints import (
    register_health_endpoints,
    register_debug_endpoints, 
    register_standard_endpoints,
    DefaultApplicationConfig
)
from .exception_handlers import register_exception_handlers
from .openapi_config import (
    configure_openapi, 
    ApplicationInfoProtocol,
    DefaultApplicationInfo,
    create_openapi_schema
)
from .routers import NeoAPIRouter
from .specialized_routers import (
    VersionedAPIRouter,
    SecureAPIRouter,
    CachedAPIRouter,
    AdminAPIRouter,
    TenantAPIRouter,
    PublicAPIRouter
)
from .router_factories import (
    create_api_router,
    create_admin_router,
    create_tenant_router,
    create_public_router,
    create_secure_router,
    create_cached_router,
    create_versioned_router,
    create_microservice_router,
    create_health_router,
    create_debug_router,
    create_api_router_by_type
)
from .tag_providers import (
    TagGroupProviderProtocol,
    DefaultTagGroupProvider,
    AdminTagGroupProvider,
    TenantTagGroupProvider,
    create_admin_openapi_config,
    create_tenant_openapi_config,
    create_default_openapi_config
)
from .schema_enhancers import (
    enhance_schema_with_security,
    enhance_schema_with_examples,
    enhance_schema_with_tenant_security,
    enhance_schema_with_admin_security,
    enhance_schema_with_cors_info,
    enhance_schema_with_rate_limiting_info
)

__all__ = [
    # Endpoints
    "register_health_endpoints",
    "register_debug_endpoints",
    "register_standard_endpoints", 
    "DefaultApplicationConfig",
    
    # Exception handlers
    "register_exception_handlers",
    
    # OpenAPI core
    "configure_openapi",
    "ApplicationInfoProtocol",
    "DefaultApplicationInfo",
    "create_openapi_schema",
    
    # Tag providers
    "TagGroupProviderProtocol",
    "DefaultTagGroupProvider",
    "AdminTagGroupProvider",
    "TenantTagGroupProvider",
    "create_admin_openapi_config",
    "create_tenant_openapi_config",
    "create_default_openapi_config",
    
    # Schema enhancers
    "enhance_schema_with_security",
    "enhance_schema_with_examples",
    "enhance_schema_with_tenant_security",
    "enhance_schema_with_admin_security",
    "enhance_schema_with_cors_info",
    "enhance_schema_with_rate_limiting_info",
    
    # Routers
    "create_api_router",
    "NeoAPIRouter",
    "VersionedAPIRouter",
    "SecureAPIRouter",
    "CachedAPIRouter",
    "AdminAPIRouter",
    "TenantAPIRouter", 
    "PublicAPIRouter",
    "create_admin_router",
    "create_tenant_router",
    "create_public_router",
    "create_secure_router",
    "create_cached_router",
    "create_versioned_router",
    "create_microservice_router",
    "create_health_router",
    "create_debug_router",
    "create_api_router_by_type"
]