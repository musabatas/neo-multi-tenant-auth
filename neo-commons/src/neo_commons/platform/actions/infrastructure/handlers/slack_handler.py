"""Slack action handler for platform actions infrastructure.

This module implements Slack action handling for domain events.
Single responsibility: Handle Slack actions by delegating to Slack adapter.

Extracted to platform/actions following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import asyncio
from typing import Any, Dict, Optional

from ...core.entities import DomainEvent, Action
from ...core.protocols import ActionHandler
from .....core.shared.context import RequestContext
from .....utils import utc_now
from ..adapters.slack_notification_adapter import SlackNotificationAdapter, SlackConfiguration


class SlackHandler(ActionHandler):
    """Slack action handler using Slack notification adapter.
    
    ONLY handles Slack action execution by delegating to Slack notification adapter.
    Single responsibility: Bridge between action execution and Slack delivery.
    NO business logic, NO validation, NO external dependencies beyond Slack adapter.
    """
    
    def __init__(self, slack_adapter: SlackNotificationAdapter):
        """Initialize handler with Slack adapter.
        
        Args:
            slack_adapter: Slack notification adapter for delivery
        """
        self._slack_adapter = slack_adapter
    
    # ===========================================
    # ActionHandler Protocol Implementation
    # ===========================================
    
    @property
    def handler_type(self) -> str:
        """Get the handler type identifier.
        
        Returns:
            Handler type string for Slack actions
        """
        return "slack"
    
    async def can_handle(self, action: Action) -> bool:
        """Check if this handler can process the given action.
        
        Args:
            action: Event action to check
            
        Returns:
            True if this handler can process the action
        """
        return (
            action.handler_type == self.handler_type and
            action.configuration.get("webhook_url") is not None
        )
    
    async def handle(
        self,
        event: DomainEvent,
        action: Action,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Handle Slack action by sending Slack notification for domain event.
        
        Args:
            event: Domain event that triggered the action
            action: Event action configuration for Slack delivery
            context: Optional request context for tracking
            
        Returns:
            Dictionary with action execution results
            
        Raises:
            SlackDeliveryError: If Slack message cannot be delivered
            ActionExecutionError: If action execution fails
        """
        execution_record = {
            "handler_type": self.handler_type,
            "action_id": str(action.id.value),
            "event_id": str(event.id.value),
            "execution_status": "pending",
            "started_at": utc_now(),
            "context_id": str(context.request_id) if context else None
        }
        
        try:
            # Validate action configuration
            validation_result = await self._validate_slack_config(action)
            if not validation_result["is_valid"]:
                raise ValueError(f"Invalid Slack configuration: {validation_result['errors']}")
            
            # Execute Slack delivery using adapter
            delivery_result = await self._slack_adapter.send_notification(
                event=event,
                action=action,
                context=context
            )
            
            execution_record.update({
                "execution_status": "completed" if delivery_result["success"] else "failed",
                "completed_at": utc_now(),
                "delivery_result": delivery_result,
                "slack_response": delivery_result.get("slack_response"),
                "message_size_bytes": delivery_result.get("message_size_bytes", 0),
                "delivery_duration_ms": delivery_result.get("delivery_duration_ms", 0),
                "success": delivery_result["success"]
            })
            
            return execution_record
            
        except Exception as e:
            execution_record.update({
                "execution_status": "failed",
                "completed_at": utc_now(),
                "error_message": str(e),
                "error_type": type(e).__name__,
                "success": False
            })
            
            return execution_record
    
    async def handle_batch(
        self,
        events_and_actions: list[tuple[DomainEvent, Action]],
        context: Optional[RequestContext] = None
    ) -> list[Dict[str, Any]]:
        """Handle multiple Slack actions efficiently.
        
        Args:
            events_and_actions: List of (event, action) tuples to process
            context: Optional request context for tracking
            
        Returns:
            List of execution results for each action
        """
        # Filter for Slack actions only
        slack_items = [
            (event, action) for event, action in events_and_actions
            if await self.can_handle(action)
        ]
        
        if not slack_items:
            return []
        
        # Process Slack messages concurrently
        slack_notifications = []
        for event, action in slack_items:
            slack_notifications.append({
                "event": event,
                "action": action,
                "context": context
            })
        
        # Use adapter batch delivery
        delivery_results = await self._slack_adapter.send_batch_notifications(
            slack_notifications,
            preserve_order=False,  # Allow concurrent delivery
            max_concurrent=5  # Moderate limit for Slack API
        )
        
        # Convert delivery results to execution results
        execution_results = []
        for i, (event, action) in enumerate(slack_items):
            delivery_result = delivery_results[i] if i < len(delivery_results) else {}
            
            execution_result = {
                "handler_type": self.handler_type,
                "action_id": str(action.id.value),
                "event_id": str(event.id.value),
                "execution_status": "completed" if delivery_result.get("success") else "failed",
                "delivery_result": delivery_result,
                "success": delivery_result.get("success", False)
            }
            
            execution_results.append(execution_result)
        
        return execution_results
    
    # ===========================================
    # Slack Handler Operations
    # ===========================================
    
    async def test_slack_configuration(self, action: Action) -> Dict[str, Any]:
        """Test Slack configuration for action.
        
        Args:
            action: Event action with Slack configuration to test
            
        Returns:
            Dictionary with configuration test results
        """
        try:
            # Use adapter's validation
            validation_result = await self._slack_adapter.validate_configuration(action)
            
            # Test webhook connectivity if configuration is valid
            if validation_result["is_valid"]:
                webhook_url = action.configuration.get("webhook_url")
                if webhook_url:
                    webhook_test = await self._slack_adapter.test_webhook(webhook_url)
                    validation_result.update({
                        "webhook_test": webhook_test
                    })
            
            return validation_result
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Configuration test failed: {str(e)}"],
                "webhook_test": {
                    "webhook_accessible": False,
                    "error_message": str(e)
                }
            }
    
    async def preview_slack_message(
        self,
        event: DomainEvent,
        action: Action
    ) -> Dict[str, Any]:
        """Preview Slack message that would be sent for event and action.
        
        Args:
            event: Domain event for content generation
            action: Event action with Slack configuration
            
        Returns:
            Dictionary with preview content
        """
        try:
            # Extract Slack configuration
            config = action.configuration
            
            # Generate preview using adapter's message building logic
            slack_config = self._slack_adapter._extract_slack_config(action)
            message = await self._slack_adapter._build_slack_message(event, action, slack_config)
            
            # Create attachment preview if auto-generated
            attachment_preview = None
            if not message.attachments and not message.blocks:
                attachment_preview = await self._slack_adapter.create_event_attachment(event)
            
            return {
                "preview_successful": True,
                "text": message.text,
                "channel": message.channel,
                "username": message.username,
                "icon_emoji": message.icon_emoji,
                "icon_url": message.icon_url,
                "attachments": message.attachments or ([attachment_preview] if attachment_preview else []),
                "blocks": message.blocks,
                "estimated_size_bytes": len(message.text) + (
                    len(str(message.attachments)) if message.attachments else 0
                ) + (
                    len(str(message.blocks)) if message.blocks else 0
                )
            }
            
        except Exception as e:
            return {
                "preview_successful": False,
                "error": f"Preview generation failed: {str(e)}"
            }
    
    async def create_event_blocks_preview(
        self,
        event: DomainEvent,
        include_actions: bool = False
    ) -> Dict[str, Any]:
        """Create Slack blocks preview for event.
        
        Args:
            event: Domain event to format as blocks
            include_actions: Whether to include interactive elements
            
        Returns:
            Dictionary with Slack blocks preview
        """
        try:
            # Create action with blocks configuration for preview
            from ...core.entities import Action
            from ...core.value_objects import ActionId
            from .....utils import generate_uuid_v7
            
            preview_action = Action(
                id=ActionId(generate_uuid_v7()),
                name="Preview Action",
                handler_type="slack",
                configuration={"webhook_url": "https://hooks.slack.com/example"}
            )
            
            blocks = await self._slack_adapter.create_blocks_message(
                event=event,
                action=preview_action,
                include_actions=include_actions
            )
            
            return {
                "blocks_preview_successful": True,
                "blocks": blocks,
                "block_count": len(blocks),
                "estimated_size_bytes": len(str(blocks))
            }
            
        except Exception as e:
            return {
                "blocks_preview_successful": False,
                "error": f"Blocks preview generation failed: {str(e)}"
            }
    
    async def get_handler_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get Slack handler performance metrics.
        
        Args:
            time_range_hours: Time range for metrics calculation
            
        Returns:
            Dictionary with handler performance metrics
        """
        # This would typically query execution logs/metrics
        # For now, return placeholder metrics
        return {
            "handler_type": self.handler_type,
            "time_range_hours": time_range_hours,
            "total_executions": 0,  # Would query from execution logs
            "successful_executions": 0,
            "failed_executions": 0,
            "total_messages_sent": 0,
            "total_channels_notified": 0,
            "average_execution_time_ms": 0,
            "success_rate": 0.0,
            "webhook_error_rate": 0.0,
            "error_rate": 0.0
        }
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    async def _validate_slack_config(self, action: Action) -> Dict[str, Any]:
        """Validate Slack configuration in action.
        
        Args:
            action: Event action with Slack configuration
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        config = action.configuration
        
        # Required webhook URL validation
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            validation_result["errors"].append("Slack webhook URL is required")
            validation_result["is_valid"] = False
        elif not webhook_url.startswith("https://hooks.slack.com/"):
            validation_result["warnings"].append(
                "webhook_url should be a valid Slack webhook URL"
            )
        
        # Message content validation
        if not config.get("text") and not config.get("attachments") and not config.get("blocks"):
            validation_result["warnings"].append(
                "No message content specified - attachment will be auto-generated"
            )
        
        # Channel validation
        channel = config.get("channel")
        if channel and not (channel.startswith("#") or channel.startswith("@")):
            validation_result["warnings"].append(
                "Channel should start with # for public channels or @ for direct messages"
            )
        
        # Username validation
        username = config.get("username")
        if username and len(username) > 21:
            validation_result["warnings"].append(
                "Username should be 21 characters or fewer"
            )
        
        # Icon validation
        icon_emoji = config.get("icon_emoji")
        icon_url = config.get("icon_url")
        if icon_emoji and icon_url:
            validation_result["warnings"].append(
                "Both icon_emoji and icon_url specified - icon_emoji will take precedence"
            )
        
        if icon_emoji and not (icon_emoji.startswith(":") and icon_emoji.endswith(":")):
            validation_result["warnings"].append(
                "icon_emoji should be wrapped in colons (e.g., :bell:)"
            )
        
        if icon_url and not (icon_url.startswith("http://") or icon_url.startswith("https://")):
            validation_result["errors"].append("icon_url must be a valid HTTP/HTTPS URL")
            validation_result["is_valid"] = False
        
        # Attachments validation
        attachments = config.get("attachments", [])
        if attachments and not isinstance(attachments, list):
            validation_result["errors"].append("attachments must be a list")
            validation_result["is_valid"] = False
        
        # Blocks validation
        blocks = config.get("blocks", [])
        if blocks and not isinstance(blocks, list):
            validation_result["errors"].append("blocks must be a list")
            validation_result["is_valid"] = False
        
        return validation_result


def create_slack_handler(slack_adapter: SlackNotificationAdapter) -> SlackHandler:
    """Factory function to create Slack action handler.
    
    Args:
        slack_adapter: Slack notification adapter for delivery
        
    Returns:
        SlackHandler: Configured handler instance
    """
    return SlackHandler(slack_adapter)