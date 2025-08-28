"""
Demonstrate actual database data storage.

This test stores data in the database and shows you the actual records
before cleaning up, so you can see the real database persistence.
"""

import os
import asyncio
import asyncpg
import json
from datetime import datetime, timezone

# Import platform modules
import sys
sys.path.insert(0, 'src')

from neo_commons.platform.actions.core.entities import Action, ActionExecution
from neo_commons.platform.actions.core.value_objects import (
    ActionId, HandlerType, ExecutionMode, ActionPriority, ActionStatus
)
from neo_commons.core.value_objects import UserId
from neo_commons.utils import generate_uuid_v7


async def show_database_data():
    """Store data and show actual database records."""
    # Get database connection
    env_file = '/Users/musabatas/Workspaces/NeoMultiTenant/NeoAdminApi/.env'
    db_url = None
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('ADMIN_DATABASE_URL='):
                    db_url = line.split('=', 1)[1].strip('"\'')
                    break
    
    conn = await asyncpg.connect(db_url)
    
    # Create test action
    test_user_id = UserId.generate()
    action = Action(
        name="Demo Action - Check Database",
        handler_type=HandlerType.WEBHOOK,
        event_types=["demo.test"],
        configuration={
            "url": "https://api.example.com/demo",
            "method": "POST",
            "headers": {"Content-Type": "application/json"}
        },
        execution_mode=ExecutionMode.ASYNC,
        priority=ActionPriority.HIGH,
        status=ActionStatus.ACTIVE,
        is_enabled=True,
        created_by_user_id=test_user_id
    )
    
    # Store in database
    await conn.execute("""
        INSERT INTO admin.event_actions (
            id, name, description, handler_type, configuration, event_types,
            conditions, context_filters, execution_mode, priority, 
            timeout_seconds, max_retries, retry_delay_seconds,
            status, is_enabled, tags, tenant_id, created_by_user_id,
            created_at, updated_at, trigger_count, success_count, failure_count
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23
        )
    """, 
        action.id.value, action.name, "Demo action for database verification",
        action.handler_type.value, json.dumps(action.configuration),
        json.dumps(action.event_types), json.dumps([]), json.dumps({}),
        action.execution_mode.value, action.priority.value,
        30, 3, 5, action.status.value, action.is_enabled,
        json.dumps({"demo": True}), None, action.created_by_user_id.value,
        action.created_at, action.created_at, 0, 0, 0
    )
    
    # Create test execution
    execution = ActionExecution.create_new(
        action_id=action.id,
        event_id=str(generate_uuid_v7()),
        event_type="demo.test",
        event_data={"message": "This is demo data in database"},
        execution_context={"demo": True, "visible_in_db": True}
    )
    
    execution.start_execution()
    await asyncio.sleep(0.01)
    execution.complete_success({
        "demo_result": "You can see this in the database!",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Store execution in database
    await conn.execute("""
        INSERT INTO admin.action_executions (
            id, action_id, event_id, event_type, event_data,
            status, started_at, completed_at, duration_ms,
            result, error_message, retry_count, execution_context, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
        )
    """,
        execution.id.value, execution.action_id.value, execution.event_id,
        execution.event_type, json.dumps(execution.event_data),
        execution.status, execution.started_at, execution.completed_at,
        execution.duration_ms, json.dumps(execution.result),
        execution.error_message, execution.retry_count,
        json.dumps(execution.execution_context), execution.created_at
    )
    
    print("🗄️ DATA STORED IN DATABASE - Check these tables:")
    print("=" * 60)
    
    # Show action in database
    print("📋 admin.event_actions:")
    action_data = await conn.fetchrow(
        "SELECT id, name, handler_type, configuration, event_types, status, is_enabled, created_at FROM admin.event_actions WHERE id = $1",
        action.id.value
    )
    print(f"  ID: {action_data['id']}")
    print(f"  Name: {action_data['name']}")
    print(f"  Handler: {action_data['handler_type']}")
    print(f"  Config: {action_data['configuration']}")
    print(f"  Events: {action_data['event_types']}")
    print(f"  Status: {action_data['status']}")
    print(f"  Enabled: {action_data['is_enabled']}")
    print(f"  Created: {action_data['created_at']}")
    
    print("\n⚡ admin.action_executions:")
    execution_data = await conn.fetchrow(
        "SELECT id, action_id, event_type, event_data, status, result, execution_context, created_at FROM admin.action_executions WHERE id = $1",
        execution.id.value
    )
    print(f"  ID: {execution_data['id']}")
    print(f"  Action ID: {execution_data['action_id']}")
    print(f"  Event Type: {execution_data['event_type']}")
    print(f"  Event Data: {execution_data['event_data']}")
    print(f"  Status: {execution_data['status']}")
    print(f"  Result: {execution_data['result']}")
    print(f"  Context: {execution_data['execution_context']}")
    print(f"  Created: {execution_data['created_at']}")
    
    print("\n" + "=" * 60)
    print("🔍 You can now check the database with:")
    print(f"  SELECT * FROM admin.event_actions WHERE id = '{action.id.value}';")
    print(f"  SELECT * FROM admin.action_executions WHERE id = '{execution.id.value}';")
    
    # Keep data for 10 seconds so you can check database
    print("\n⏳ Data will be kept for 10 seconds for you to check database...")
    print("   (Open another terminal and connect to check the tables)")
    await asyncio.sleep(10)
    
    # Clean up
    await conn.execute("DELETE FROM admin.action_executions WHERE id = $1", execution.id.value)
    await conn.execute("DELETE FROM admin.event_actions WHERE id = $1", action.id.value)
    
    print("🧹 Test data cleaned up")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(show_database_data())