"""Integration tests for the dynamic event actions system."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from neo_commons.core.value_objects import ActionId, UserId
from neo_commons.features.events.entities.event_action import (
    EventAction, ActionStatus, HandlerType, ActionPriority, ExecutionMode, ActionCondition
)
from neo_commons.features.events.entities.domain_event import DomainEvent, EventType
from neo_commons.features.events.services.event_dispatcher_service import EventDispatcherService
from neo_commons.features.events.services.event_action_registry import EventActionRegistry
from neo_commons.features.events.services.action_execution_service import ActionExecutionService
from neo_commons.features.events.services.action_monitoring_service import ActionMonitoringService


class MockWebhookHandler:
    """Mock webhook handler for testing."""
    
    def __init__(self, should_succeed: bool = True, delay: float = 0.1):
        self.should_succeed = should_succeed
        self.delay = delay
        self.call_count = 0
        self.last_call_data = None
    
    async def handle(self, action: EventAction, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock webhook handling."""
        self.call_count += 1
        self.last_call_data = event_data
        
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if self.should_succeed:
            return {
                "success": True,
                "status_code": 200,
                "response_time_ms": int(self.delay * 1000)
            }
        else:
            raise Exception("Webhook call failed")


class MockEmailHandler:
    """Mock email handler for testing."""
    
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.sent_emails = []
    
    async def handle(self, action: EventAction, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock email sending."""
        if self.should_succeed:
            email_data = {
                "to": action.configuration.get("to"),
                "template": action.configuration.get("template"),
                "data": event_data,
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
            self.sent_emails.append(email_data)
            
            return {
                "success": True,
                "message_id": f"msg_{len(self.sent_emails)}",
                "recipient": action.configuration.get("to")
            }
        else:
            raise Exception("Email delivery failed")


class TestEventActionIntegration:
    """Integration tests for the complete event action system."""
    
    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db_service = AsyncMock()
        db_service.get_connection.return_value.__aenter__ = AsyncMock()
        db_service.get_connection.return_value.__aexit__ = AsyncMock()
        return db_service
    
    @pytest.fixture
    def mock_action_repository(self):
        """Mock action repository."""
        repo = AsyncMock()
        repo.save.return_value = None
        repo.find_by_id.return_value = None
        repo.find_all.return_value = []
        repo.find_by_event_type.return_value = []
        repo.update.return_value = None
        repo.delete.return_value = True
        return repo
    
    @pytest.fixture
    def mock_execution_repository(self):
        """Mock execution repository."""
        repo = AsyncMock()
        repo.save.return_value = None
        repo.find_by_id.return_value = None
        repo.find_by_action_id.return_value = []
        return repo
    
    @pytest.fixture
    def action_registry(self, mock_action_repository):
        """Create action registry with mock repository."""
        return EventActionRegistry(mock_action_repository)
    
    @pytest.fixture
    def monitoring_service(self, mock_execution_repository):
        """Create monitoring service."""
        from neo_commons.features.events.services.action_monitoring_service import ActionMonitoringConfig
        config = ActionMonitoringConfig(collect_metrics=True, log_executions=False)
        return ActionMonitoringService(mock_execution_repository, config)
    
    @pytest.fixture
    def execution_service(self, mock_execution_repository, monitoring_service):
        """Create execution service with monitoring."""
        from neo_commons.features.events.entities.action_handlers import HandlerRegistry
        
        handler_registry = HandlerRegistry()
        service = ActionExecutionService(
            execution_repository=mock_execution_repository,
            handler_registry=handler_registry,
            monitoring_config=monitoring_service._config
        )
        
        # Replace monitoring service
        service._monitoring_service = monitoring_service
        
        return service
    
    @pytest.fixture
    def event_dispatcher(self, action_registry, execution_service):
        """Create event dispatcher with action integration."""
        dispatcher = EventDispatcherService()
        dispatcher._action_registry = action_registry
        dispatcher._execution_service = execution_service
        return dispatcher
    
    @pytest.fixture
    def webhook_action(self):
        """Create webhook action for testing."""
        return EventAction(
            id=ActionId.generate(),
            name="User Registration Webhook",
            description="Send webhook when user registers",
            handler_type=HandlerType.WEBHOOK,
            configuration={
                "url": "https://api.example.com/webhooks/user-registered",
                "method": "POST",
                "headers": {"Authorization": "Bearer test-token"}
            },
            event_types=["user.created"],
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.NORMAL,
            is_enabled=True
        )
    
    @pytest.fixture
    def email_action(self):
        """Create email action for testing."""
        return EventAction(
            id=ActionId.generate(),
            name="Welcome Email",
            description="Send welcome email to new users",
            handler_type=HandlerType.EMAIL,
            configuration={
                "to": "{{user.email}}",
                "template": "welcome_email",
                "from": "noreply@example.com"
            },
            event_types=["user.created"],
            conditions=[
                ActionCondition("data.user.email_verified", "equals", True)
            ],
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.HIGH,
            is_enabled=True
        )
    
    @pytest.fixture
    def conditional_action(self):
        """Create action with complex conditions."""
        return EventAction(
            id=ActionId.generate(),
            name="Premium User Notification",
            description="Notify when premium users perform actions",
            handler_type=HandlerType.WEBHOOK,
            configuration={
                "url": "https://api.example.com/premium-notifications",
                "method": "POST"
            },
            event_types=["user.*"],  # Wildcard matching
            conditions=[
                ActionCondition("data.user.subscription", "equals", "premium"),
                ActionCondition("data.user.active", "equals", True)
            ],
            context_filters={"tenant_id": "premium_tenant"},
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.HIGH,
            is_enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_end_to_end_webhook_execution(
        self, 
        event_dispatcher, 
        action_registry, 
        webhook_action,
        mock_action_repository
    ):
        """Test complete end-to-end webhook execution flow."""
        # Setup
        mock_webhook_handler = MockWebhookHandler(should_succeed=True)
        mock_action_repository.find_by_event_type.return_value = [webhook_action]
        
        # Register mock handler
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock()
            mock_get_handler.return_value.can_handle.return_value = True
            mock_get_handler.return_value.handle = mock_webhook_handler.handle
            mock_get_handler.return_value.status.value = "registered"
            
            # Create and dispatch event
            event = DomainEvent(
                event_type=EventType("user.created"),
                aggregate_id="user_123",
                data={
                    "user": {
                        "id": "user_123",
                        "email": "test@example.com",
                        "name": "Test User"
                    }
                },
                metadata={"tenant_id": "tenant_123"}
            )
            
            # Dispatch event
            await event_dispatcher.dispatch(event)
            
            # Verify handler was called
            assert mock_webhook_handler.call_count == 1
            assert mock_webhook_handler.last_call_data["data"]["user"]["id"] == "user_123"
    
    @pytest.mark.asyncio
    async def test_multiple_actions_execution(
        self, 
        event_dispatcher, 
        webhook_action, 
        email_action,
        mock_action_repository
    ):
        """Test execution of multiple actions for single event."""
        # Setup multiple actions
        mock_action_repository.find_by_event_type.return_value = [webhook_action, email_action]
        
        mock_webhook_handler = MockWebhookHandler(should_succeed=True)
        mock_email_handler = MockEmailHandler(should_succeed=True)
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            def handler_side_effect(handler_type):
                if handler_type == "webhook":
                    handler = Mock()
                    handler.can_handle.return_value = True
                    handler.handle = mock_webhook_handler.handle
                    handler.status.value = "registered"
                    return handler
                elif handler_type == "email":
                    handler = Mock()
                    handler.can_handle.return_value = True
                    handler.handle = mock_email_handler.handle
                    handler.status.value = "registered"
                    return handler
                return None
            
            mock_get_handler.side_effect = handler_side_effect
            
            # Create event
            event = DomainEvent(
                event_type=EventType("user.created"),
                aggregate_id="user_456",
                data={
                    "user": {
                        "id": "user_456",
                        "email": "verified@example.com",
                        "name": "Verified User",
                        "email_verified": True
                    }
                }
            )
            
            # Dispatch event
            await event_dispatcher.dispatch(event)
            
            # Give async executions time to complete
            await asyncio.sleep(0.2)
            
            # Verify both handlers were called
            assert mock_webhook_handler.call_count == 1
            assert len(mock_email_handler.sent_emails) == 1
            assert mock_email_handler.sent_emails[0]["data"]["data"]["user"]["email_verified"] is True
    
    @pytest.mark.asyncio
    async def test_condition_filtering(
        self, 
        event_dispatcher, 
        conditional_action,
        mock_action_repository
    ):
        """Test that actions are properly filtered by conditions."""
        mock_action_repository.find_by_event_type.return_value = [conditional_action]
        mock_webhook_handler = MockWebhookHandler(should_succeed=True)
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock()
            mock_get_handler.return_value.can_handle.return_value = True
            mock_get_handler.return_value.handle = mock_webhook_handler.handle
            mock_get_handler.return_value.status.value = "registered"
            
            # Test 1: Event that should match all conditions
            matching_event = DomainEvent(
                event_type=EventType("user.updated"),
                aggregate_id="user_premium",
                data={
                    "user": {
                        "id": "user_premium",
                        "subscription": "premium",
                        "active": True
                    }
                },
                metadata={"tenant_id": "premium_tenant"}
            )
            
            await event_dispatcher.dispatch(matching_event)
            assert mock_webhook_handler.call_count == 1
            
            # Test 2: Event that doesn't match conditions (not premium)
            mock_webhook_handler.call_count = 0
            non_matching_event = DomainEvent(
                event_type=EventType("user.updated"),
                aggregate_id="user_basic",
                data={
                    "user": {
                        "id": "user_basic",
                        "subscription": "basic",  # Not premium
                        "active": True
                    }
                },
                metadata={"tenant_id": "premium_tenant"}
            )
            
            await event_dispatcher.dispatch(non_matching_event)
            assert mock_webhook_handler.call_count == 0
            
            # Test 3: Event that doesn't match context filter
            wrong_tenant_event = DomainEvent(
                event_type=EventType("user.updated"),
                aggregate_id="user_premium2",
                data={
                    "user": {
                        "id": "user_premium2",
                        "subscription": "premium",
                        "active": True
                    }
                },
                metadata={"tenant_id": "other_tenant"}  # Wrong tenant
            )
            
            await event_dispatcher.dispatch(wrong_tenant_event)
            assert mock_webhook_handler.call_count == 0
    
    @pytest.mark.asyncio
    async def test_action_failure_and_retry(
        self, 
        event_dispatcher, 
        webhook_action,
        mock_action_repository
    ):
        """Test action failure handling and retry logic."""
        # Configure action for retries
        webhook_action.max_retries = 2
        webhook_action.retry_delay_seconds = 0.1
        
        mock_action_repository.find_by_event_type.return_value = [webhook_action]
        
        # Handler that fails initially then succeeds
        call_count = 0
        async def failing_handler(action, event_data):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise Exception("Temporary failure")
            return {"success": True, "attempt": call_count}
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock()
            mock_get_handler.return_value.can_handle.return_value = True
            mock_get_handler.return_value.handle = failing_handler
            mock_get_handler.return_value.status.value = "registered"
            
            # Create event
            event = DomainEvent(
                event_type=EventType("user.created"),
                aggregate_id="user_retry",
                data={"user": {"id": "user_retry"}}
            )
            
            # Dispatch event and wait for retries
            await event_dispatcher.dispatch(event)
            await asyncio.sleep(0.5)  # Wait for retries
            
            # Should have been called 3 times (initial + 2 retries)
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(
        self, 
        event_dispatcher, 
        webhook_action, 
        monitoring_service,
        mock_action_repository
    ):
        """Test that monitoring captures execution metrics."""
        mock_action_repository.find_by_event_type.return_value = [webhook_action]
        
        # Mix of successful and failed handlers
        call_count = 0
        async def mixed_handler(action, event_data):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # Fail every other call
                raise Exception("Intermittent failure")
            return {"success": True}
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock()
            mock_get_handler.return_value.can_handle.return_value = True
            mock_get_handler.return_value.handle = mixed_handler
            mock_get_handler.return_value.status.value = "registered"
            
            # Dispatch multiple events
            for i in range(4):
                event = DomainEvent(
                    event_type=EventType("user.created"),
                    aggregate_id=f"user_{i}",
                    data={"user": {"id": f"user_{i}"}}
                )
                await event_dispatcher.dispatch(event)
            
            await asyncio.sleep(0.3)  # Wait for async executions
            
            # Check global metrics
            global_metrics = await monitoring_service.get_global_metrics()
            assert global_metrics.total_executions == 4
            assert global_metrics.successful_executions == 2
            assert global_metrics.failed_executions == 2
            assert global_metrics.success_rate_percent == 50.0
            
            # Check action-specific metrics
            action_id = str(webhook_action.id.value)
            action_metrics = await monitoring_service.get_action_metrics(action_id)
            assert action_metrics is not None
            assert action_metrics.total_executions == 4
            assert action_metrics.success_rate_percent == 50.0
    
    @pytest.mark.asyncio
    async def test_execution_mode_differences(
        self, 
        event_dispatcher, 
        mock_action_repository
    ):
        """Test different execution modes (sync vs async)."""
        # Create sync action
        sync_action = EventAction(
            id=ActionId.generate(),
            name="Sync Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://sync.example.com"},
            event_types=["test.sync"],
            execution_mode=ExecutionMode.SYNC,
            is_enabled=True
        )
        
        # Create async action
        async_action = EventAction(
            id=ActionId.generate(),
            name="Async Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://async.example.com"},
            event_types=["test.async"],
            execution_mode=ExecutionMode.ASYNC,
            is_enabled=True
        )
        
        sync_call_time = None
        async_call_time = None
        
        async def sync_handler(action, event_data):
            nonlocal sync_call_time
            await asyncio.sleep(0.1)  # Simulate work
            sync_call_time = datetime.now(timezone.utc)
            return {"success": True}
        
        async def async_handler(action, event_data):
            nonlocal async_call_time
            await asyncio.sleep(0.1)  # Simulate work
            async_call_time = datetime.now(timezone.utc)
            return {"success": True}
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            def handler_side_effect(handler_type):
                handler = Mock()
                handler.can_handle.return_value = True
                handler.status.value = "registered"
                if handler_type == "webhook":
                    # Return different handlers based on action context
                    handler.handle = sync_handler if sync_call_time is None else async_handler
                return handler
            
            mock_get_handler.side_effect = handler_side_effect
            
            # Setup mock repository responses
            def repo_side_effect(event_type):
                if event_type == "test.sync":
                    return [sync_action]
                elif event_type == "test.async":
                    return [async_action]
                return []
            
            mock_action_repository.find_by_event_type.side_effect = repo_side_effect
            
            # Dispatch sync event
            dispatch_start = datetime.now(timezone.utc)
            sync_event = DomainEvent(
                event_type=EventType("test.sync"),
                aggregate_id="test_sync",
                data={"test": True}
            )
            await event_dispatcher.dispatch(sync_event)
            sync_dispatch_end = datetime.now(timezone.utc)
            
            # For sync execution, handler should complete before dispatch returns
            assert sync_call_time is not None
            assert dispatch_start <= sync_call_time <= sync_dispatch_end
            
            # Dispatch async event
            async_event = DomainEvent(
                event_type=EventType("test.async"),
                aggregate_id="test_async", 
                data={"test": True}
            )
            await event_dispatcher.dispatch(async_event)
            async_dispatch_end = datetime.now(timezone.utc)
            
            # For async execution, handler might still be running
            # Wait a bit and check
            await asyncio.sleep(0.2)
            assert async_call_time is not None
    
    @pytest.mark.asyncio
    async def test_wildcard_event_matching(
        self, 
        event_dispatcher, 
        mock_action_repository
    ):
        """Test wildcard event type matching."""
        # Action with wildcard matching
        wildcard_action = EventAction(
            id=ActionId.generate(),
            name="User Wildcard Action",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://wildcard.example.com"},
            event_types=["user.*"],  # Matches any user event
            execution_mode=ExecutionMode.ASYNC,
            is_enabled=True
        )
        
        mock_action_repository.find_by_event_type.return_value = [wildcard_action]
        mock_handler = MockWebhookHandler(should_succeed=True)
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock()
            mock_get_handler.return_value.can_handle.return_value = True
            mock_get_handler.return_value.handle = mock_handler.handle
            mock_get_handler.return_value.status.value = "registered"
            
            # Test various user events
            test_events = [
                "user.created",
                "user.updated",
                "user.deleted",
                "user.profile.changed",
                "user.subscription.upgraded"
            ]
            
            for event_type in test_events:
                event = DomainEvent(
                    event_type=EventType(event_type),
                    aggregate_id=f"user_{event_type.split('.')[-1]}",
                    data={"user": {"id": "test_user"}}
                )
                await event_dispatcher.dispatch(event)
            
            await asyncio.sleep(0.3)  # Wait for async executions
            
            # All events should have triggered the action
            assert mock_handler.call_count == len(test_events)
    
    @pytest.mark.asyncio
    async def test_disabled_action_not_executed(
        self, 
        event_dispatcher, 
        webhook_action,
        mock_action_repository
    ):
        """Test that disabled actions are not executed."""
        webhook_action.is_enabled = False  # Disable action
        mock_action_repository.find_by_event_type.return_value = [webhook_action]
        
        mock_handler = MockWebhookHandler(should_succeed=True)
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock()
            mock_get_handler.return_value.can_handle.return_value = True
            mock_get_handler.return_value.handle = mock_handler.handle
            mock_get_handler.return_value.status.value = "registered"
            
            # Create and dispatch event
            event = DomainEvent(
                event_type=EventType("user.created"),
                aggregate_id="user_disabled_test",
                data={"user": {"id": "user_disabled_test"}}
            )
            
            await event_dispatcher.dispatch(event)
            await asyncio.sleep(0.2)
            
            # Handler should not be called
            assert mock_handler.call_count == 0
    
    @pytest.mark.asyncio
    async def test_priority_execution_order(
        self, 
        event_dispatcher, 
        mock_action_repository
    ):
        """Test that actions execute in priority order for sync actions."""
        # Create actions with different priorities
        high_priority_action = EventAction(
            id=ActionId.generate(),
            name="High Priority",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://high.example.com"},
            event_types=["test.priority"],
            execution_mode=ExecutionMode.SYNC,  # Sync to test ordering
            priority=ActionPriority.HIGH,
            is_enabled=True
        )
        
        normal_priority_action = EventAction(
            id=ActionId.generate(),
            name="Normal Priority",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://normal.example.com"},
            event_types=["test.priority"],
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.NORMAL,
            is_enabled=True
        )
        
        low_priority_action = EventAction(
            id=ActionId.generate(),
            name="Low Priority",
            handler_type=HandlerType.WEBHOOK,
            configuration={"url": "https://low.example.com"},
            event_types=["test.priority"],
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.LOW,
            is_enabled=True
        )
        
        # Return actions in random order
        mock_action_repository.find_by_event_type.return_value = [
            normal_priority_action, high_priority_action, low_priority_action
        ]
        
        execution_order = []
        
        async def track_execution(action, event_data):
            execution_order.append(action.name)
            return {"success": True}
        
        with patch.object(event_dispatcher._execution_service._handler_registry, 'get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock()
            mock_get_handler.return_value.can_handle.return_value = True
            mock_get_handler.return_value.handle = track_execution
            mock_get_handler.return_value.status.value = "registered"
            
            # Create and dispatch event
            event = DomainEvent(
                event_type=EventType("test.priority"),
                aggregate_id="priority_test",
                data={"test": True}
            )
            
            await event_dispatcher.dispatch(event)
            
            # Should execute in priority order: High -> Normal -> Low
            expected_order = ["High Priority", "Normal Priority", "Low Priority"]
            assert execution_order == expected_order