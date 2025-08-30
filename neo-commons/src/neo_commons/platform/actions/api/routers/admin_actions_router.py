"""Admin actions router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from uuid import UUID

from ..models.requests import CreateActionRequest, UpdateActionRequest, ExecuteActionRequest
from ..models.responses import ActionResponse, ActionListResponse, ExecutionResponse, ActionMetricsResponse
from ..dependencies.action_dependencies import (
    get_action_service,
    get_action_execution_service,
    get_action_metrics_service
)
from ...application.commands.create_action import CreateActionCommand
from ...application.commands.execute_action import ExecuteActionCommand  
from ...application.queries.get_action import GetActionQuery
from ...application.queries.list_actions import ListActionsQuery, ListActionsRequest
from ...domain.value_objects.action_id import ActionId


router = APIRouter(
    prefix="/admin/actions",
    tags=["Actions Administration"]
)


@router.post("/", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
async def create_action(
    request: CreateActionRequest,
    schema: str = Query(..., description="Database schema name"),
    create_command: CreateActionCommand = Depends(get_action_service)
) -> ActionResponse:
    """Create a new action."""
    try:
        action = await create_command.execute(request, schema)
        return ActionResponse.from_domain(action)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=ActionListResponse)
async def list_actions(
    schema: str = Query(..., description="Database schema name"),
    limit: int = Query(50, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_healthy: Optional[bool] = Query(None, description="Filter by health status"),
    owner_team: Optional[str] = Query(None, description="Filter by owner team"),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> ActionListResponse:
    """List actions with filtering and pagination."""
    try:
        list_request = ListActionsRequest(
            limit=limit,
            offset=offset,
            action_type=action_type,
            is_active=is_active,
            is_healthy=is_healthy,
            owner_team=owner_team
        )
        actions = await list_query.execute(list_request, schema)
        total_count = await list_query.count_actions(None, schema)
        
        return ActionListResponse.from_domain_list(actions, total_count, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{action_id}", response_model=ActionResponse)
async def get_action(
    action_id: UUID = Path(..., description="Action ID"),
    schema: str = Query(..., description="Database schema name"),
    get_query: GetActionQuery = Depends(get_action_service)
) -> ActionResponse:
    """Get a specific action by ID."""
    try:
        action = await get_query.execute(ActionId(action_id), schema)
        if not action:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
        return ActionResponse.from_domain(action)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{action_id}", response_model=ActionResponse)
async def update_action(
    action_id: UUID = Path(..., description="Action ID"),
    request: UpdateActionRequest,
    schema: str = Query(..., description="Database schema name"),
    # TODO: Add UpdateActionCommand dependency when implemented
) -> ActionResponse:
    """Update an existing action."""
    # TODO: Implement when UpdateActionCommand is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Update action functionality not yet implemented"
    )


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action(
    action_id: UUID = Path(..., description="Action ID"),
    schema: str = Query(..., description="Database schema name"),
    # TODO: Add DeleteActionCommand dependency when implemented
):
    """Delete an action."""
    # TODO: Implement when DeleteActionCommand is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete action functionality not yet implemented"
    )


@router.post("/{action_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_action(
    action_id: UUID = Path(..., description="Action ID"),
    request: ExecuteActionRequest,
    schema: str = Query(..., description="Database schema name"),
    execute_command: ExecuteActionCommand = Depends(get_action_execution_service)
) -> ExecutionResponse:
    """Manually execute an action."""
    try:
        execution = await execute_command.execute(request, schema)
        return ExecutionResponse.from_domain(execution)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{action_id}/executions", response_model=List[ExecutionResponse])
async def get_action_executions(
    action_id: UUID = Path(..., description="Action ID"),
    schema: str = Query(..., description="Database schema name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of executions to return"),
    offset: int = Query(0, ge=0, description="Number of executions to skip"),
    # TODO: Add execution history query dependency when implemented
) -> List[ExecutionResponse]:
    """Get execution history for an action."""
    # TODO: Implement when GetExecutionHistoryQuery is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Execution history functionality not yet implemented"
    )


@router.get("/{action_id}/metrics", response_model=ActionMetricsResponse)
async def get_action_metrics(
    action_id: UUID = Path(..., description="Action ID"),
    schema: str = Query(..., description="Database schema name"),
    # TODO: Add metrics query dependency when implemented
) -> ActionMetricsResponse:
    """Get performance metrics for an action."""
    # TODO: Implement when action metrics service is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Action metrics functionality not yet implemented"
    )


@router.post("/{action_id}/health-check", status_code=status.HTTP_200_OK)
async def check_action_health(
    action_id: UUID = Path(..., description="Action ID"),
    schema: str = Query(..., description="Database schema name"),
    # TODO: Add health check command dependency when implemented
):
    """Trigger a health check for an action."""
    # TODO: Implement when health check functionality is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Health check functionality not yet implemented"
    )