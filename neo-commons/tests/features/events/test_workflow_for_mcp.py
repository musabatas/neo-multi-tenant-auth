"""
Run event-action workflow and keep data for MCP verification.

This test runs the workflow and prints the IDs so we can verify 
the data using database MCP queries.
"""

import os
import asyncio
import asyncpg
import json
from datetime import datetime, timezone

# Import platform modules
import sys
sys.path.insert(0, 'src')

from neo_commons.platform.events.core.entities import DomainEvent
from neo_commons.platform.events.core.value_objects import EventType
from neo_commons.platform.actions.core.entities import Action, ActionExecution
from neo_commons.platform.actions.core.value_objects import (
    ActionId, HandlerType, ExecutionMode, ActionPriority, ActionStatus
)
from neo_commons.core.value_objects import UserId
from neo_commons.utils import generate_uuid_v7


async def run_workflow_keep_data():
    """Run event-action workflow and keep data for MCP verification."""
    print("🚀 Running event-action workflow and keeping data for MCP verification...")
    
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
    
    if not db_url:
        print("❌ Database URL not found")
        return
    
    conn = await asyncpg.connect(db_url)
    
    # Step 1: Create Domain Event
    print("📝 Creating domain event...")
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
            "source": "mcp_verification_test"
        },
        triggered_by_user_id=test_user_id
    )
    
    print(f"✅ Event created: {event.id.value}")
    print(f"   Type: {event.event_type.value}")
    
    # Step 2: Create Actions
    print("⚙️ Creating actions...")
    
    # Webhook action
    webhook_action = Action(
        name="MCP Verification Webhook",
        handler_type=HandlerType.WEBHOOK,
        event_types=["user.profile_updated"],
        configuration={
            "url": "https://webhook.site/mcp-verification",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer mcp-test-token",
                "Content-Type": "application/json"
            }
        },
        execution_mode=ExecutionMode.ASYNC,
        priority=ActionPriority.HIGH,
        status=ActionStatus.ACTIVE,
        is_enabled=True,
        created_by_user_id=test_user_id
    )
    
    # Email action
    email_action = Action(
        name="MCP Verification Email",
        handler_type=HandlerType.EMAIL,
        event_types=["user.profile_updated"],
        configuration={
            "to": "admin@example.com",
            "template": "mcp_verification",
            "subject": "Profile Updated - MCP Test"
        },
        execution_mode=ExecutionMode.SYNC,
        priority=ActionPriority.NORMAL,
        status=ActionStatus.ACTIVE,
        is_enabled=True,
        created_by_user_id=test_user_id
    )
    
    print(f"✅ Webhook action: {webhook_action.id.value}")
    print(f"✅ Email action: {email_action.id.value}")
    
    # Step 3: Save actions to database
    print("💾 Saving actions to database...")
    
    for action in [webhook_action, email_action]:
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
            action.id.value, action.name, f"Action for {action.handler_type.value} handling - MCP test",
            action.handler_type.value, json.dumps(action.configuration),
            json.dumps(action.event_types), json.dumps([]), json.dumps({}),
            action.execution_mode.value, action.priority.value,
            30, 3, 5, action.status.value, action.is_enabled,
            json.dumps({"mcp_verification": True}), None, action.created_by_user_id.value,
            action.created_at, action.created_at, 0, 0, 0
        )
    
    print("✅ Actions saved to admin.event_actions")
    
    # Step 4: Execute event-action workflow
    print("⚡ Executing event-action workflow...")
    
    executions = []
    for action in [webhook_action, email_action]:
        # Create execution
        execution = ActionExecution.create_new(
            action_id=action.id,
            event_id=str(event.id.value),
            event_type=event.event_type.value,
            event_data=event.event_data,
            execution_context={
                "workflow": "mcp_verification",
                "triggered_at": datetime.now(timezone.utc).isoformat(),
                "source": "mcp_test"
            }
        )
        
        # Start execution
        execution.start_execution()
        await asyncio.sleep(0.05)  # Simulate processing time
        
        # Complete with results based on handler type
        if action.handler_type == HandlerType.WEBHOOK:
            execution.complete_success({
                "webhook_delivered": True,
                "response_code": 200,
                "response_body": {"status": "received", "mcp_test": True},
                "delivery_time_ms": 245
            })
        else:  # EMAIL
            execution.complete_success({
                "email_sent": True,
                "recipient": action.configuration["to"],
                "message_id": f"mcp_test_{generate_uuid_v7()}",
                "send_time_ms": 156
            })
        
        executions.append(execution)
        print(f"   ✅ {action.handler_type.value} execution: {execution.status}")
    
    # Step 5: Save executions to database
    print("💾 Saving executions to database...")
    
    for execution in executions:
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
    
    print("✅ Executions saved to admin.action_executions")
    
    await conn.close()
    
    # Step 6: Print verification info for MCP
    print("\n🔍 DATA SAVED FOR MCP VERIFICATION:")
    print("=" * 60)
    print(f"📋 Webhook Action ID: {webhook_action.id.value}")
    print(f"📋 Email Action ID:   {email_action.id.value}")
    print(f"⚡ Webhook Execution: {executions[0].id.value}")
    print(f"⚡ Email Execution:   {executions[1].id.value}")
    print(f"📝 Event ID:          {event.id.value}")
    print("=" * 60)
    
    return {
        "webhook_action_id": str(webhook_action.id.value),
        "email_action_id": str(email_action.id.value),
        "webhook_execution_id": str(executions[0].id.value),
        "email_execution_id": str(executions[1].id.value),
        "event_id": str(event.id.value),
        "test_timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    result = asyncio.run(run_workflow_keep_data())
    
    print(f"\n🎯 MCP VERIFICATION QUERIES:")
    print(f"-- Check webhook action:")
    print(f"SELECT * FROM admin.event_actions WHERE id = '{result['webhook_action_id']}';")
    print(f"\n-- Check email action:")
    print(f"SELECT * FROM admin.event_actions WHERE id = '{result['email_action_id']}';")
    print(f"\n-- Check webhook execution:")
    print(f"SELECT * FROM admin.action_executions WHERE id = '{result['webhook_execution_id']}';")
    print(f"\n-- Check email execution:")
    print(f"SELECT * FROM admin.action_executions WHERE id = '{result['email_execution_id']}';")
    print(f"\n-- Summary query:")
    print(f"SELECT ea.name, ea.handler_type, ae.status, ae.result FROM admin.event_actions ea JOIN admin.action_executions ae ON ea.id = ae.action_id WHERE ea.name LIKE '%MCP Verification%';")
    
    print(f"\n✨ Test completed at: {result['test_timestamp']}")
    print("🔍 Use the queries above with database MCP to verify the data!")