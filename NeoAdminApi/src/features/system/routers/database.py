"""Database management API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ....common.dependencies import get_database_service

router = APIRouter()


@router.get("/connections")
async def list_database_connections(
    db_service = Depends(get_database_service)
):
    """List all database connections.
    
    Connections are automatically loaded from admin.database_connections table on startup.
    Use POST /database/connections/reload to refresh connections from database.
    """
    try:
        # Get all registered connections from neo-commons registry
        registry_connections = await db_service.connection_registry.get_all_connections()
        
        return {
            "connections": [conn.to_dict() for conn in registry_connections],
            "total": len(registry_connections),
            "source": "neo_commons_registry"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list database connections: {str(e)}"
        ) from e


@router.post("/connections/reload")
async def reload_database_connections(
    db_service = Depends(get_database_service)
):
    """Manually reload database connections from admin.database_connections table.
    
    Connections are automatically loaded on startup, but this endpoint allows 
    refreshing the connections if the database configuration has been updated.
    """
    try:
        from ..services.connection_loader import DatabaseConnectionLoader
        import os
        
        # Get admin database URL from environment
        admin_db_url = os.getenv("ADMIN_DATABASE_URL")
        if not admin_db_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ADMIN_DATABASE_URL environment variable not configured"
            )
        
        # Create connection loader
        loader = DatabaseConnectionLoader(
            admin_database_url=admin_db_url,
            connection_registry=db_service.connection_registry
        )
        
        # Clear existing connections first (except admin) to avoid duplicates
        all_connections = await db_service.connection_registry.get_all_connections()
        for conn in all_connections:
            if conn.connection_name != "admin":  # Keep admin connection
                await db_service.connection_registry.remove_connection(conn.id)
        
        # Load and register all connections
        result = await loader.load_and_register_all()
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reload connections: {result['error']}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload database connections: {str(e)}"
        ) from e


@router.get("/connections/{connection_name}/health")
async def check_connection_health(
    connection_name: str,
    db_service = Depends(get_database_service)
):
    """Check health of a specific database connection."""
    try:
        # Try to get the connection pool and check its health
        pool = await db_service.get_connection_pool(connection_name)
        stats = await pool.get_stats()
        
        return {
            "connection_name": connection_name,
            "status": "healthy",
            "stats": stats
        }
        
    except Exception as e:
        return {
            "connection_name": connection_name,
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/stats")
async def get_database_stats(
    db_service = Depends(get_database_service)
):
    """Get comprehensive database statistics."""
    try:
        # Get connection stats
        connection_stats = await db_service.get_connection_stats()
        
        # Get health status
        health_status = await db_service.health_check()
        
        return {
            "connection_stats": connection_stats,
            "health_status": health_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database stats: {str(e)}"
        ) from e