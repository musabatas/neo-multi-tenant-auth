"""Event action management API endpoints for NeoAdminApi."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import (
    EventActionCreateRequest,
    EventActionUpdateRequest, 
    EventActionResponse,
    EventActionListResponse,
    ActionTestRequest,
    ActionTestResponse,
    ActionStatsResponse,
    ActionExecutionListResponse
)
from ..dependencies import get_admin_event_action_service
from ..services import AdminEventActionService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/", response_model=EventActionListResponse)
async def list_event_actions(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by action status"),
    handler_type: Optional[str] = Query(None, description="Filter by handler type"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    search: Optional[str] = Query(None, description="Search in name or description"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> EventActionListResponse:
    """List event actions with pagination and filtering."""
    try:
        actions, total = await event_service.list_actions(
            skip=skip,
            limit=limit,
            status=status,
            handler_type=handler_type,
            event_type=event_type,
            search=search,
            tenant_id=tenant_id
        )
        
        # Convert skip/limit to page/size for response model
        page = (skip // limit) + 1 if limit > 0 else 1
        size = limit
        
        return EventActionListResponse(
            actions=[EventActionResponse.from_entity(action) for action in actions],
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"Failed to list event actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list event actions: {str(e)}"
        )


@router.post("/", response_model=EventActionResponse, status_code=status.HTTP_201_CREATED)
async def create_event_action(
    request: EventActionCreateRequest,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
    # TODO: Add current_user dependency when authentication is enabled
    # current_user = Depends(get_current_user),
) -> EventActionResponse:
    """Create a new event action."""
    try:
        # TODO: Use current_user.id when authentication is enabled
        created_by_user_id = None  # str(current_user.id) 
        
        action = await event_service.create_action(request, created_by_user_id)
        return EventActionResponse.from_entity(action)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create event action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event action: {str(e)}"
        )


@router.get("/{action_id}", response_model=EventActionResponse)
async def get_event_action(
    action_id: UUID,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> EventActionResponse:
    """Get event action by ID."""
    try:
        action = await event_service.get_action(str(action_id))
        
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event action with ID {action_id} not found"
            )
        
        return EventActionResponse.from_entity(action)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event action: {str(e)}"
        )


@router.put("/{action_id}", response_model=EventActionResponse)
async def update_event_action(
    action_id: UUID,
    request: EventActionUpdateRequest,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> EventActionResponse:
    """Update an event action."""
    try:
        action = await event_service.update_action(str(action_id), request)
        
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event action with ID {action_id} not found"
            )
        
        return EventActionResponse.from_entity(action)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update event action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event action: {str(e)}"
        )


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_action(
    action_id: UUID,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> None:
    """Delete an event action."""
    try:
        success = await event_service.delete_action(str(action_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event action with ID {action_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete event action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event action: {str(e)}"
        )


@router.post("/{action_id}/test", response_model=ActionTestResponse)
async def test_event_action(
    action_id: UUID,
    request: ActionTestRequest,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> ActionTestResponse:
    """Test an event action against simulated event data."""
    try:
        test_result = await event_service.test_action(str(action_id), request)
        
        if not test_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event action with ID {action_id} not found"
            )
        
        return test_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test event action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test event action: {str(e)}"
        )


@router.get("/{action_id}/executions", response_model=ActionExecutionListResponse)
async def get_action_executions(
    action_id: UUID,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> ActionExecutionListResponse:
    """Get execution history for an event action."""
    try:
        executions, total = await event_service.get_action_executions(
            str(action_id), skip=skip, limit=limit, status=status
        )
        
        # Convert skip/limit to page/size for response model
        page = (skip // limit) + 1 if limit > 0 else 1
        size = limit
        
        return ActionExecutionListResponse(
            executions=executions,  # These would be converted to response models
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"Failed to get action executions for {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get action executions: {str(e)}"
        )


@router.post("/{action_id}/enable", response_model=EventActionResponse)
async def enable_event_action(
    action_id: UUID,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> EventActionResponse:
    """Enable an event action."""
    try:
        # Update to enable the action
        from ..models import EventActionUpdateRequest
        request = EventActionUpdateRequest(is_enabled=True)
        
        action = await event_service.update_action(str(action_id), request)
        
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event action with ID {action_id} not found"
            )
        
        return EventActionResponse.from_entity(action)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable event action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable event action: {str(e)}"
        )


@router.post("/{action_id}/disable", response_model=EventActionResponse)
async def disable_event_action(
    action_id: UUID,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> EventActionResponse:
    """Disable an event action."""
    try:
        # Update to disable the action
        from ..models import EventActionUpdateRequest
        request = EventActionUpdateRequest(is_enabled=False)
        
        action = await event_service.update_action(str(action_id), request)
        
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event action with ID {action_id} not found"
            )
        
        return EventActionResponse.from_entity(action)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable event action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable event action: {str(e)}"
        )


@router.get("/stats/overview", response_model=ActionStatsResponse)
async def get_action_stats(
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> ActionStatsResponse:
    """Get overall statistics for event actions."""
    try:
        return await event_service.get_action_stats()
        
    except Exception as e:
        logger.error(f"Failed to get action stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get action stats: {str(e)}"
        )


@router.get("/{action_id}/stats", response_model=ActionStatsResponse)
async def get_action_specific_stats(
    action_id: UUID,
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
) -> ActionStatsResponse:
    """Get statistics for a specific event action."""
    try:
        return await event_service.get_action_stats(str(action_id))
        
    except Exception as e:
        logger.error(f"Failed to get stats for action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get action stats: {str(e)}"
        )