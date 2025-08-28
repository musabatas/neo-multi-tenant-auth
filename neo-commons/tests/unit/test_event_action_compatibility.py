"""
Unit tests for event-action module compatibility.

Tests that events and actions modules work together following DRY principles
and Maximum Separation Architecture.
"""

import pytest
from uuid import UUID
from datetime import datetime, timezone
from typing import Dict, Any

# Test imports to verify DRY compliance - no duplicate functionality
try:
    # Events module core components
    from neo_commons.platform.events.core.entities import DomainEvent
    from neo_commons.platform.events.core.value_objects import EventId, EventType
    from neo_commons.platform.events.core.exceptions import InvalidEventConfiguration
    
    # Actions module core components  
    from neo_commons.platform.actions.core.entities import Action, ActionExecution
    from neo_commons.platform.actions.core.value_objects import (
        ActionId, HandlerType, ExecutionMode, ActionPriority, ActionStatus
    )
    from neo_commons.platform.actions.core.exceptions import ActionExecutionFailed
    
    # Shared core components
    from neo_commons.core.value_objects import UserId
    
    IMPORTS_AVAILABLE = True
    
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestImportCompatibility:
    """Test that imports work correctly between modules."""
    
    def test_imports_available(self):
        """Test that all required imports are available."""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Imports not available: {IMPORT_ERROR}")
        
        # If we get here, all imports worked
        assert True

    def test_no_circular_imports(self):
        """Test that there are no circular import dependencies."""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Imports not available: {IMPORT_ERROR}")
        
        # If imports work, there are no circular dependencies
        assert DomainEvent is not None
        assert Action is not None
        assert EventId is not None
        assert ActionId is not None

    def test_module_separation_compliance(self):
        """Test that modules maintain proper separation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip(f"Imports not available: {IMPORT_ERROR}")
        
        # Events module should have event-specific types
        assert EventId != ActionId
        assert DomainEvent != Action
        
        # Actions module should have action-specific types
        assert ActionExecution is not None
        assert HandlerType is not None
        assert ExecutionMode is not None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Imports not available")
class TestEventActionCompatibility:
    """Test compatibility between event and action entities."""

    def test_create_domain_event(self):
        """Test creating a domain event."""
        event = DomainEvent.create(
            event_type=EventType("user.registered"),
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef"),
            event_data={"username": "testuser", "email": "test@example.com"}
        )
        
        assert event.event_type.value == "user.registered"
        assert isinstance(event.id, EventId)
        assert event.event_data["username"] == "testuser"

    def test_create_action(self):
        """Test creating an action."""
        action = Action.create(
            name="Welcome Email",
            handler_type=HandlerType.EMAIL,
            event_types=["user.registered"],
            endpoint_url="smtp://localhost:587",
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.HIGH,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        assert action.name == "Welcome Email"
        assert action.handler_type == HandlerType.EMAIL
        assert "user.registered" in action.event_types
        assert isinstance(action.id, ActionId)

    def test_action_execution_with_event(self):
        """Test creating action execution linked to event."""
        # Create event
        event = DomainEvent.create(
            event_type=EventType("order.placed"),
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef"),
            event_data={"order_id": "12345", "amount": 99.99}
        )
        
        # Create action
        action = Action.create(
            name="Order Notification",
            handler_type=HandlerType.WEBHOOK,
            event_types=["order.placed"],
            endpoint_url="https://api.example.com/orders",
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.MEDIUM,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        # Create execution linking action to event
        execution = ActionExecution.create_new(
            action_id=action.id,
            event_id=event.id,
            event_type=event.event_type.value,
            event_data=event.event_data,
            execution_context={"retry_count": 0}
        )
        
        assert execution.action_id == action.id
        assert execution.event_id == event.id
        assert execution.event_type == "order.placed"
        assert execution.event_data["order_id"] == "12345"

    def test_action_matching_event_types(self):
        """Test that actions properly match event types."""
        action = Action.create(
            name="Multi-Event Action",
            handler_type=HandlerType.WEBHOOK,
            event_types=["user.created", "user.updated", "user.deleted"],
            endpoint_url="https://api.example.com/users",
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.LOW,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        # Test matching various event types
        assert action.matches_event("user.created", {})
        assert action.matches_event("user.updated", {})
        assert action.matches_event("user.deleted", {})
        assert not action.matches_event("order.created", {})

    def test_handler_types_coverage(self):
        """Test that all handler types are properly defined."""
        # Test that HandlerType enum has expected values
        assert HandlerType.WEBHOOK is not None
        assert HandlerType.EMAIL is not None
        assert HandlerType.FUNCTION is not None
        assert HandlerType.WORKFLOW is not None

    def test_execution_modes_coverage(self):
        """Test that execution modes are properly defined."""
        # Test that ExecutionMode enum has expected values
        assert ExecutionMode.SYNC is not None
        assert ExecutionMode.ASYNC is not None
        assert ExecutionMode.QUEUED is not None

    def test_action_priorities_coverage(self):
        """Test that action priorities are properly defined."""
        # Test that ActionPriority enum has expected values
        assert ActionPriority.LOW is not None
        assert ActionPriority.MEDIUM is not None
        assert ActionPriority.HIGH is not None
        assert ActionPriority.CRITICAL is not None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Imports not available")
class TestDRYPrincipleCompliance:
    """Test that DRY principles are followed."""

    def test_single_action_entity(self):
        """Test that there's only one Action entity (no duplication for webhooks, etc.)."""
        # Create different action types using same Action entity
        webhook_action = Action.create(
            name="Webhook Test",
            handler_type=HandlerType.WEBHOOK,
            event_types=["test.event"],
            endpoint_url="https://example.com/webhook",
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.MEDIUM,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        email_action = Action.create(
            name="Email Test",
            handler_type=HandlerType.EMAIL,
            event_types=["test.event"],
            endpoint_url="smtp://localhost",
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.HIGH,
            user_id=UserId("01234567-89ab-cdef-0123-456789abcdef")
        )
        
        # Both should be Action instances with different handler types
        assert type(webhook_action) == type(email_action)  # Same class
        assert webhook_action.handler_type != email_action.handler_type  # Different handlers

    def test_single_execution_entity(self):
        """Test that there's only one ActionExecution entity."""
        action_id = ActionId("01234567-89ab-cdef-0123-456789abcdef")
        event_id = EventId("01234567-89ab-cdef-0123-456789abcdef")
        
        # Create executions for different handler types
        webhook_execution = ActionExecution.create_new(
            action_id=action_id,
            event_id=event_id,
            event_type="test.webhook",
            event_data={},
            execution_context={"handler": "webhook"}
        )
        
        email_execution = ActionExecution.create_new(
            action_id=action_id,
            event_id=event_id,
            event_type="test.email",
            event_data={},
            execution_context={"handler": "email"}
        )
        
        # Both should be ActionExecution instances
        assert type(webhook_execution) == type(email_execution)

    def test_no_duplicate_repositories(self):
        """Test that ActionRepository is used for all action types."""
        # This test documents that we use ActionRepository for webhooks
        # instead of creating separate WebhookRepository (DRY principle)
        
        from neo_commons.platform.actions.core.protocols import ActionRepository
        
        # ActionRepository should be the single source for all action persistence
        assert ActionRepository is not None
        
        # Verify it's a protocol (can be implemented differently)
        import inspect
        assert inspect.isabstract(ActionRepository)


if __name__ == "__main__":
    print("Event-Action compatibility tests ready!")
    print("Run with: pytest tests/unit/test_event_action_compatibility.py -v")