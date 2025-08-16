"""
API routes for database connection management.
"""

from typing import Optional
from fastapi import Depends, Query, HTTPException, status
from src.common.routers.base import NeoAPIRouter

from src.common.models.base import APIResponse
from src.features.auth.dependencies import CheckPermission
from ..models.request import DatabaseConnectionFilter, HealthCheckRequest
from ..models.response import DatabaseConnectionListResponse, DatabaseConnectionResponse
from ..services.database_service import DatabaseConnectionService

router = NeoAPIRouter()


def get_database_service() -> DatabaseConnectionService:
    """Dependency to get database service."""
    return DatabaseConnectionService()


@router.get(
    "",
    response_model=APIResponse[DatabaseConnectionListResponse],
    summary="List database connections",
    description="Get a paginated list of database connections with health status information"
)
async def list_database_connections(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    region_id: Optional[str] = Query(None, description="Filter by region ID"),
    connection_type: Optional[str] = Query(None, description="Filter by connection type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_healthy: Optional[bool] = Query(None, description="Filter by health status"),
    search: Optional[str] = Query(None, description="Search in connection or database name"),
    service: DatabaseConnectionService = Depends(get_database_service),
    current_user: dict = Depends(CheckPermission(["databases:read"], scope="platform"))
) -> APIResponse[DatabaseConnectionListResponse]:
    """
    List all database connections with pagination and filtering.
    
    This endpoint provides:
    - Paginated list of database connections
    - Health status for each connection
    - Summary statistics across all connections
    - Filtering by region, type, health status
    - Search functionality
    """
    try:
        # Create filter object
        filters = DatabaseConnectionFilter(
            region_id=region_id,
            connection_type=connection_type,
            is_active=is_active,
            is_healthy=is_healthy,
            search=search
        )
        
        # Get connections
        result = await service.list_connections(
            page=page,
            page_size=page_size,
            filters=filters
        )
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result.items)} database connections"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/health-check",
    response_model=APIResponse,
    summary="Perform health checks",
    description="Trigger health checks on database connections"
)
async def perform_health_checks(
    request: HealthCheckRequest,
    service: DatabaseConnectionService = Depends(get_database_service),
    current_user: dict = Depends(CheckPermission(["databases:health_check"], scope="platform"))
) -> APIResponse:
    """
    Perform health checks on database connections.
    
    This endpoint allows you to:
    - Check specific connections by ID
    - Check all active connections
    - Force re-check even if recently checked
    - Configure timeout for health checks
    
    Health checks verify:
    - Connection availability
    - Query execution capability
    - Response time
    """
    try:
        result = await service.perform_health_checks(request)
        
        return APIResponse.success_response(
            data=result,
            message=f"Health check completed: {result['healthy']}/{result['checked']} healthy"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/health/summary",
    response_model=APIResponse,
    summary="Get health summary",
    description="Get summary health statistics for all database connections"
)
async def get_health_summary(
    service: DatabaseConnectionService = Depends(get_database_service),
    current_user: dict = Depends(CheckPermission(["databases:read"], scope="platform"))
) -> APIResponse:
    """
    Get summary health statistics for all database connections.
    
    Returns aggregated statistics including:
    - Total, active, healthy, degraded, and unhealthy counts
    - Breakdown by connection type
    - Breakdown by region
    - Overall health score
    """
    try:
        summary = await service.repository.get_summary_stats()
        
        return APIResponse.success_response(
            data=summary,
            message="Health summary retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# This route must come LAST to avoid matching specific paths like /health/summary
@router.get(
    "/{connection_id}",
    response_model=APIResponse[DatabaseConnectionResponse],
    summary="Get database connection details",
    description="Get detailed information about a specific database connection"
)
async def get_database_connection(
    connection_id: str,
    service: DatabaseConnectionService = Depends(get_database_service),
    current_user: dict = Depends(CheckPermission(["databases:read"], scope="platform"))
) -> APIResponse[DatabaseConnectionResponse]:
    """
    Get detailed information about a specific database connection.
    
    This includes:
    - Connection configuration
    - Pool settings
    - Current health status
    - Region information
    """
    try:
        result = await service.get_connection(connection_id)
        
        return APIResponse.success_response(
            data=result,
            message="Database connection retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )