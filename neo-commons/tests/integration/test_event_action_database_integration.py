"""
Real database integration tests for event-action workflows.

This test file uses the NeoAdminApi database service with real database connections
configured via .env file. Tests event-action workflows end-to-end with PostgreSQL.
"""

import os
import asyncio
import pytest
import sys
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock

# Add paths for imports
sys.path.insert(0, '/Users/musabatas/Workspaces/NeoMultiTenant/NeoAdminApi/src')
sys.path.insert(0, '/Users/musabatas/Workspaces/NeoMultiTenant/neo-commons/src')

# Database service from NeoAdminApi
from common.dependencies import get_database_service

# Event-Action entities from neo-commons
from neo_commons.platform.events.core.entities import DomainEvent
from neo_commons.platform.events.core.value_objects import EventId, EventType
from neo_commons.platform.actions.core.entities import Action, ActionExecution
from neo_commons.platform.actions.core.value_objects import (
    ActionId, HandlerType, ExecutionMode, ActionPriority, ActionStatus,
    ActionCondition
)
from neo_commons.core.value_objects import UserId
from neo_commons.utils import generate_uuid_v7

# Action Repository Protocol from actions module
from neo_commons.platform.actions.core.protocols import ActionRepository


class DatabaseActionRepository:
    """Real database implementation of ActionRepository using NeoAdminApi database service."""
    
    def __init__(self, db_service):
        self.db_service = db_service
        self.schema_name = "admin"  # Using admin schema for testing
    
    async def save_action(self, action: Action) -> None:
        """Save an action to the database."""
        query = f"""
            INSERT INTO {self.schema_name}.event_actions (
                id, name, description, handler_type, configuration,
                event_types, execution_mode, priority, status, is_enabled,
                created_by_user_id, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                configuration = EXCLUDED.configuration,
                updated_at = EXCLUDED.updated_at
        """
        
        async with self.db_service.get_connection(self.schema_name) as conn:
            await conn.execute(
                query,
                action.id.value,
                action.name,
                action.description,
                action.handler_type.value,
                action.configuration,
                action.event_types,
                action.execution_mode.value,
                action.priority.value,
                action.status.value,
                action.is_enabled,
                action.created_by_user_id.value if action.created_by_user_id else None,
                action.created_at,
                action.updated_at
            )
    
    async def get_action(self, action_id: ActionId) -> Optional[Action]:
        """Get action by ID from database."""
        query = f"""
            SELECT id, name, description, handler_type, configuration,
                   event_types, execution_mode, priority, status, is_enabled,
                   created_by_user_id, created_at, updated_at
            FROM {self.schema_name}.event_actions
            WHERE id = $1
        """
        
        async with self.db_service.get_connection(self.schema_name) as conn:
            row = await conn.fetchrow(query, action_id.value)
            
            if not row:
                return None
            
            # Convert database row back to Action entity
            action = Action(
                id=ActionId(row['id']),
                name=row['name'],
                description=row['description'],
                handler_type=HandlerType(row['handler_type']),
                configuration=row['configuration'] or {},
                event_types=row['event_types'] or [],
                execution_mode=ExecutionMode(row['execution_mode']),
                priority=ActionPriority(row['priority']),
                status=ActionStatus(row['status']),
                is_enabled=row['is_enabled'],
                created_by_user_id=UserId(row['created_by_user_id']) if row['created_by_user_id'] else None,
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
            return action
    
    async def find_actions_for_event(self, event_type: str) -> list[Action]:
        """Find actions that should trigger for an event type."""
        query = f"""
            SELECT id, name, description, handler_type, configuration,
                   event_types, execution_mode, priority, status, is_enabled,
                   created_by_user_id, created_at, updated_at
            FROM {self.schema_name}.event_actions
            WHERE is_enabled = true 
              AND status = 'active'
              AND $1 = ANY(event_types)
            ORDER BY priority DESC, created_at ASC
        """
        
        async with self.db_service.get_connection(self.schema_name) as conn:
            rows = await conn.fetch(query, event_type)
            
            actions = []
            for row in rows:
                action = Action(
                    id=ActionId(row['id']),
                    name=row['name'],
                    description=row['description'],
                    handler_type=HandlerType(row['handler_type']),
                    configuration=row['configuration'] or {},
                    event_types=row['event_types'] or [],
                    execution_mode=ExecutionMode(row['execution_mode']),
                    priority=ActionPriority(row['priority']),
                    status=ActionStatus(row['status']),
                    is_enabled=row['is_enabled'],
                    created_by_user_id=UserId(row['created_by_user_id']) if row['created_by_user_id'] else None,
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                # Double-check matching logic
                if action.matches_event(event_type, {}):
                    actions.append(action)
            
            return actions
    
    async def save_execution(self, execution: ActionExecution) -> None:
        """Save action execution to database."""
        query = f"""
            INSERT INTO {self.schema_name}.action_executions (
                id, action_id, event_id, event_type, event_data,
                execution_context, status, started_at, completed_at,
                error_message, result_data, retry_count
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            )
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                completed_at = EXCLUDED.completed_at,
                error_message = EXCLUDED.error_message,
                result_data = EXCLUDED.result_data,
                retry_count = EXCLUDED.retry_count
        """
        
        async with self.db_service.get_connection(self.schema_name) as conn:
            await conn.execute(
                query,
                execution.id.value,
                execution.action_id.value,
                execution.event_id.value,
                execution.event_type,
                execution.event_data,
                execution.execution_context,
                execution.status.value,
                execution.started_at,
                execution.completed_at,
                execution.error_message,
                execution.result_data,
                execution.retry_count
            )
    
    async def get_execution(self, execution_id: ActionId) -> Optional[ActionExecution]:
        """Get execution by ID from database."""
        query = f"""
            SELECT id, action_id, event_id, event_type, event_data,
                   execution_context, status, started_at, completed_at,
                   error_message, result_data, retry_count
            FROM {self.schema_name}.action_executions
            WHERE id = $1
        """
        
        async with self.db_service.get_connection(self.schema_name) as conn:
            row = await conn.fetchrow(query, execution_id.value)
            
            if not row:
                return None
            
            # Create execution object from database row
            execution = ActionExecution(
                id=ActionId(row['id']),
                action_id=ActionId(row['action_id']),
                event_id=EventId(row['event_id']),
                event_type=row['event_type'],
                event_data=row['event_data'] or {},
                execution_context=row['execution_context'] or {},
                status=ActionStatus(row['status']),
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                error_message=row['error_message'],
                result_data=row['result_data'],
                retry_count=row['retry_count'] or 0
            )
            
            return execution
    
    async def cleanup_test_data(self) -> None:
        """Clean up test data from database."""
        async with self.db_service.get_connection(self.schema_name) as conn:
            # Clean up test executions and actions
            await conn.execute(f"DELETE FROM {self.schema_name}.action_executions WHERE event_type LIKE 'test.%'")
            await conn.execute(f"DELETE FROM {self.schema_name}.event_actions WHERE name LIKE 'Test %'")


@pytest.fixture(scope="session")
async def database_service():
    """Get database service using NeoAdminApi configuration."""
    # Set environment variables from .env if not already set
    env_file = '/Users/musabatas/Workspaces/NeoMultiTenant/NeoAdminApi/.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes from value if present
                    value = value.strip('"\'')
                    if key not in os.environ:
                        os.environ[key] = value
    
    # Get database service
    db_service = await get_database_service()
    
    yield db_service
    
    # Cleanup would happen here if needed


@pytest.fixture
async def action_repository(database_service):
    """Create database action repository."""
    repo = DatabaseActionRepository(database_service)
    
    yield repo
    
    # Cleanup test data after each test
    await repo.cleanup_test_data()


@pytest.fixture
def test_user_id():
    """Generate test user ID using UUIDv7."""
    return UserId(generate_uuid_v7())


@pytest.fixture
def sample_event(test_user_id):
    """Create a sample domain event for testing."""
    return DomainEvent.create_new(
        event_type=EventType("test.user_registered"),
        aggregate_id=test_user_id.value,
        aggregate_type="user",
        event_data={
            "username": "test_user_db",
            "email": "test@example.com",
            "registration_method": "database_test"
        },
        triggered_by_user_id=test_user_id
    )


@pytest.fixture 
def webhook_action(test_user_id):
    """Create a webhook action for testing."""
    return Action(
        name="Test Webhook Action DB",
        description="Database integration test webhook",
        handler_type=HandlerType.WEBHOOK,
        event_types=["test.user_registered", "test.user_updated"],
        configuration={
            "url": "https://api.example.com/test-webhook",
            "headers": {"Content-Type": "application/json"},
            "timeout": 30
        },
        execution_mode=ExecutionMode.ASYNC,
        priority=ActionPriority.HIGH,
        status=ActionStatus.ACTIVE,
        is_enabled=True,
        created_by_user_id=test_user_id
    )


@pytest.fixture
def email_action(test_user_id):
    """Create an email action for testing."""
    return Action(
        name="Test Email Action DB",
        description="Database integration test email",
        handler_type=HandlerType.EMAIL,
        event_types=["test.user_registered"],
        configuration={
            "to": "admin@example.com",
            "template": "welcome_email",
            "subject": "Welcome to the Platform"
        },
        execution_mode=ExecutionMode.SYNC,
        priority=ActionPriority.NORMAL,
        status=ActionStatus.ACTIVE,
        is_enabled=True,
        created_by_user_id=test_user_id
    )


class TestDatabaseEventActionIntegration:
    """Test event-action workflows with real database integration."""

    async def test_database_connection_works(self, database_service):
        """Test that database connection is working."""
        # Test admin connection
        async with database_service.get_connection("admin") as conn:
            result = await conn.fetchval("SELECT 1 as test_value")
            assert result == 1
        
        # Test connection registry
        connections = await database_service.connection_registry.get_all_connections()
        assert len(connections) > 0
        
        admin_connection = None
        for conn in connections:
            if conn.connection_name == "admin":
                admin_connection = conn
                break
        
        assert admin_connection is not None
        assert admin_connection.is_healthy

    async def test_action_crud_operations(self, action_repository, webhook_action):
        """Test basic CRUD operations for actions in database."""
        # Save action
        await action_repository.save_action(webhook_action)
        
        # Retrieve action
        retrieved_action = await action_repository.get_action(webhook_action.id)
        
        assert retrieved_action is not None
        assert retrieved_action.id == webhook_action.id
        assert retrieved_action.name == webhook_action.name
        assert retrieved_action.handler_type == HandlerType.WEBHOOK
        assert retrieved_action.event_types == webhook_action.event_types
        assert retrieved_action.is_enabled == True

    async def test_find_actions_for_event(self, action_repository, webhook_action, email_action):
        """Test finding actions that match specific event types."""
        # Save both actions
        await action_repository.save_action(webhook_action)
        await action_repository.save_action(email_action)
        
        # Find actions for user_registered event
        matching_actions = await action_repository.find_actions_for_event("test.user_registered")
        
        # Both actions should match
        assert len(matching_actions) >= 2
        
        action_names = {action.name for action in matching_actions}
        assert "Test Webhook Action DB" in action_names
        assert "Test Email Action DB" in action_names
        
        # Test event that only webhook should match
        webhook_only_actions = await action_repository.find_actions_for_event("test.user_updated")
        assert len(webhook_only_actions) >= 1
        
        webhook_names = {action.name for action in webhook_only_actions}
        assert "Test Webhook Action DB" in webhook_names

    async def test_execution_crud_operations(self, action_repository, sample_event, webhook_action):
        """Test CRUD operations for action executions."""
        # Save the action first
        await action_repository.save_action(webhook_action)
        
        # Create execution
        execution = ActionExecution.create_new(
            action_id=webhook_action.id,
            event_id=sample_event.id,
            event_type=sample_event.event_type.value,
            event_data=sample_event.event_data,
            execution_context={"test_context": "database_integration"}
        )
        
        # Start execution
        execution.start_execution()
        
        # Save execution
        await action_repository.save_execution(execution)
        
        # Retrieve execution
        retrieved_execution = await action_repository.get_execution(execution.id)
        
        assert retrieved_execution is not None
        assert retrieved_execution.id == execution.id
        assert retrieved_execution.action_id == webhook_action.id
        assert retrieved_execution.event_id == sample_event.id
        assert retrieved_execution.event_type == "test.user_registered"
        assert retrieved_execution.status == ActionStatus.RUNNING
        
        # Complete execution
        execution.complete_success({"webhook_delivered": True, "response_code": 200})
        await action_repository.save_execution(execution)
        
        # Retrieve completed execution
        completed_execution = await action_repository.get_execution(execution.id)
        assert completed_execution.status == ActionStatus.SUCCEEDED
        assert completed_execution.result_data["webhook_delivered"] == True

    async def test_full_event_action_workflow(self, action_repository, sample_event, webhook_action, email_action):
        """Test complete event-action workflow with database persistence."""
        # Setup: Save actions
        await action_repository.save_action(webhook_action)
        await action_repository.save_action(email_action)
        
        # Step 1: Event occurs - find matching actions
        matching_actions = await action_repository.find_actions_for_event(
            sample_event.event_type.value
        )
        
        assert len(matching_actions) >= 2
        
        # Step 2: Execute actions and track executions
        executions = []
        for action in matching_actions:
            if action.name.startswith("Test"):  # Only our test actions
                # Create execution
                execution = ActionExecution.create_new(
                    action_id=action.id,
                    event_id=sample_event.id,
                    event_type=sample_event.event_type.value,
                    event_data=sample_event.event_data,
                    execution_context={
                        "workflow_test": True,
                        "handler_type": action.handler_type.value
                    }
                )
                
                # Start execution
                execution.start_execution()
                await action_repository.save_execution(execution)
                
                # Simulate execution completion
                if action.handler_type == HandlerType.WEBHOOK:
                    execution.complete_success({
                        "webhook_url": action.configuration["url"],
                        "response_code": 200,
                        "delivered_at": datetime.now(timezone.utc).isoformat()
                    })
                elif action.handler_type == HandlerType.EMAIL:
                    execution.complete_success({
                        "email_sent": True,
                        "recipient": action.configuration["to"],
                        "template": action.configuration["template"]
                    })
                
                await action_repository.save_execution(execution)
                executions.append(execution)
        
        # Step 3: Verify all executions completed successfully
        assert len(executions) >= 2
        
        for execution in executions:
            retrieved = await action_repository.get_execution(execution.id)
            assert retrieved.status == ActionStatus.SUCCEEDED
            assert retrieved.result_data is not None
            assert retrieved.completed_at is not None

    async def test_action_matching_logic_with_database(self, action_repository, test_user_id):
        """Test action matching logic with various event patterns."""
        # Create actions with different event type patterns
        wildcard_action = Action(
            name="Test Wildcard Action",
            handler_type=HandlerType.WEBHOOK,
            event_types=["test.*"],  # Should match all test.* events
            configuration={"url": "https://example.com/wildcard"},
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.NORMAL,
            created_by_user_id=test_user_id
        )
        
        specific_action = Action(
            name="Test Specific Action", 
            handler_type=HandlerType.EMAIL,
            event_types=["test.specific_event"],
            configuration={"to": "test@example.com", "template": "specific"},
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.HIGH,
            created_by_user_id=test_user_id
        )
        
        # Save actions
        await action_repository.save_action(wildcard_action)
        await action_repository.save_action(specific_action)
        
        # Test wildcard matching
        wildcard_matches = await action_repository.find_actions_for_event("test.any_event")
        wildcard_names = {action.name for action in wildcard_matches if action.name.startswith("Test")}
        assert "Test Wildcard Action" in wildcard_names
        
        # Test specific matching
        specific_matches = await action_repository.find_actions_for_event("test.specific_event")
        specific_names = {action.name for action in specific_matches if action.name.startswith("Test")}
        assert "Test Specific Action" in specific_names
        assert "Test Wildcard Action" in specific_names  # Wildcard should also match
        
        # Test non-matching event
        no_matches = await action_repository.find_actions_for_event("other.event")
        no_match_names = {action.name for action in no_matches if action.name.startswith("Test")}
        assert len(no_match_names) == 0

    async def test_dry_principle_compliance_in_database(self, action_repository, test_user_id):
        """Test DRY principle - single repository handles all action types."""
        # Create actions of different handler types
        webhook = Action(
            name="Test DRY Webhook",
            handler_type=HandlerType.WEBHOOK,
            event_types=["test.dry_check"],
            configuration={"url": "https://example.com/webhook"},
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.NORMAL,
            created_by_user_id=test_user_id
        )
        
        email = Action(
            name="Test DRY Email",
            handler_type=HandlerType.EMAIL,
            event_types=["test.dry_check"],
            configuration={"to": "test@example.com", "template": "dry_test"},
            execution_mode=ExecutionMode.SYNC,
            priority=ActionPriority.NORMAL,
            created_by_user_id=test_user_id
        )
        
        function = Action(
            name="Test DRY Function",
            handler_type=HandlerType.FUNCTION,
            event_types=["test.dry_check"],
            configuration={"module": "test_module", "function": "test_handler"},
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.NORMAL,
            created_by_user_id=test_user_id
        )
        
        # Save all action types using same repository
        await action_repository.save_action(webhook)
        await action_repository.save_action(email)
        await action_repository.save_action(function)
        
        # Retrieve all actions
        webhook_retrieved = await action_repository.get_action(webhook.id)
        email_retrieved = await action_repository.get_action(email.id)
        function_retrieved = await action_repository.get_action(function.id)
        
        # Verify all types saved and retrieved correctly
        assert webhook_retrieved.handler_type == HandlerType.WEBHOOK
        assert email_retrieved.handler_type == HandlerType.EMAIL
        assert function_retrieved.handler_type == HandlerType.FUNCTION
        
        # Verify they can all be found by event type
        all_actions = await action_repository.find_actions_for_event("test.dry_check")
        test_action_names = {action.name for action in all_actions if action.name.startswith("Test DRY")}
        
        assert "Test DRY Webhook" in test_action_names
        assert "Test DRY Email" in test_action_names
        assert "Test DRY Function" in test_action_names


async def run_database_tests():
    """Run database integration tests manually."""
    print("🔄 Running database integration tests...")
    
    try:
        # Set up environment
        env_file = '/Users/musabatas/Workspaces/NeoMultiTenant/NeoAdminApi/.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip('"\'')
                        if key not in os.environ:
                            os.environ[key] = value
        
        # Get database service
        print("📊 Connecting to database...")
        db_service = await get_database_service()
        
        # Test connection
        async with db_service.get_connection("admin") as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection failed")
                return False
        
        # Test repository operations
        print("🔧 Testing repository operations...")
        repo = DatabaseActionRepository(db_service)
        
        # Clean up any existing test data
        await repo.cleanup_test_data()
        
        # Create test data
        test_user_id = UserId(generate_uuid_v7())
        
        webhook_action = Action(
            name="Test Manual Webhook",
            handler_type=HandlerType.WEBHOOK,
            event_types=["test.manual_run"],
            configuration={"url": "https://api.example.com/manual-test"},
            execution_mode=ExecutionMode.ASYNC,
            priority=ActionPriority.HIGH,
            created_by_user_id=test_user_id
        )
        
        # Test save and retrieve
        await repo.save_action(webhook_action)
        retrieved = await repo.get_action(webhook_action.id)
        
        if retrieved and retrieved.name == "Test Manual Webhook":
            print("✅ Action save/retrieve test passed")
        else:
            print("❌ Action save/retrieve test failed")
            return False
        
        # Test event matching
        matching_actions = await repo.find_actions_for_event("test.manual_run")
        if len(matching_actions) > 0:
            print("✅ Action event matching test passed")
        else:
            print("❌ Action event matching test failed")
            return False
        
        # Clean up
        await repo.cleanup_test_data()
        print("✅ Cleanup completed")
        
        print("🎉 All database integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_database_tests())
    exit(0 if success else 1)