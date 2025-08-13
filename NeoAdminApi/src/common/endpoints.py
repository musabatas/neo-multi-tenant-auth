"""
Common application endpoints (health, debug, etc).
"""
import time
from fastapi import FastAPI, status
from loguru import logger

from src.common.config.settings import settings
from src.common.models.base import (
    APIResponse,
    HealthCheckResponse,
    HealthStatus,
    ServiceHealth
)


def register_health_endpoints(app: FastAPI) -> None:
    """Register health check endpoints.
    
    Args:
        app: FastAPI application instance
    """
    @app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        from src.common.database.connection import get_database
        from src.common.cache.client import get_cache
        from src.common.utils.datetime import utc_now
        
        services = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check database
        try:
            start = time.time()
            db = get_database()
            db_healthy = await db.health_check()
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
        
        # Check cache
        try:
            start = time.time()
            cache = get_cache()
            cache_healthy = await cache.health_check()
            latency = (time.time() - start) * 1000
            
            services["cache"] = ServiceHealth(
                name="Redis",
                status=HealthStatus.HEALTHY if cache_healthy else HealthStatus.UNHEALTHY,
                latency_ms=latency
            )
            
            if not cache_healthy:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
        except Exception as e:
            services["cache"] = ServiceHealth(
                name="Redis",
                status=HealthStatus.UNHEALTHY,
                error=str(e)
            )
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return HealthCheckResponse(
            status=overall_status,
            version=settings.app_version,
            environment=settings.environment,
            timestamp=utc_now(),
            services=services
        )
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "docs": "/docs" if not settings.is_production else None,
            "swagger": "/swagger" if not settings.is_production else None,
            "redoc": "/redoc" if not settings.is_production else None
        }


def register_debug_endpoints(app: FastAPI) -> None:
    """Register debug endpoints (non-production only).
    
    Args:
        app: FastAPI application instance
    """
    if settings.is_production:
        return
    
    @app.get("/middleware", tags=["Debug"], include_in_schema=False)
    async def middleware_status():
        """Get middleware configuration and status."""
        from src.common.middleware import get_middleware_status
        from src.common.middleware.timing import get_performance_summary
        
        return {
            "middleware_status": get_middleware_status(),
            "performance_summary": get_performance_summary(),
            "environment": settings.environment,
            "note": "This endpoint is only available in non-production environments"
        }
    
    @app.get("/metadata-test", tags=["Debug"], include_in_schema=False)
    async def test_metadata():
        """Test endpoint to verify metadata collection."""
        from src.common.database.connection import get_database
        from src.common.cache.client import get_cache
        from src.common.utils.metadata import MetadataCollector
        
        # Simulate some database operations
        db = get_database()
        await db.fetchval("SELECT 1")
        await db.fetchval("SELECT 2")
        
        # Simulate some cache operations
        cache = get_cache()
        await cache.get("test_key_that_does_not_exist")  # Miss
        await cache.set("test_key", "test_value", ttl=10)  # Set
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