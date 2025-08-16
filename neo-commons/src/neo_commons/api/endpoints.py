"""
Common application endpoints (health, debug, etc) for FastAPI applications.

This module provides reusable endpoint registration functions that can be used
across all Neo services for consistent health checks and debugging.
"""
import time
from typing import Optional, Dict, Any, Callable, Awaitable
from fastapi import FastAPI, status
from loguru import logger

from neo_commons.models.base import (
    APIResponse,
    HealthCheckResponse,
    HealthStatus,
    ServiceHealth
)


async def default_database_health_check() -> tuple[bool, float]:
    """Default database health check implementation.
    
    Returns:
        Tuple of (is_healthy, latency_ms)
    """
    # This is a placeholder - services should provide their own implementation
    return True, 0.0


async def default_cache_health_check() -> tuple[bool, float, Dict[str, Any]]:
    """Default cache health check implementation.
    
    Returns:
        Tuple of (is_healthy, latency_ms, cache_status)
    """
    # This is a placeholder - services should provide their own implementation
    return True, 0.0, {"configured": False, "available": False}


def register_health_endpoints(
    app: FastAPI,
    get_database: Optional[Callable[[], Any]] = None,
    get_cache: Optional[Callable[[], Any]] = None,
    get_settings: Optional[Callable[[], Any]] = None,
    additional_checks: Optional[Dict[str, Callable[[], Awaitable[ServiceHealth]]]] = None
) -> None:
    """Register health check endpoints with customizable service checks.
    
    Args:
        app: FastAPI application instance
        get_database: Function to get database connection for health check
        get_cache: Function to get cache client for health check
        get_settings: Function to get application settings
        additional_checks: Optional additional service health checks
    
    Example:
        ```python
        from neo_commons.api.endpoints import register_health_endpoints
        from src.common.database.connection import get_database
        from src.common.cache.client import get_cache
        from src.common.config.settings import settings
        
        register_health_endpoints(
            app,
            get_database=get_database,
            get_cache=get_cache,
            get_settings=lambda: settings
        )
        ```
    """
    @app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        from neo_commons.utils.datetime import utc_now
        
        services = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check database if provided
        if get_database:
            try:
                start = time.time()
                db = get_database()
                
                # Check if db has health_check method
                if hasattr(db, 'health_check'):
                    db_healthy = await db.health_check()
                else:
                    # Fallback to simple query
                    await db.fetchval("SELECT 1")
                    db_healthy = True
                    
                latency = (time.time() - start) * 1000
                
                services["database"] = ServiceHealth(
                    name="PostgreSQL",
                    status=HealthStatus.HEALTHY if db_healthy else HealthStatus.UNHEALTHY,
                    latency_ms=latency
                )
                
                if not db_healthy:
                    overall_status = HealthStatus.UNHEALTHY
                    
            except Exception as e:
                services["database"] = ServiceHealth(
                    name="PostgreSQL",
                    status=HealthStatus.UNHEALTHY,
                    error=str(e)
                )
                overall_status = HealthStatus.UNHEALTHY
        
        # Check cache if provided
        if get_cache:
            try:
                start = time.time()
                cache = get_cache()
                
                # Check if cache has health_check method
                if hasattr(cache, 'health_check'):
                    cache_healthy = await cache.health_check()
                else:
                    # Fallback to ping
                    cache_healthy = await cache.ping() if hasattr(cache, 'ping') else True
                    
                latency = (time.time() - start) * 1000
                
                # Get cache status info if available
                cache_status = {}
                if hasattr(cache, 'get_cache_status'):
                    cache_status = cache.get_cache_status()
                
                services["cache"] = ServiceHealth(
                    name="Redis",
                    status=HealthStatus.HEALTHY if cache_healthy else HealthStatus.DEGRADED,
                    latency_ms=latency if cache_healthy else None,
                    details=cache_status if cache_status else None
                )
                
                # Cache unavailable is degraded performance, not unhealthy
                if not cache_healthy and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                        
            except Exception as e:
                services["cache"] = ServiceHealth(
                    name="Redis",
                    status=HealthStatus.DEGRADED,
                    error=str(e),
                    details={
                        "message": "Cache unavailable - application running without cache",
                        "performance_impact": True
                    }
                )
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        # Run additional health checks if provided
        if additional_checks:
            for check_name, check_func in additional_checks.items():
                try:
                    service_health = await check_func()
                    services[check_name] = service_health
                    
                    if service_health.status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                    elif service_health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                        
                except Exception as e:
                    services[check_name] = ServiceHealth(
                        name=check_name,
                        status=HealthStatus.UNHEALTHY,
                        error=str(e)
                    )
                    overall_status = HealthStatus.UNHEALTHY
        
        # Get settings for version info
        settings = get_settings() if get_settings else None
        
        return HealthCheckResponse(
            status=overall_status,
            version=getattr(settings, 'app_version', 'unknown') if settings else 'unknown',
            environment=getattr(settings, 'environment', 'unknown') if settings else 'unknown',
            timestamp=utc_now(),
            services=services
        )
    
    # Cache health endpoint if cache is provided
    if get_cache:
        @app.get("/health/cache", tags=["Health"])
        async def cache_health():
            """Detailed cache health and status endpoint."""
            from neo_commons.utils.datetime import utc_now
            
            cache = get_cache()
            cache_status = {}
            
            # Get cache status if available
            if hasattr(cache, 'get_cache_status'):
                cache_status = cache.get_cache_status()
            
            # Get cache stats if available
            cache_stats = {}
            if hasattr(cache, 'is_available') and cache.is_available:
                try:
                    # Try to get Redis info if available
                    if hasattr(cache, 'connect'):
                        client = await cache.connect()
                        if client and hasattr(client, 'info'):
                            info = await client.info()
                            cache_stats = {
                                "connected_clients": info.get("connected_clients", 0),
                                "used_memory_human": info.get("used_memory_human", "N/A"),
                                "keyspace_hits": info.get("keyspace_hits", 0),
                                "keyspace_misses": info.get("keyspace_misses", 0)
                            }
                except Exception:
                    pass
            
            # Get settings for recommendations
            settings = get_settings() if get_settings else None
            is_production = getattr(settings, 'is_production', False) if settings else False
            
            return APIResponse.success_response(
                data={
                    "timestamp": utc_now(),
                    "cache_status": cache_status,
                    "cache_stats": cache_stats,
                    "recommendations": [
                        "Install and configure Redis for optimal performance" 
                        if not cache_status.get("redis_available", False) else None,
                        "Consider Redis clustering for production workloads" 
                        if cache_status.get("redis_available", False) and is_production else None
                    ]
                },
                message="Cache status retrieved successfully"
            )
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint."""
        settings = get_settings() if get_settings else None
        is_production = getattr(settings, 'is_production', False) if settings else False
        
        return {
            "name": getattr(settings, 'app_name', 'Neo Service') if settings else 'Neo Service',
            "version": getattr(settings, 'app_version', 'unknown') if settings else 'unknown',
            "environment": getattr(settings, 'environment', 'unknown') if settings else 'unknown',
            "docs": "/docs" if not is_production else None,
            "swagger": "/swagger" if not is_production else None,
            "redoc": "/redoc" if not is_production else None
        }


def register_debug_endpoints(
    app: FastAPI,
    get_settings: Optional[Callable[[], Any]] = None,
    get_database: Optional[Callable[[], Any]] = None,
    get_cache: Optional[Callable[[], Any]] = None,
    get_middleware_status: Optional[Callable[[], Dict[str, Any]]] = None,
    get_performance_summary: Optional[Callable[[], Dict[str, Any]]] = None
) -> None:
    """Register debug endpoints (non-production only).
    
    Args:
        app: FastAPI application instance
        get_settings: Function to get application settings
        get_database: Function to get database connection
        get_cache: Function to get cache client
        get_middleware_status: Function to get middleware status
        get_performance_summary: Function to get performance summary
    """
    # Check if production environment
    settings = get_settings() if get_settings else None
    is_production = getattr(settings, 'is_production', False) if settings else False
    
    if is_production:
        return
    
    @app.get("/debug/info", tags=["Debug"], include_in_schema=False)
    async def debug_info():
        """Get debug information about the application."""
        return {
            "environment": getattr(settings, 'environment', 'unknown') if settings else 'unknown',
            "debug_enabled": not is_production,
            "database_configured": get_database is not None,
            "cache_configured": get_cache is not None,
            "middleware_status_available": get_middleware_status is not None,
            "performance_monitoring": get_performance_summary is not None,
            "note": "This endpoint is only available in non-production environments"
        }
    
    if get_middleware_status:
        @app.get("/middleware", tags=["Debug"], include_in_schema=False)
        async def middleware_status():
            """Get middleware configuration and status."""
            result = {
                "middleware_status": get_middleware_status(),
                "environment": getattr(settings, 'environment', 'unknown') if settings else 'unknown',
                "note": "This endpoint is only available in non-production environments"
            }
            
            if get_performance_summary:
                result["performance_summary"] = get_performance_summary()
            
            return result
    
    if get_database and get_cache:
        @app.get("/metadata-test", tags=["Debug"], include_in_schema=False)
        async def test_metadata():
            """Test endpoint to verify metadata collection."""
            from neo_commons.utils.metadata import MetadataCollector
            
            # Simulate some database operations
            db = get_database()
            if hasattr(db, 'fetchval'):
                await db.fetchval("SELECT 1")
                await db.fetchval("SELECT 2")
            
            # Simulate some cache operations
            cache = get_cache()
            if hasattr(cache, 'get'):
                await cache.get("test_key_that_does_not_exist")  # Miss
            if hasattr(cache, 'set'):
                await cache.set("test_key", "test_value", ttl=10)  # Set
            if hasattr(cache, 'get'):
                await cache.get("test_key")  # Hit
            
            return APIResponse.success_response(
                data={
                    "message": "Metadata test endpoint",
                    "operations_simulated": {
                        "db_queries": 2,
                        "cache_operations": 3
                    }
                },
                message="Test completed successfully"
            )