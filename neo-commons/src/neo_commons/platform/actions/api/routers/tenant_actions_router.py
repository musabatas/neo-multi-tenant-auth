"""Tenant actions router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from uuid import UUID

from ..models.requests import CreateActionRequest, UpdateActionRequest, ExecuteActionRequest
from ..models.responses import ActionResponse, ActionListResponse, ExecutionResponse
from ..dependencies.action_dependencies import (
    get_action_service,
    get_action_execution_service,
    get_tenant_schema_resolver
)
from ...application.commands.create_action import CreateActionCommand
from ...application.commands.execute_action import ExecuteActionCommand
from ...application.queries.get_action import GetActionQuery
from ...application.queries.list_actions import ListActionsQuery, ListActionsRequest
from ...domain.value_objects.action_id import ActionId


router = APIRouter(
    prefix="/tenant/{tenant_id}/actions",
    tags=["Tenant Actions"]
)


@router.post("/", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_action(
    tenant_id: str = Path(..., description="Tenant ID"),
    request: CreateActionRequest,
    schema: str = Depends(get_tenant_schema_resolver),
    create_command: CreateActionCommand = Depends(get_action_service)
) -> ActionResponse:
    """Create a new action for a tenant."""
    try:
        action = await create_command.execute(request, schema)
        return ActionResponse.from_domain(action)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=ActionListResponse)
async def list_tenant_actions(
    tenant_id: str = Path(..., description="Tenant ID"),
    limit: int = Query(50, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_healthy: Optional[bool] = Query(None, description="Filter by health status"),
    owner_team: Optional[str] = Query(None, description="Filter by owner team"),
    schema: str = Depends(get_tenant_schema_resolver),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> ActionListResponse:
    """List actions for a tenant."""
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
async def get_tenant_action(
    tenant_id: str = Path(..., description="Tenant ID"),
    action_id: UUID = Path(..., description="Action ID"),
    schema: str = Depends(get_tenant_schema_resolver),
    get_query: GetActionQuery = Depends(get_action_service)
) -> ActionResponse:
    """Get a specific tenant action by ID."""
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
async def update_tenant_action(
    tenant_id: str = Path(..., description="Tenant ID"),
    action_id: UUID = Path(..., description="Action ID"),
    request: UpdateActionRequest,
    schema: str = Depends(get_tenant_schema_resolver),
    # TODO: Add UpdateActionCommand dependency when implemented
) -> ActionResponse:
    """Update a tenant action."""
    # TODO: Implement when UpdateActionCommand is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Update action functionality not yet implemented"
    )


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_action(
    tenant_id: str = Path(..., description="Tenant ID"),
    action_id: UUID = Path(..., description="Action ID"),
    schema: str = Depends(get_tenant_schema_resolver),
    # TODO: Add DeleteActionCommand dependency when implemented
):
    """Delete a tenant action."""
    # TODO: Implement when DeleteActionCommand is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete action functionality not yet implemented"
    )


@router.post("/{action_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_tenant_action(
    tenant_id: str = Path(..., description="Tenant ID"),
    action_id: UUID = Path(..., description="Action ID"),
    request: ExecuteActionRequest,
    schema: str = Depends(get_tenant_schema_resolver),
    execute_command: ExecuteActionCommand = Depends(get_action_execution_service)
) -> ExecutionResponse:
    """Execute a tenant action."""
    try:
        # Ensure the action ID matches the path parameter
        if request.action_id != action_id:
            raise ValueError("Action ID in request body must match path parameter")
            
        execution = await execute_command.execute(request, schema)
        return ExecutionResponse.from_domain(execution)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{action_id}/executions", response_model=List[ExecutionResponse])
async def get_tenant_action_executions(
    tenant_id: str = Path(..., description="Tenant ID"),
    action_id: UUID = Path(..., description="Action ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of executions to return"),
    offset: int = Query(0, ge=0, description="Number of executions to skip"),
    schema: str = Depends(get_tenant_schema_resolver),
    # TODO: Add execution history query dependency when implemented
) -> List[ExecutionResponse]:
    """Get execution history for a tenant action."""
    # TODO: Implement when GetExecutionHistoryQuery is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Execution history functionality not yet implemented"
    )


@router.get("/active", response_model=ActionListResponse)
async def list_active_tenant_actions(
    tenant_id: str = Path(..., description="Tenant ID"),
    limit: int = Query(50, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    schema: str = Depends(get_tenant_schema_resolver),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> ActionListResponse:
    """List only active actions for a tenant."""
    try:
        actions = await list_query.find_active_actions(schema)
        # Apply pagination manually since find_active_actions doesn't support it
        paginated_actions = actions[offset:offset + limit]
        total_count = len(actions)
        
        return ActionListResponse.from_domain_list(paginated_actions, total_count, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/healthy", response_model=ActionListResponse)
async def list_healthy_tenant_actions(
    tenant_id: str = Path(..., description="Tenant ID"),
    limit: int = Query(50, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    schema: str = Depends(get_tenant_schema_resolver),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> ActionListResponse:
    """List only healthy actions for a tenant."""
    try:
        actions = await list_query.find_healthy_actions(schema)
        # Apply pagination manually since find_healthy_actions doesn't support it
        paginated_actions = actions[offset:offset + limit]
        total_count = len(actions)
        
        return ActionListResponse.from_domain_list(paginated_actions, total_count, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))