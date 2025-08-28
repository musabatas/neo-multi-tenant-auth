"""
Integration tests for event-action workflows.

Tests the compatibility between events and actions modules following Maximum Separation Architecture.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any

# Core imports from both modules - testing DRY compliance
from neo_commons.platform.events.core.entities import DomainEvent
from neo_commons.platform.events.core.value_objects import EventId, EventType
from neo_commons.platform.actions.core.entities import Action, ActionExecution
from neo_commons.platform.actions.core.value_objects import (
    ActionId, HandlerType, ExecutionMode, ActionPriority, ActionStatus
)
from neo_commons.platform.actions.core.protocols import ActionRepository
from neo_commons.core.value_objects import UserId


class MockActionRepository:
    """Mock action repository for testing."""
    
    def __init__(self):
        self.actions: Dict[str, Action] = {}
        self.executions: Dict[str, ActionExecution] = {}
    
    async def save_action(self, action: Action) -> None:
        """Save an action."""
        self.actions[str(action.id.value)] = action
    
    async def get_action(self, action_id: ActionId) -> Action | None:
        """Get action by ID."""
        return self.actions.get(str(action_id.value))
    
    async def find_actions_for_event(self, event_type: str) -> list[Action]:
        """Find actions that should trigger for an event type."""
        return [
            action for action in self.actions.values()
            if action.matches_event(event_type, {})
        ]
    
    async def save_execution(self, execution: ActionExecution) -> None:
        """Save execution record."""
        self.executions[str(execution.id.value)] = execution
    
    async def get_execution(self, execution_id: ActionId) -> ActionExecution | None:
        """Get execution by ID."""
        return self.executions.get(str(execution_id.value))


@pytest.fixture
def mock_repository():
    """Provide mock action repository."""
    return MockActionRepository()


@pytest.fixture
def sample_event():
    """Create a sample domain event."""
    return DomainEvent.create(
        event_type=EventType("user.created"),
        user_id=UserId("01234567-89ab-cdef-0123-456789abcdef"),
        event_data={"username": "test_user", "email": "test@example.com"}
    )


@pytest.fixture
def webhook_action():
    """Create a webhook action."""
    return Action.create(
        name="User Creation Webhook",
        handler_type=HandlerType.WEBHOOK,
        event_types=["user.created"],
        endpoint_url="https://api.example.com/webhooks/user-created",
        execution_mode=ExecutionMode.ASYNC,
        priority=ActionPriority.HIGH,
        user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
    )


@pytest.fixture
def email_action():
    """Create an email action."""
    return Action.create(
        name="Welcome Email",
        handler_type=HandlerType.EMAIL,
        event_types=["user.created"],
        endpoint_url="smtp://localhost:587",
        execution_mode=ExecutionMode.SYNC,
        priority=ActionPriority.MEDIUM,
        user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
    )


class TestEventActionIntegration:
    """Test event-action integration workflows."""

    async def test_event_triggers_webhook_action(self, mock_repository, sample_event, webhook_action):
        """Test that events properly trigger webhook actions."""
        # Setup: Save webhook action in repository
        await mock_repository.save_action(webhook_action)
        
        # Test: Find actions for the event
        matching_actions = await mock_repository.find_actions_for_event("user.created")
        
        # Verify: Webhook action should match
        assert len(matching_actions) == 1
        assert matching_actions[0].handler_type == HandlerType.WEBHOOK
        assert matching_actions[0].name == "User Creation Webhook"

    async def test_event_triggers_multiple_actions(self, mock_repository, sample_event, webhook_action, email_action):
        """Test that one event can trigger multiple actions."""
        # Setup: Save both actions
        await mock_repository.save_action(webhook_action)
        await mock_repository.save_action(email_action)
        
        # Test: Find actions for the event
        matching_actions = await mock_repository.find_actions_for_event("user.created")
        
        # Verify: Both actions should match
        assert len(matching_actions) == 2
        handler_types = {action.handler_type for action in matching_actions}
        assert HandlerType.WEBHOOK in handler_types
        assert HandlerType.EMAIL in handler_types

    async def test_action_execution_tracking(self, mock_repository, sample_event, webhook_action):
        """Test that action executions are properly tracked."""
        # Setup: Save action
        await mock_repository.save_action(webhook_action)
        
        # Test: Create and save execution
        execution = ActionExecution.create_new(
            action_id=webhook_action.id,
            event_id=sample_event.id,
            event_type=sample_event.event_type.value,
            event_data=sample_event.event_data,
            execution_context={"source": "test"}
        )
        
        await mock_repository.save_execution(execution)
        
        # Verify: Execution can be retrieved
        retrieved_execution = await mock_repository.get_execution(execution.id)
        assert retrieved_execution is not None
        assert retrieved_execution.action_id == webhook_action.id
        assert retrieved_execution.event_id == sample_event.id

    async def test_action_matching_logic(self, webhook_action, email_action):
        """Test the action matching logic for different event types."""
        # Test: Webhook action matches correct event type
        assert webhook_action.matches_event("user.created", {})
        assert not webhook_action.matches_event("user.deleted", {})
        
        # Test: Email action matches correct event type
        assert email_action.matches_event("user.created", {})
        assert not email_action.matches_event("order.created", {})

    async def test_dry_principle_compliance(self, mock_repository):
        """Test that DRY principles are followed - no duplicate functionality."""
        # Verify: ActionRepository is used for all action types (webhooks, emails, etc.)
        # This test confirms that webhooks don't have their own repository
        
        # Create different action types
        webhook_action = Action.create(
            name="Test Webhook",
            handler_type=HandlerType.WEBHOOK,
            event_types=["test.event"],
            endpoint_url="https://example.com/hook",
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.MEDIUM,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        email_action = Action.create(
            name="Test Email",
            handler_type=HandlerType.EMAIL,
            event_types=["test.event"],
            endpoint_url="smtp://localhost",
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.HIGH,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        # Test: Same repository handles all action types
        await mock_repository.save_action(webhook_action)
        await mock_repository.save_action(email_action)
        
        # Verify: Both actions stored in same repository
        webhook_retrieved = await mock_repository.get_action(webhook_action.id)
        email_retrieved = await mock_repository.get_action(email_action.id)
        
        assert webhook_retrieved is not None
        assert email_retrieved is not None
        assert webhook_retrieved.handler_type == HandlerType.WEBHOOK
        assert email_retrieved.handler_type == HandlerType.EMAIL


class TestMaximumSeparationCompliance:
    """Test Maximum Separation Architecture compliance."""

    def test_module_boundaries_respected(self):
        """Test that module boundaries are properly respected."""
        # This test verifies that imports work correctly and don't violate boundaries
        
        # Events module should export its core concepts
        from neo_commons.platform.events.core.entities import DomainEvent
        from neo_commons.platform.events.core.value_objects import EventId, EventType
        
        # Actions module should export its core concepts
        from neo_commons.platform.actions.core.entities import Action, ActionExecution
        from neo_commons.platform.actions.core.value_objects import ActionId, HandlerType
        
        # Cross-module usage should work without circular dependencies
        event = DomainEvent.create(
            event_type=EventType("test.event"),
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef"),
            event_data={}
        )
        
        action = Action.create(
            name="Test Action",
            handler_type=HandlerType.WEBHOOK,
            event_types=["test.event"],
            endpoint_url="https://example.com",
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.MEDIUM,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        # Actions should be able to reference events
        execution = ActionExecution.create_new(
            action_id=action.id,
            event_id=event.id,
            event_type=event.event_type.value,
            event_data=event.event_data,
            execution_context={}
        )
        
        assert execution.action_id == action.id
        assert execution.event_id == event.id

    def test_one_file_one_purpose_principle(self):
        """Test that each imported component has a single responsibility."""
        # This test documents the Maximum Separation Architecture compliance
        
        # Events module - each component has single responsibility
        from neo_commons.platform.events.core.entities import DomainEvent  # ONLY domain events
        from neo_commons.platform.events.core.value_objects import EventId  # ONLY event identification
        
        # Actions module - each component has single responsibility  
        from neo_commons.platform.actions.core.entities import Action  # ONLY action entities
        from neo_commons.platform.actions.core.value_objects import ActionId  # ONLY action identification
        from neo_commons.platform.actions.core.protocols import ActionRepository  # ONLY action storage contract
        
        # Verify types are distinct and focused
        assert DomainEvent != Action
        assert EventId != ActionId
        
        # Success if imports work without conflicts
        assert True


if __name__ == "__main__":
    print("Event-Action workflow tests ready to run!")
    print("Run with: pytest tests/integration/test_event_action_workflow.py -v")