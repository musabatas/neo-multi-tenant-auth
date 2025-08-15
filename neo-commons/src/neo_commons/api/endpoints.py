"""
Enhanced common application endpoints (health, debug, etc) for neo-commons.
Protocol-based dependency injection with improved modularity and reusability.
"""
import time
from typing import Optional, Dict, Any, Protocol, runtime_checkable
from fastapi import FastAPI, status
import logging

from neo_commons.models.base import (
    APIResponse,
    HealthCheckResponse,
    HealthStatus,
    ServiceHealth
)

logger = logging.getLogger(__name__)


@runtime_checkable
class DatabaseManagerProtocol(Protocol):
    """Protocol for database manager implementations."""
    
    async def health_check(self) -> bool:
        """Check database health."""
        ...


@runtime_checkable
class CacheManagerProtocol(Protocol):
    """Protocol for cache manager implementations."""
    
    async def health_check(self) -> bool:
        """Check cache health."""
        ...
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information."""
        ...
    
    @property
    def is_available(self) -> bool:
        """Check if cache is available."""
        ...
    
    async def connect(self) -> Optional[Any]:
        """Connect to cache."""
        ...


@runtime_checkable
class ApplicationConfigProtocol(Protocol):
    """Protocol for application configuration."""
    
    @property
    def app_name(self) -> str:
        """Application name."""
        ...
    
    @property
    def app_version(self) -> str:
        """Application version."""
        ...
    
    @property
    def environment(self) -> str:
        """Environment name."""
        ...
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        ...


class DefaultApplicationConfig:
    """Default implementation of application configuration."""
    
    def __init__(
        self,
        app_name: str = "API Application",
        app_version: str = "1.0.0",
        environment: str = "development",
        is_production: bool = False
    ):
        self._app_name = app_name
        self._app_version = app_version
        self._environment = environment
        self._is_production = is_production
    
    @property
    def app_name(self) -> str:
        return self._app_name
    
    @property
    def app_version(self) -> str:
        return self._app_version
    
    @property
    def environment(self) -> str:
        return self._environment
    
    @property
    def is_production(self) -> bool:
        return self._is_production


def register_health_endpoints(
    app: FastAPI,
    database_manager: Optional[DatabaseManagerProtocol] = None,
    cache_manager: Optional[CacheManagerProtocol] = None,
    app_config: Optional[ApplicationConfigProtocol] = None
) -> None:
    """
    Register health check endpoints with dependency injection.
    
    Args:
        app: FastAPI application instance
        database_manager: Database manager implementation
        cache_manager: Cache manager implementation
        app_config: Application configuration
    """
    config = app_config or DefaultApplicationConfig()
    
    @app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
    async def health_check():
        """Health check endpoint with configurable service checks."""
        from neo_commons.utils.datetime import utc_now
        
        services = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check database if available
        if database_manager:
            try:
                start = time.time()
                db_healthy = await database_manager.health_check()
                latency = (time.time() - start) * 1000
                
                services["database"] = ServiceHealth(
                    name="Database",
                    status=HealthStatus.HEALTHY if db_healthy else HealthStatus.UNHEALTHY,
                    latency_ms=latency
                )
                
                if not db_healthy:
                    overall_status = HealthStatus.UNHEALTHY
                    
            except Exception as e:
                services["database"] = ServiceHealth(
                    name="Database",
                    status=HealthStatus.UNHEALTHY,
                    error=str(e)
                )
                overall_status = HealthStatus.UNHEALTHY
                logger.error(f"Database health check failed: {e}")
        
        # Check cache if available
        if cache_manager:
            try:
                start = time.time()
                cache_healthy = await cache_manager.health_check()
                latency = (time.time() - start) * 1000
                
                # Get cache status info
                cache_status = cache_manager.get_cache_status()
                
                services["cache"] = ServiceHealth(
                    name="Cache",
                    status=HealthStatus.HEALTHY if cache_healthy else HealthStatus.DEGRADED,
                    latency_ms=latency if cache_healthy else None,
                    details={
                        "configured": cache_status.get("redis_configured", False),
                        "available": cache_status.get("redis_available", False),
                        "connection_attempted": cache_status.get("connection_attempted", False),
                        "performance_impact": cache_status.get("performance_impact", True),
                        "warnings": cache_status.get("warnings", [])
                    }
                )
                
                # Cache unavailable is degraded performance, not unhealthy
                if not cache_healthy and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                        
            except Exception as e:
                services["cache"] = ServiceHealth(
                    name="Cache",
                    status=HealthStatus.DEGRADED,
                    error=str(e),
                    details={
                        "message": "Cache unavailable - application running without cache",
                        "performance_impact": True
                    }
                )
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                logger.warning(f"Cache health check failed: {e}")
        
        return HealthCheckResponse(
            status=overall_status,
            version=config.app_version,
            environment=config.environment,
            timestamp=utc_now(),
            services=services
        )
    
    @app.get("/health/cache", tags=["Health"])
    async def cache_health():
        """Detailed cache health and status endpoint."""
        from neo_commons.utils.datetime import utc_now
        
        if not cache_manager:
            return APIResponse.error_response(
                message="Cache manager not configured"
            )
        
        cache_status = cache_manager.get_cache_status()
        
        # Get cache stats if available
        cache_stats = {}
        if cache_manager.is_available:
            try:
                # Try to get cache info if available
                client = await cache_manager.connect()
                if client and hasattr(client, 'info'):
                    info = await client.info()
                    cache_stats = {
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory_human": info.get("used_memory_human", "N/A"),
                        "keyspace_hits": info.get("keyspace_hits", 0),
                        "keyspace_misses": info.get("keyspace_misses", 0)
                    }
            except Exception as e:
                logger.warning(f"Failed to get cache stats: {e}")
        
        recommendations = []
        if not cache_status.get("redis_available", False):
            recommendations.append("Install and configure Redis for optimal performance")
        elif cache_status.get("redis_available", False) and config.is_production:
            recommendations.append("Consider Redis clustering for production workloads")
        
        return APIResponse.success_response(
            data={
                "timestamp": utc_now(),
                "cache_status": cache_status,
                "cache_stats": cache_stats,
                "recommendations": [r for r in recommendations if r]
            },
            message="Cache status retrieved successfully"
        )
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with application information."""
        docs_info = {}
        if not config.is_production:
            docs_info = {
                "docs": "/docs",
                "swagger": "/swagger", 
                "redoc": "/redoc"
            }
        
        return {
            "name": config.app_name,
            "version": config.app_version,
            "environment": config.environment,
            **docs_info
        }


def register_debug_endpoints(
    app: FastAPI,
    database_manager: Optional[DatabaseManagerProtocol] = None,
    cache_manager: Optional[CacheManagerProtocol] = None,
    app_config: Optional[ApplicationConfigProtocol] = None
) -> None:
    """
    Register debug endpoints (non-production only) with dependency injection.
    
    Args:
        app: FastAPI application instance
        database_manager: Database manager implementation
        cache_manager: Cache manager implementation
        app_config: Application configuration
    """
    config = app_config or DefaultApplicationConfig()
    
    if config.is_production:
        logger.info("Debug endpoints disabled in production environment")
        return
    
    @app.get("/debug/middleware", tags=["Debug"], include_in_schema=False)
    async def middleware_status():
        """Get middleware configuration and status."""
        try:
            # Try to import middleware status functions if available
            middleware_status = {}
            performance_summary = {}
            
            try:
                from neo_commons.middleware import get_middleware_status
                middleware_status = get_middleware_status()
            except ImportError:
                middleware_status = {"status": "middleware status not available"}
            
            try:
                from neo_commons.middleware.timing import get_performance_summary
                performance_summary = get_performance_summary()
            except ImportError:
                performance_summary = {"status": "performance summary not available"}
            
            return {
                "middleware_status": middleware_status,
                "performance_summary": performance_summary,
                "environment": config.environment,
                "note": "This endpoint is only available in non-production environments"
            }
        except Exception as e:
            logger.error(f"Debug middleware endpoint failed: {e}")
            return {"error": "Failed to retrieve middleware status"}
    
    @app.get("/debug/metadata-test", tags=["Debug"], include_in_schema=False)
    async def test_metadata():
        """Test endpoint to verify metadata collection and service health."""
        operations_performed = {
            "database_operations": 0,
            "cache_operations": 0
        }
        
        # Test database operations if available
        if database_manager:
            try:
                # Simple database health check
                await database_manager.health_check()
                operations_performed["database_operations"] = 1
                logger.debug("Database test operation completed")
            except Exception as e:
                logger.warning(f"Database test operation failed: {e}")
        
        # Test cache operations if available
        if cache_manager:
            try:
                # Simple cache operations
                await cache_manager.health_check()
                operations_performed["cache_operations"] = 1
                logger.debug("Cache test operation completed")
            except Exception as e:
                logger.warning(f"Cache test operation failed: {e}")
        
        return APIResponse.success_response(
            data={
                "message": "Metadata test endpoint",
                "operations_simulated": operations_performed,
                "services_tested": {
                    "database_available": database_manager is not None,
                    "cache_available": cache_manager is not None
                }
            },
            message="Test completed successfully"
        )


def register_standard_endpoints(
    app: FastAPI,
    database_manager: Optional[DatabaseManagerProtocol] = None,
    cache_manager: Optional[CacheManagerProtocol] = None,
    app_config: Optional[ApplicationConfigProtocol] = None,
    include_debug: bool = True
) -> None:
    """
    Register all standard endpoints (health + debug) with dependency injection.
    
    Args:
        app: FastAPI application instance
        database_manager: Database manager implementation
        cache_manager: Cache manager implementation
        app_config: Application configuration
        include_debug: Whether to include debug endpoints
    """
    # Always register health endpoints
    register_health_endpoints(
        app=app,
        database_manager=database_manager,
        cache_manager=cache_manager,
        app_config=app_config
    )
    
    # Register debug endpoints if requested
    if include_debug:
        register_debug_endpoints(
            app=app,
            database_manager=database_manager,
            cache_manager=cache_manager,
            app_config=app_config
        )
    
    logger.info(f"Registered standard endpoints for {app_config.app_name if app_config else 'API Application'}")