"""Tests for EventAction entity and related components."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from neo_commons.core.value_objects import ActionId, UserId
from neo_commons.features.events.entities.event_action import (
    EventAction, ActionStatus, HandlerType, ActionPriority, ExecutionMode,
    ActionCondition, ActionExecution
)


class TestActionCondition:
    """Tests for ActionCondition class."""
    
    def test_condition_creation(self):
        """Test creating an action condition."""
        condition = ActionCondition("data.user.id", "equals", "123")
        
        assert condition.field == "data.user.id"
        assert condition.operator == "equals"
        assert condition.value == "123"
    
    def test_condition_equals_operator(self):
        """Test equals operator evaluation."""
        condition = ActionCondition("user_id", "equals", "123")
        event_data = {"user_id": "123"}
        
        assert condition.evaluate(event_data) is True
        
        event_data = {"user_id": "456"}
        assert condition.evaluate(event_data) is False
    
    def test_condition_contains_operator(self):
        """Test contains operator evaluation."""
        condition = ActionCondition("email", "contains", "@company.com")
        
        assert condition.evaluate({"email": "user@company.com"}) is True
        assert condition.evaluate({"email": "user@other.com"}) is False
        assert condition.evaluate({"email": None}) is False
    
    def test_condition_comparison_operators(self):
        """Test gt/lt operators."""
        gt_condition = ActionCondition("age", "gt", 18)
        assert gt_condition.evaluate({"age": 25}) is True
        assert gt_condition.evaluate({"age": 15}) is False
        
        lt_condition = ActionCondition("score", "lt", 100)
        assert lt_condition.evaluate({"score": 85}) is True
        assert lt_condition.evaluate({"score": 120}) is False
    
    def test_condition_in_operators(self):
        """Test in/not_in operators."""
        in_condition = ActionCondition("status", "in", ["active", "pending"])
        assert in_condition.evaluate({"status": "active"}) is True
        assert in_condition.evaluate({"status": "inactive"}) is False
        
        not_in_condition = ActionCondition("status", "not_in", ["banned", "deleted"])
        assert not_in_condition.evaluate({"status": "active"}) is True
        assert not_in_condition.evaluate({"status": "banned"}) is False
    
    def test_condition_exists_operators(self):
        """Test exists/not_exists operators."""
        exists_condition = ActionCondition("optional_field", "exists", True)
        assert exists_condition.evaluate({"optional_field": "value"}) is True
        assert exists_condition.evaluate({}) is False
        
        not_exists_condition = ActionCondition("removed_field", "not_exists", True)
        assert not_exists_condition.evaluate({}) is True
        assert not_exists_condition.evaluate({"removed_field": "value"}) is False
    
    def test_condition_nested_field_access(self):
        """Test accessing nested fields with dot notation."""
        condition = ActionCondition("data.user.profile.name", "equals", "John")
        
        event_data = {
            "data": {
                "user": {
                    "profile": {
                        "name": "John"
                    }
                }
            }
        }
        
        assert condition.evaluate(event_data) is True
        
        # Test missing nested field
        event_data = {"data": {"user": {}}}
        assert condition.evaluate(event_data) is False
    
    def test_condition_unknown_operator(self):
        """Test handling unknown operators."""
        condition = ActionCondition("field", "unknown_op", "value")
        
        with pytest.raises(ValueError, match="Unknown operator: unknown_op"):
            condition.evaluate({"field": "value"})
    
    def test_condition_to_dict(self):
        """Test converting condition to dictionary."""
        condition = ActionCondition("field", "equals", "value")
        expected = {"field": "field", "operator": "equals", "value": "value"}
        
        assert condition.to_dict() == expected
    
    def test_condition_from_dict(self):
        """Test creating condition from dictionary."""
        data = {"field": "field", "operator": "equals", "value": "value"}
        condition = ActionCondition.from_dict(data)
        
        assert condition.field == "field"
        assert condition.operator == "equals"
        assert condition.value == "value"


class TestEventAction:
    """Tests for EventAction entity."""
    
    def test_event_action_creation(self):
        """Test creating a valid event action."""
        action = EventAction(
            id=ActionId.generate(),
            name="Test Action",
            description="Test action description",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"],
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.NORMAL,
            created_by_user_id=UserId.generate()
        )
        
        assert action.name == "Test Action"
        assert action.description == "Test action description"
        assert action.handler_type == HandlerType.WEBHOOK
        assert action.event_types == ["user.created"]
        assert action.execution_mode == ExecutionMode.ASYNC
        assert action.priority == ActionPriority.NORMAL
        assert action.status == ActionStatus.ACTIVE
        assert action.is_enabled is True
        assert action.trigger_count == 0
        assert action.success_count == 0
        assert action.failure_count == 0
    
    def test_event_action_validation_empty_name(self):
        """Test validation fails for empty name."""
        with pytest.raises(ValueError, match="Action name cannot be empty"):
            EventAction(
                id=ActionId.generate(),
                name="",
                handler_type=HandlerType.WEBHOOK,
                configuration={"url": "https://example.com/webhook"},
                event_types=["user.created"]
            )
    
    def test_event_action_validation_no_event_types(self):
        """Test validation fails for no event types."""
        with pytest.raises(ValueError, match="At least one event type must be specified"):
            EventAction(
                id=ActionId.generate(),
                name="Test Action",
                handler_type=HandlerType.WEBHOOK,
                configuration={"url": "https://example.com/webhook"},
                event_types=[]
            )
    
    def test_event_action_validation_invalid_event_type(self):
        """Test validation fails for invalid event type format."""
        with pytest.raises(ValueError, match="Invalid event type format"):
            EventAction(
                id=ActionId.generate(),
                name="Test Action", 
                handler_type=HandlerType.WEBHOOK,
                configuration={"url": "https://example.com/webhook"},
                event_types=["invalid_event_type"]  # Missing dot
            )
    
    def test_webhook_handler_validation(self):
        """Test webhook handler configuration validation."""
        # Valid webhook configuration
        action = EventAction(
            id=ActionId.generate(),
            name="Test Webhook",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"]
        )
        assert action.configuration["url"] == "https://example.com/webhook"
        
        # Invalid webhook configuration - missing URL
        with pytest.raises(ValueError, match="Webhook handler requires 'url' in configuration"):
            EventAction(
                id=ActionId.generate(),
                name="Test Webhook",
                handler_type=HandlerType.WEBHOOK,
                configuration={},
                event_types=["user.created"]
            )
    
    def test_email_handler_validation(self):
        """Test email handler configuration validation."""
        # Valid email configuration
        action = EventAction(
            id=ActionId.generate(),
            name="Test Email",
            handler_type=HandlerType.EMAIL,
            configuration={
                "to": "user@example.com",
                "template": "welcome_email"
            },
            event_types=["user.created"]
        )
        assert action.configuration["to"] == "user@example.com"
        
        # Invalid email configuration - missing 'to'
        with pytest.raises(ValueError, match="Email handler requires 'to' address"):
            EventAction(
                id=ActionId.generate(),
                name="Test Email",
                handler_type=HandlerType.EMAIL,
                configuration={"template": "welcome_email"},
                event_types=["user.created"]
            )
    
    def test_function_handler_validation(self):
        """Test function handler configuration validation."""
        # Valid function configuration
        action = EventAction(
            id=ActionId.generate(),
            name="Test Function",
            handler_type=HandlerType.FUNCTION,
            configuration={
                "module": "my_module.handlers",
                "function": "process_user_created"
            },
            event_types=["user.created"]
        )
        assert action.configuration["module"] == "my_module.handlers"
        
        # Invalid function configuration - missing function name
        with pytest.raises(ValueError, match="Function handler requires 'function' name"):
            EventAction(
                id=ActionId.generate(),
                name="Test Function",
                handler_type=HandlerType.FUNCTION,
                configuration={"module": "my_module.handlers"},
                event_types=["user.created"]
            )
    
    def test_event_type_matching(self):
        """Test event type matching logic."""
        action = EventAction(
            id=ActionId.generate(),
            name="Test Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created", "user.updated"]
        )
        
        # Exact matches
        assert action._matches_event_type("user.created") is True
        assert action._matches_event_type("user.updated") is True
        assert action._matches_event_type("user.deleted") is False
        
        # Wildcard matching
        wildcard_action = EventAction(
            id=ActionId.generate(),
            name="Wildcard Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.*"]
        )
        
        assert wildcard_action._matches_event_type("user.created") is True
        assert wildcard_action._matches_event_type("user.updated") is True
        assert wildcard_action._matches_event_type("user.profile.changed") is True
        assert wildcard_action._matches_event_type("order.created") is False
        
        # Universal wildcard
        universal_action = EventAction(
            id=ActionId.generate(),
            name="Universal Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["*"]
        )
        
        assert universal_action._matches_event_type("user.created") is True
        assert universal_action._matches_event_type("order.updated") is True
    
    def test_context_filters_matching(self):
        """Test context filters matching."""
        action = EventAction(
            id=ActionId.generate(),
            name="Filtered Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"],
            context_filters={"tenant_id": "tenant_123"}
        )
        
        # Matching context
        event_data = {"tenant_id": "tenant_123", "user_id": "user_456"}
        assert action._matches_context_filters(event_data) is True
        
        # Non-matching context
        event_data = {"tenant_id": "tenant_456", "user_id": "user_456"}
        assert action._matches_context_filters(event_data) is False
        
        # Missing context field
        event_data = {"user_id": "user_456"}
        assert action._matches_context_filters(event_data) is False
        
        # List-based filter
        action.context_filters = {"status": ["active", "pending"]}
        
        assert action._matches_context_filters({"status": "active"}) is True
        assert action._matches_context_filters({"status": "inactive"}) is False
    
    def test_conditions_matching(self):
        """Test condition matching."""
        condition = ActionCondition("data.user.email", "contains", "@company.com")
        
        action = EventAction(
            id=ActionId.generate(),
            name="Conditional Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"],
            conditions=[condition]
        )
        
        # Matching condition
        event_data = {"data": {"user": {"email": "john@company.com"}}}
        assert action._matches_conditions(event_data) is True
        
        # Non-matching condition
        event_data = {"data": {"user": {"email": "john@other.com"}}}
        assert action._matches_conditions(event_data) is False
    
    def test_matches_event_comprehensive(self):
        """Test comprehensive event matching."""
        condition = ActionCondition("data.user.active", "equals", True)
        
        action = EventAction(
            id=ActionId.generate(),
            name="Comprehensive Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.*"],
            conditions=[condition],
            context_filters={"tenant_id": "tenant_123"}
        )
        
        # All criteria match
        event_data = {
            "tenant_id": "tenant_123",
            "data": {"user": {"active": True}}
        }
        assert action.matches_event("user.created", event_data) is True
        
        # Event type doesn't match
        assert action.matches_event("order.created", event_data) is False
        
        # Context filter doesn't match
        event_data["tenant_id"] = "tenant_456"
        assert action.matches_event("user.created", event_data) is False
        
        # Condition doesn't match
        event_data["tenant_id"] = "tenant_123"
        event_data["data"]["user"]["active"] = False
        assert action.matches_event("user.created", event_data) is False
        
        # Action disabled
        event_data["data"]["user"]["active"] = True
        action.is_enabled = False
        assert action.matches_event("user.created", event_data) is False
        
        # Action paused
        action.is_enabled = True
        action.status = ActionStatus.PAUSED
        assert action.matches_event("user.created", event_data) is False
    
    def test_trigger_stats_update(self):
        """Test trigger statistics update."""
        action = EventAction(
            id=ActionId.generate(),
            name="Stats Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"]
        )
        
        # Initial state
        assert action.trigger_count == 0
        assert action.success_count == 0
        assert action.failure_count == 0
        assert action.success_rate == 0.0
        assert action.last_triggered_at is None
        
        # Successful execution
        action.update_trigger_stats(success=True)
        assert action.trigger_count == 1
        assert action.success_count == 1
        assert action.failure_count == 0
        assert action.success_rate == 100.0
        assert action.last_triggered_at is not None
        
        # Failed execution
        action.update_trigger_stats(success=False)
        assert action.trigger_count == 2
        assert action.success_count == 1
        assert action.failure_count == 1
        assert action.success_rate == 50.0
    
    def test_action_lifecycle_methods(self):
        """Test action lifecycle methods."""
        action = EventAction(
            id=ActionId.generate(),
            name="Lifecycle Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"]
        )
        
        # Initial state
        assert action.status == ActionStatus.ACTIVE
        assert action.is_enabled is True
        
        # Pause
        action.pause()
        assert action.status == ActionStatus.PAUSED
        
        # Resume
        action.resume()
        assert action.status == ActionStatus.ACTIVE
        
        # Disable
        action.disable()
        assert action.is_enabled is False
        
        # Enable
        action.enable()
        assert action.is_enabled is True
        
        # Archive
        action.archive()
        assert action.status == ActionStatus.ARCHIVED
        assert action.is_enabled is False
    
    def test_configuration_update(self):
        """Test configuration update."""
        action = EventAction(
            id=ActionId.generate(),
            name="Config Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook", "timeout": 30},
            event_types=["user.created"]
        )
        
        original_updated_at = action.updated_at
        
        # Update configuration
        new_config = {"timeout": 60, "retries": 3}
        action.update_configuration(new_config)
        
        assert action.configuration["url"] == "https://example.com/webhook"  # Preserved
        assert action.configuration["timeout"] == 60  # Updated
        assert action.configuration["retries"] == 3  # Added
        assert action.updated_at > original_updated_at
    
    def test_condition_management(self):
        """Test adding and removing conditions."""
        action = EventAction(
            id=ActionId.generate(),
            name="Condition Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"]
        )
        
        assert len(action.conditions) == 0
        
        # Add condition
        condition1 = ActionCondition("field1", "equals", "value1")
        action.add_condition(condition1)
        assert len(action.conditions) == 1
        
        condition2 = ActionCondition("field2", "gt", 10)
        action.add_condition(condition2)
        assert len(action.conditions) == 2
        
        # Remove condition
        removed = action.remove_condition("field1", "equals")
        assert removed is True
        assert len(action.conditions) == 1
        
        # Try to remove non-existent condition
        removed = action.remove_condition("field3", "equals")
        assert removed is False
        assert len(action.conditions) == 1
    
    def test_to_dict_serialization(self):
        """Test converting action to dictionary."""
        user_id = UserId.generate()
        action = EventAction(
            id=ActionId.generate(),
            name="Serialization Action",
            description="Test serialization",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://example.com/webhook"},
            event_types=["user.created"],
            created_by_user_id=user_id,
            tenant_id="tenant_123"
        )
        
        result = action.to_dict()
        
        assert result["name"] == "Serialization Action"
        assert result["description"] == "Test serialization"
        assert result["handler_type"] == "webhook"
        assert result["configuration"]["url"] == "https://example.com/webhook"
        assert result["event_types"] == ["user.created"]
        assert result["created_by_user_id"] == str(user_id.value)
        assert result["tenant_id"] == "tenant_123"
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result