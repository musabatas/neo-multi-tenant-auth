"""Database management API endpoints."""

import uuid
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


@router.get("/connections/{connection_identifier}/health")
async def check_connection_health(
    connection_identifier: str,
    db_service = Depends(get_database_service)
):
    """Check health of a specific database connection.
    
    Args:
        connection_identifier: Either connection name or connection ID (UUID)
        db_service: Database service dependency
        
    Returns:
        Health status of the specified connection
    """
    try:
        from neo_commons.core.value_objects.identifiers import DatabaseConnectionId
        import uuid
        
        # First, try to find the connection
        connection = None
        
        # Check if identifier looks like a UUID
        try:
            # Try to parse as UUID
            uuid_obj = uuid.UUID(connection_identifier)
            # It's a valid UUID, try to get by ID
            connection_id = DatabaseConnectionId(str(uuid_obj))
            connection = await db_service.connection_registry.get_connection(connection_id)
            
            if not connection:
                # UUID not found, might still be a connection name that looks like UUID
                connection = await db_service.connection_registry.get_connection_by_name(connection_identifier)
        except (ValueError, AttributeError):
            # Not a UUID, treat as connection name
            connection = await db_service.connection_registry.get_connection_by_name(connection_identifier)
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_identifier}"
            )
        
        # Get health status from the connection object (it's a property, not a method)
        health_info = connection.health_status
        
        # Try to get pool stats if available
        pool_stats = None
        try:
            pool = await db_service.get_connection_pool(connection.connection_name)
            # AsyncConnectionPool doesn't have get_stats, but we can get basic info
            pool_stats = {
                "size": pool._size if hasattr(pool, '_size') else None,
                "max_size": pool._maxsize if hasattr(pool, '_maxsize') else None,
                "min_size": pool._minsize if hasattr(pool, '_minsize') else None,
            }
        except Exception:
            pass  # Pool stats are optional
        
        return {
            "connection_id": connection.id.value,
            "connection_name": connection.connection_name,
            "status": "healthy" if connection.is_healthy else "unhealthy",
            "is_active": connection.is_active,
            "is_available": connection.is_available,
            "health_details": health_info,
            "pool_stats": pool_stats,
            "last_health_check": connection.last_health_check.isoformat() if connection.last_health_check else None,
            "consecutive_failures": connection.consecutive_failures
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Try to find connection info for error response
        try:
            # Try both methods to get connection info
            from neo_commons.core.value_objects.identifiers import DatabaseConnectionId
            import uuid
            
            connection = None
            try:
                uuid_obj = uuid.UUID(connection_identifier)
                connection_id = DatabaseConnectionId(str(uuid_obj))
                connection = await db_service.connection_registry.get_connection(connection_id)
            except:
                connection = await db_service.connection_registry.get_connection_by_name(connection_identifier)
            
            if connection:
                return {
                    "connection_id": connection.id.value if hasattr(connection.id, 'value') else str(connection.id),
                    "connection_name": connection.connection_name,
                    "status": "unhealthy",
                    "is_active": connection.is_active,
                    "is_available": False,
                    "error": str(e),
                    "consecutive_failures": connection.consecutive_failures
                }
        except:
            pass
        
        # Fallback error response
        return {
            "connection_identifier": connection_identifier,
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