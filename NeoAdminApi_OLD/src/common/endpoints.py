"""
Common application endpoints (health, debug, etc) for NeoAdminApi.

This module now uses the generic endpoint registration from neo-commons
while providing service-specific implementations.
"""
from fastapi import FastAPI

# Import generic endpoint registration from neo-commons
from neo_commons.api.endpoints import (
    register_health_endpoints as neo_register_health,
    register_debug_endpoints as neo_register_debug
)

from src.common.config.settings import settings


def register_health_endpoints(app: FastAPI) -> None:
    """Register health check endpoints using neo-commons with Admin-specific configuration.
    
    Args:
        app: FastAPI application instance
    """
    from src.common.database.connection import get_database
    from src.common.cache.client import get_cache
    
    # Use neo-commons endpoint registration with Admin-specific dependencies
    neo_register_health(
        app,
        get_database=get_database,
        get_cache=get_cache,
        get_settings=lambda: settings
    )


def register_debug_endpoints(app: FastAPI) -> None:
    """Register debug endpoints using neo-commons with Admin-specific configuration.
    
    Args:
        app: FastAPI application instance
    """
    from src.common.database.connection import get_database
    from src.common.cache.client import get_cache
    from src.common.middleware import get_middleware_status
    from src.common.middleware.timing import get_performance_summary
    
    # Use neo-commons debug endpoint registration with Admin-specific dependencies
    neo_register_debug(
        app,
        get_settings=lambda: settings,
        get_database=get_database,
        get_cache=get_cache,
        get_middleware_status=get_middleware_status,
        get_performance_summary=get_performance_summary
    )