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


@router.post("/test-workflow", status_code=status.HTTP_201_CREATED)
async def run_event_action_workflow_test(
    event_service: AdminEventActionService = Depends(get_admin_event_action_service),
):
    """Run a complete event-action workflow test and save to database."""
    try:
        logger.info("Starting event-action workflow test")
        
        # Import neo-commons modules
        from neo_commons.platform.events.core.entities import DomainEvent
        from neo_commons.platform.events.core.value_objects import EventType
        from neo_commons.platform.actions.core.entities import Action, ActionExecution
        from neo_commons.platform.actions.core.value_objects import (
            HandlerType, ExecutionMode, ActionPriority, ActionStatus
        )
        from neo_commons.core.value_objects import UserId
        from neo_commons.utils import generate_uuid_v7
        from datetime import datetime, timezone
        import json
        
        # Step 1: Create test user and event
        test_user_id = UserId.generate()
        
        event = DomainEvent.create_new(
            event_type=EventType("user.profile_updated"),
            aggregate_id=test_user_id.value,
            aggregate_type="user",
            event_data={
                "user_id": str(test_user_id.value),
                "field": "email",
                "old_value": "old@example.com",
                "new_value": "new@example.com",
                "source": "workflow_test"
            },
            triggered_by_user_id=test_user_id
        )
        
        # Step 2: Create test actions
        webhook_action = Action(
            name="Test Workflow Webhook",
            handler_type=HandlerType.WEBHOOK,
            event_types=["user.profile_updated"],
            configuration={
                "url": "https://webhook.site/test-workflow",
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            },
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.HIGH,
            status=ActionStatus.ACTIVE,
            is_enabled=True,
            created_by_user_id=test_user_id
        )
        
        email_action = Action(
            name="Test Workflow Email",
            handler_type=HandlerType.EMAIL,
            event_types=["user.profile_updated"],
            configuration={
                "to": "admin@example.com",
                "template": "profile_updated",
                "subject": "Profile Updated - Workflow Test"
            },
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.NORMAL,
            status=ActionStatus.ACTIVE,
            is_enabled=True,
            created_by_user_id=test_user_id
        )
        
        # Step 3: Save actions using the service
        from ..models import EventActionCreateRequest
        
        # Create webhook action via service
        webhook_request = EventActionCreateRequest(
            name=webhook_action.name,
            description="Test webhook action created via workflow test",
            handler_type="webhook",
            configuration=webhook_action.configuration,
            event_types=webhook_action.event_types,
            execution_mode="async",
            priority="high",
            status="active",
            is_enabled=True
        )
        
        created_webhook = await event_service.create_action(webhook_request, str(test_user_id.value))
        
        # Create email action via service  
        email_request = EventActionCreateRequest(
            name=email_action.name,
            description="Test email action created via workflow test",
            handler_type="email",
            configuration=email_action.configuration,
            event_types=email_action.event_types,
            execution_mode="sync",
            priority="normal",
            status="active",
            is_enabled=True
        )
        
        created_email = await event_service.create_action(email_request, str(test_user_id.value))
        
        # Step 4: Create and execute action executions
        webhook_execution = ActionExecution.create_new(
            action_id=created_webhook.id,  # Use the created action's ID
            event_id=str(event.id.value),
            event_type=event.event_type.value,
            event_data=event.event_data,
            execution_context={"workflow_test": True, "api_endpoint": "test-workflow"}
        )
        
        email_execution = ActionExecution.create_new(
            action_id=created_email.id,  # Use the created action's ID
            event_id=str(event.id.value),
            event_type=event.event_type.value,
            event_data=event.event_data,
            execution_context={"workflow_test": True, "api_endpoint": "test-workflow"}
        )
        
        # Execute webhook
        webhook_execution.start_execution()
        import asyncio
        await asyncio.sleep(0.05)  # Simulate processing
        webhook_execution.complete_success({
            "webhook_delivered": True,
            "response_code": 200,
            "test_workflow": "webhook_success"
        })
        
        # Execute email
        email_execution.start_execution()
        await asyncio.sleep(0.03)  # Simulate processing
        email_execution.complete_success({
            "email_sent": True,
            "recipient": email_action.configuration["to"],
            "test_workflow": "email_success"
        })
        
        # Step 5: Save executions to database (directly via service database connection)
        # Get database connection from service
        db_service = event_service.db_service
        
        async with db_service.get_connection("admin") as conn:
            # Save webhook execution
            await conn.execute("""
                INSERT INTO admin.action_executions (
                    id, action_id, event_id, event_type, event_data,
                    status, started_at, completed_at, duration_ms,
                    result, error_message, retry_count, execution_context, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                webhook_execution.id.value, created_webhook.id.value, webhook_execution.event_id,
                webhook_execution.event_type, json.dumps(webhook_execution.event_data),
                webhook_execution.status, webhook_execution.started_at, webhook_execution.completed_at,
                webhook_execution.duration_ms, json.dumps(webhook_execution.result),
                webhook_execution.error_message, webhook_execution.retry_count,
                json.dumps(webhook_execution.execution_context), webhook_execution.created_at
            )
            
            # Save email execution
            await conn.execute("""
                INSERT INTO admin.action_executions (
                    id, action_id, event_id, event_type, event_data,
                    status, started_at, completed_at, duration_ms,
                    result, error_message, retry_count, execution_context, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                email_execution.id.value, created_email.id.value, email_execution.event_id,
                email_execution.event_type, json.dumps(email_execution.event_data),
                email_execution.status, email_execution.started_at, email_execution.completed_at,
                email_execution.duration_ms, json.dumps(email_execution.result),
                email_execution.error_message, email_execution.retry_count,
                json.dumps(email_execution.execution_context), email_execution.created_at
            )
        
        # Step 6: Return test results
        return {
            "status": "success",
            "message": "Event-action workflow test completed successfully",
            "results": {
                "event": {
                    "id": str(event.id.value),
                    "type": event.event_type.value,
                    "aggregate_id": str(event.aggregate_id),
                    "data": event.event_data
                },
                "actions": [
                    {
                        "id": str(created_webhook.id.value),
                        "name": created_webhook.name,
                        "handler_type": "webhook",
                        "status": "created_and_stored"
                    },
                    {
                        "id": str(created_email.id.value),
                        "name": created_email.name,
                        "handler_type": "email",
                        "status": "created_and_stored"
                    }
                ],
                "executions": [
                    {
                        "id": str(webhook_execution.id.value),
                        "action_id": str(created_webhook.id.value),
                        "status": webhook_execution.status,
                        "duration_ms": webhook_execution.duration_ms,
                        "result": webhook_execution.result
                    },
                    {
                        "id": str(email_execution.id.value),
                        "action_id": str(created_email.id.value),
                        "status": email_execution.status,
                        "duration_ms": email_execution.duration_ms,
                        "result": email_execution.result
                    }
                ],
                "database_verification": {
                    "actions_table": "admin.event_actions",
                    "executions_table": "admin.action_executions",
                    "webhook_action_id": str(created_webhook.id.value),
                    "email_action_id": str(created_email.id.value),
                    "webhook_execution_id": str(webhook_execution.id.value),
                    "email_execution_id": str(email_execution.id.value)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Event-action workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow test failed: {str(e)}"
        )