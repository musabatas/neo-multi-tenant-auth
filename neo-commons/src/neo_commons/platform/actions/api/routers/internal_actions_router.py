"""Internal actions router for service-to-service communication."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID

from ..models.requests import ExecuteActionRequest
from ..models.responses import ActionResponse, ExecutionResponse
from ..dependencies.action_dependencies import (
    get_action_service,
    get_action_execution_service,
    get_event_matcher_service
)
from ...application.commands.execute_action import ExecuteActionCommand
from ...application.queries.get_action import GetActionQuery
from ...application.queries.list_actions import ListActionsQuery
from ...domain.value_objects.action_id import ActionId
from ...domain.value_objects.action_type import ActionType


router = APIRouter(
    prefix="/internal/actions",
    tags=["Internal Actions"],
    include_in_schema=False  # Hide from public API documentation
)


@router.post("/execute-by-event", response_model=List[ExecutionResponse])
async def execute_actions_for_event(
    event_type: str = Query(..., description="Event type"),
    event_data: dict = Query(..., description="Event data"),
    schema: str = Query(..., description="Database schema name"),
    tenant_id: Optional[str] = Query(None, description="Tenant ID filter"),
    organization_id: Optional[str] = Query(None, description="Organization ID filter"),
    source_service: Optional[str] = Query(None, description="Source service filter"),
    execute_command: ExecuteActionCommand = Depends(get_action_execution_service),
    event_matcher = Depends(get_event_matcher_service)
) -> List[ExecutionResponse]:
    """Execute all actions matching an event pattern."""
    try:
        # Find matching actions for the event
        matching_actions = await event_matcher.find_matching_actions(
            event_type=event_type,
            schema=schema,
            tenant_id=tenant_id,
            organization_id=organization_id,
            source_service=source_service
        )
        
        executions = []
        for action in matching_actions:
            # Create execution request for each matching action
            execution_request = ExecuteActionRequest(
                action_id=action.id.value,
                input_data=event_data,
                context_data={
                    "event_type": event_type,
                    "tenant_id": tenant_id,
                    "organization_id": organization_id,
                    "source_service": source_service
                }
            )
            
            try:
                execution = await execute_command.execute(execution_request, schema)
                executions.append(ExecutionResponse.from_domain(execution))
            except Exception as e:
                # Log error but continue with other actions
                # TODO: Add proper logging
                continue
        
        return executions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/by-type/{action_type}", response_model=List[ActionResponse])
async def get_actions_by_type(
    action_type: ActionType,
    schema: str = Query(..., description="Database schema name"),
    is_active: bool = Query(True, description="Filter by active status"),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> List[ActionResponse]:
    """Get all actions of a specific type."""
    try:
        actions = await list_query.find_by_type(action_type, schema)
        
        # Filter by active status if requested
        if is_active:
            actions = [action for action in actions if action.is_active]
        
        return [ActionResponse.from_domain(action) for action in actions]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/by-pattern/{event_pattern}", response_model=List[ActionResponse])
async def get_actions_by_event_pattern(
    event_pattern: str,
    schema: str = Query(..., description="Database schema name"),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> List[ActionResponse]:
    """Get all actions matching an event pattern."""
    try:
        actions = await list_query.find_by_event_pattern(event_pattern, schema)
        return [ActionResponse.from_domain(action) for action in actions]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/health-status", response_model=dict)
async def get_actions_health_status(
    schema: str = Query(..., description="Database schema name"),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> dict:
    """Get overall health status of actions."""
    try:
        healthy_actions = await list_query.find_healthy_actions(schema)
        active_actions = await list_query.find_active_actions(schema)
        
        total_healthy = len(healthy_actions)
        total_active = len(active_actions)
        
        health_percentage = (total_healthy / total_active * 100) if total_active > 0 else 100
        
        return {
            "total_active_actions": total_active,
            "total_healthy_actions": total_healthy,
            "health_percentage": round(health_percentage, 2),
            "status": "healthy" if health_percentage >= 95 else "degraded" if health_percentage >= 80 else "unhealthy"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/validate-handler/{handler_class}")
async def validate_action_handler(
    handler_class: str,
    # TODO: Add handler validation service dependency when implemented
) -> dict:
    """Validate if an action handler class is valid and loadable."""
    # TODO: Implement when handler validation service is created
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Handler validation functionality not yet implemented"
    )


@router.post("/bulk-execute", response_model=List[ExecutionResponse])
async def bulk_execute_actions(
    action_ids: List[UUID],
    input_data: dict,
    schema: str = Query(..., description="Database schema name"),
    execute_command: ExecuteActionCommand = Depends(get_action_execution_service)
) -> List[ExecutionResponse]:
    """Execute multiple actions with the same input data."""
    try:
        executions = []
        for action_id in action_ids:
            execution_request = ExecuteActionRequest(
                action_id=action_id,
                input_data=input_data
            )
            
            try:
                execution = await execute_command.execute(execution_request, schema)
                executions.append(ExecutionResponse.from_domain(execution))
            except Exception as e:
                # Continue with other actions even if one fails
                # TODO: Add proper logging
                continue
        
        return executions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/statistics", response_model=dict)
async def get_actions_statistics(
    schema: str = Query(..., description="Database schema name"),
    list_query: ListActionsQuery = Depends(get_action_service)
) -> dict:
    """Get basic statistics about actions."""
    try:
        active_actions = await list_query.find_active_actions(schema)
        healthy_actions = await list_query.find_healthy_actions(schema)
        
        # Count by action type
        type_counts = {}
        for action in active_actions:
            action_type = action.action_type.value
            type_counts[action_type] = type_counts.get(action_type, 0) + 1
        
        return {
            "total_active_actions": len(active_actions),
            "total_healthy_actions": len(healthy_actions),
            "actions_by_type": type_counts,
            "health_percentage": (len(healthy_actions) / len(active_actions) * 100) if active_actions else 100
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))