"""Create action command."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...domain.entities.action import Action
from ...domain.value_objects.action_id import ActionId
from ...domain.value_objects.action_type import ActionType
from ..protocols.action_repository import ActionRepositoryProtocol
from ....utils import generate_uuid_v7


@dataclass
class CreateActionRequest:
    """Request to create a new action."""
    
    name: str
    action_type: str
    handler_class: str
    config: Dict[str, Any]
    event_patterns: List[str]
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool = True
    priority: str = "normal"
    timeout_seconds: int = 300
    retry_policy: Optional[Dict[str, Any]] = None
    max_concurrent_executions: int = 1
    rate_limit_per_minute: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    owner_team: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateActionCommand:
    """Command to create a new action."""
    
    def __init__(self, action_repository: ActionRepositoryProtocol):
        self.action_repository = action_repository
    
    async def execute(self, request: CreateActionRequest, schema: str) -> Action:
        """
        Create a new action.
        
        Args:
            request: Action creation request
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Created action entity
            
        Raises:
            ValueError: If action name already exists or validation fails
        """
        # Check if action with same name already exists
        existing_action = await self.action_repository.get_by_name(request.name, schema)
        if existing_action:
            raise ValueError(f"Action with name '{request.name}' already exists")
        
        # Set default retry policy if not provided
        retry_policy = request.retry_policy or {
            "max_retries": 3,
            "backoff_type": "exponential", 
            "initial_delay_ms": 1000
        }
        
        # Create action entity
        now = datetime.now()
        action = Action(
            id=ActionId(generate_uuid_v7()),
            name=request.name,
            action_type=ActionType(request.action_type),
            handler_class=request.handler_class,
            config=request.config,
            event_patterns=request.event_patterns,
            conditions=request.conditions or {},
            is_active=request.is_active,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            retry_policy=retry_policy,
            max_concurrent_executions=request.max_concurrent_executions,
            rate_limit_per_minute=request.rate_limit_per_minute,
            is_healthy=True,
            last_health_check_at=now,
            health_check_error=None,
            total_executions=0,
            successful_executions=0,
            failed_executions=0,
            avg_execution_time_ms=0,
            description=request.description,
            tags=request.tags or [],
            owner_team=request.owner_team,
            metadata=request.metadata or {},
            created_at=now,
            updated_at=now,
            deleted_at=None
        )
        
        # Save to repository
        return await self.action_repository.save(action, schema)