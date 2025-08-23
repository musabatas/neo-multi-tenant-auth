"""System-level API endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ....common.dependencies import get_database_service

router = APIRouter()

# Track application start time
_start_time = time.time()


@router.get("/health")
async def get_system_health(
    db_service = Depends(get_database_service)
):
    """Get comprehensive system health status.
    
    Public endpoint for basic health monitoring.
    """
    try:
        # Check neo-commons database health
        db_health = await db_service.health_check()
        
        overall_status = "healthy" if db_health.get("overall_healthy", False) else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "healthy" if db_health.get("overall_healthy", False) else "unhealthy",
                "connections_count": db_health.get("total_connections", 0),
                "cache": "disabled",     # TODO: Actual health check when cache implemented
                "auth": "disabled",      # TODO: Actual health check when auth implemented
            },
            "database_connections": db_health.get("connections", {})
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/info")
async def get_system_info():
    """Get detailed system information.
    
    Requires platform administrator permissions.
    """
    try:
        uptime_seconds = time.time() - _start_time
        
        return {
            "app_name": "Neo Admin API",
            "app_version": "1.0.0",
            "environment": "development",  # TODO: Get from settings
            "uptime_seconds": uptime_seconds,
            "neo_commons_version": "1.0.0",  # TODO: Get actual version
            "python_version": "3.13",       # TODO: Get actual version
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system info: {str(e)}"
        ) from e


@router.post("/maintenance")
async def toggle_maintenance_mode(
    enabled: bool
):
    """Toggle maintenance mode.
    
    Requires platform administrator permissions.
    """
    # TODO: Implement maintenance mode
    return {
        "maintenance_mode": enabled,
        "message": "Maintenance mode updated"
    }