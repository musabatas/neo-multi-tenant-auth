"""Service layer for event action management in NeoAdminApi."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from neo_commons.core.value_objects import ActionId, UserId
from neo_commons.features.events.entities.event_action import (
    EventAction, ActionStatus, HandlerType, ActionPriority, ExecutionMode, ActionCondition
)
from neo_commons.features.events.services.event_action_registry import EventActionRegistry
from neo_commons.features.events.services.action_execution_service import ActionExecutionService
from neo_commons.features.events.repositories.action_execution_repository import ActionExecutionRepository

from .models import (
    EventActionCreateRequest, EventActionUpdateRequest, ActionTestRequest, 
    ActionTestResponse, ActionStatsResponse
)


class AdminEventActionService:
    """Admin service for managing event actions through the API."""
    
    def __init__(
        self,
        action_registry: EventActionRegistry,
        execution_service: ActionExecutionService,
        execution_repository: ActionExecutionRepository
    ):
        """Initialize admin service.
        
        Args:
            action_registry: Event action registry service
            execution_service: Action execution service  
            execution_repository: Execution repository for stats
        """
        self._action_registry = action_registry
        self._execution_service = execution_service
        self._execution_repository = execution_repository
    
    async def list_actions(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        handler_type: Optional[str] = None,
        event_type: Optional[str] = None,
        search: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> tuple[List[EventAction], int]:
        """List actions with filtering and pagination.
        
        Args:
            skip: Number of items to skip
            limit: Number of items to return
            status: Filter by status
            handler_type: Filter by handler type
            event_type: Filter by event type
            search: Search in name/description
            tenant_id: Filter by tenant ID
            
        Returns:
            Tuple of (actions list, total count)
        """
        # Convert string filters to enum values if provided
        status_filter = None
        if status:
            try:
                status_filter = ActionStatus(status)
            except ValueError:
                pass
        
        handler_type_filter = None
        if handler_type:
            try:
                handler_type_filter = HandlerType(handler_type)
            except ValueError:
                pass
        
        # Use the registry's filtering capabilities
        # Note: The registry might need to be extended to support all these filters
        actions = await self._action_registry.get_all_actions()
        
        # Apply filters manually for now (could be optimized with database filters)
        filtered_actions = []
        for action in actions:
            # Status filter
            if status_filter and action.status != status_filter:
                continue
            
            # Handler type filter
            if handler_type_filter and action.handler_type != handler_type_filter:
                continue
            
            # Event type filter
            if event_type and event_type not in action.event_types:
                # Also check for wildcard matches
                matches = False
                for configured_type in action.event_types:
                    if configured_type == "*" or configured_type.endswith(".*"):
                        if configured_type == "*" or event_type.startswith(configured_type[:-2] + "."):
                            matches = True
                            break
                if not matches:
                    continue
            
            # Search filter
            if search:
                search_lower = search.lower()
                if (search_lower not in action.name.lower() and 
                    (not action.description or search_lower not in action.description.lower())):
                    continue
            
            # Tenant filter
            if tenant_id and action.tenant_id != tenant_id:
                continue
            
            filtered_actions.append(action)
        
        # Apply pagination
        total = len(filtered_actions)
        paginated_actions = filtered_actions[skip:skip + limit]
        
        return paginated_actions, total
    
    async def get_action(self, action_id: str) -> Optional[EventAction]:
        """Get action by ID.
        
        Args:
            action_id: Action ID
            
        Returns:
            EventAction if found, None otherwise
        """
        return await self._action_registry.get_action(ActionId(action_id))
    
    async def create_action(
        self, 
        request: EventActionCreateRequest, 
        created_by_user_id: Optional[str] = None
    ) -> EventAction:
        """Create a new event action.
        
        Args:
            request: Action creation request
            created_by_user_id: ID of user creating the action
            
        Returns:
            Created EventAction
        """
        # Convert request to entity
        action = EventAction(
            id=ActionId.generate(),
            name=request.name,
            description=request.description,
            handler_type=request.handler_type,
            configuration=request.configuration,
            event_types=request.event_types,
            conditions=[condition.to_entity() for condition in request.conditions],
            context_filters=request.context_filters,
            execution_mode=request.execution_mode,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            max_retries=request.max_retries,
            retry_delay_seconds=request.retry_delay_seconds,
            is_enabled=request.is_enabled,
            tags=request.tags,
            created_by_user_id=UserId(created_by_user_id) if created_by_user_id else None,
            tenant_id=request.tenant_id
        )
        
        # Save via registry
        return await self._action_registry.register_action(action)
    
    async def update_action(
        self, 
        action_id: str, 
        request: EventActionUpdateRequest
    ) -> Optional[EventAction]:
        """Update an existing event action.
        
        Args:
            action_id: Action ID to update
            request: Update request with new values
            
        Returns:
            Updated EventAction if found, None otherwise
        """
        # Get existing action
        existing_action = await self._action_registry.get_action(ActionId(action_id))
        if not existing_action:
            return None
        
        # Update fields that are provided in request
        if request.name is not None:
            existing_action.name = request.name
        
        if request.description is not None:
            existing_action.description = request.description
        
        if request.configuration is not None:
            existing_action.update_configuration(request.configuration)
        
        if request.event_types is not None:
            existing_action.event_types = request.event_types
        
        if request.conditions is not None:
            existing_action.conditions = [condition.to_entity() for condition in request.conditions]
        
        if request.context_filters is not None:
            existing_action.context_filters = request.context_filters
        
        if request.execution_mode is not None:
            existing_action.execution_mode = request.execution_mode
        
        if request.priority is not None:
            existing_action.priority = request.priority
        
        if request.timeout_seconds is not None:
            existing_action.timeout_seconds = request.timeout_seconds
        
        if request.max_retries is not None:
            existing_action.max_retries = request.max_retries
        
        if request.retry_delay_seconds is not None:
            existing_action.retry_delay_seconds = request.retry_delay_seconds
        
        if request.status is not None:
            existing_action.status = request.status
        
        if request.is_enabled is not None:
            if request.is_enabled:
                existing_action.enable()
            else:
                existing_action.disable()
        
        if request.tags is not None:
            existing_action.tags = request.tags
        
        # Save updated action
        return await self._action_registry.update_action(existing_action)
    
    async def delete_action(self, action_id: str) -> bool:
        """Delete an event action.
        
        Args:
            action_id: Action ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        return await self._action_registry.unregister_action(ActionId(action_id))
    
    async def test_action(
        self, 
        action_id: str, 
        request: ActionTestRequest
    ) -> Optional[ActionTestResponse]:
        """Test an action against simulated event data.
        
        Args:
            action_id: Action ID to test
            request: Test request with event data
            
        Returns:
            Test response if action found, None otherwise
        """
        action = await self._action_registry.get_action(ActionId(action_id))
        if not action:
            return None
        
        # Evaluate if action would match
        event_data = {
            "event_type": request.event_type,
            "data": request.event_data,
            **request.event_data  # Include top-level event data for backward compatibility
        }
        
        matched = action.matches_event(request.event_type, event_data)
        
        # Evaluate individual conditions for detailed feedback
        conditions_evaluated = []
        for condition in action.conditions:
            try:
                result = condition.evaluate(event_data)
                conditions_evaluated.append({
                    "field": condition.field,
                    "operator": condition.operator,
                    "value": condition.value,
                    "result": result,
                    "error": None
                })
            except Exception as e:
                conditions_evaluated.append({
                    "field": condition.field,
                    "operator": condition.operator,
                    "value": condition.value,
                    "result": False,
                    "error": str(e)
                })
        
        # Determine reason for match/no-match
        if not action.is_enabled:
            reason = "Action is disabled"
        elif action.status != ActionStatus.ACTIVE:
            reason = f"Action status is {action.status.value}"
        elif not action._matches_event_type(request.event_type):
            reason = f"Event type '{request.event_type}' does not match configured types: {action.event_types}"
        elif not action._matches_context_filters(event_data):
            reason = "Context filters do not match"
        elif not action._matches_conditions(event_data):
            reason = "One or more conditions failed"
        elif matched:
            reason = "All conditions match"
        else:
            reason = "Unknown reason"
        
        return ActionTestResponse(
            matched=matched,
            reason=reason,
            conditions_evaluated=conditions_evaluated,
            would_execute=matched and not request.dry_run,
            dry_run=request.dry_run
        )
    
    async def get_action_executions(
        self,
        action_id: str,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> tuple[List, int]:
        """Get executions for an action.
        
        Args:
            action_id: Action ID
            skip: Number of items to skip
            limit: Number of items to return
            status: Filter by execution status
            
        Returns:
            Tuple of (executions list, total count)
        """
        # This would require implementing pagination in the execution repository
        # For now, return empty results
        return [], 0
    
    async def get_action_stats(self, action_id: Optional[str] = None) -> ActionStatsResponse:
        """Get statistics for actions.
        
        Args:
            action_id: Specific action ID, or None for global stats
            
        Returns:
            Statistics response
        """
        if action_id:
            # Stats for specific action
            action = await self._action_registry.get_action(ActionId(action_id))
            if not action:
                return ActionStatsResponse(
                    total_actions=0,
                    active_actions=0,
                    enabled_actions=0,
                    total_executions=0,
                    successful_executions=0,
                    failed_executions=0,
                    overall_success_rate=0.0,
                    by_handler_type={},
                    by_status={}
                )
            
            return ActionStatsResponse(
                total_actions=1,
                active_actions=1 if action.status == ActionStatus.ACTIVE else 0,
                enabled_actions=1 if action.is_enabled else 0,
                total_executions=action.trigger_count,
                successful_executions=action.success_count,
                failed_executions=action.failure_count,
                overall_success_rate=action.success_rate,
                by_handler_type={action.handler_type.value: 1},
                by_status={action.status.value: 1}
            )
        else:
            # Global stats
            all_actions = await self._action_registry.get_all_actions()
            
            total_actions = len(all_actions)
            active_actions = sum(1 for a in all_actions if a.status == ActionStatus.ACTIVE)
            enabled_actions = sum(1 for a in all_actions if a.is_enabled)
            
            total_executions = sum(a.trigger_count for a in all_actions)
            successful_executions = sum(a.success_count for a in all_actions)
            failed_executions = sum(a.failure_count for a in all_actions)
            
            overall_success_rate = (
                (successful_executions / total_executions * 100) 
                if total_executions > 0 else 0.0
            )
            
            # Group by handler type
            by_handler_type = {}
            for action in all_actions:
                handler_type = action.handler_type.value
                by_handler_type[handler_type] = by_handler_type.get(handler_type, 0) + 1
            
            # Group by status
            by_status = {}
            for action in all_actions:
                status = action.status.value
                by_status[status] = by_status.get(status, 0) + 1
            
            return ActionStatsResponse(
                total_actions=total_actions,
                active_actions=active_actions,
                enabled_actions=enabled_actions,
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                overall_success_rate=overall_success_rate,
                by_handler_type=by_handler_type,
                by_status=by_status
            )