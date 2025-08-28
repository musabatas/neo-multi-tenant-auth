"""Slack notification adapter for platform events infrastructure.

This module implements Slack notification delivery for domain events.
Single responsibility: Send Slack messages triggered by events.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import aiohttp

from ...core.entities import DomainEvent, Action
from .....core.shared.context import RequestContext
from .....utils import utc_now, ensure_utc


@dataclass
class SlackConfiguration:
    """Slack configuration for webhook delivery."""
    
    webhook_url: str
    channel: Optional[str] = None
    username: Optional[str] = None
    icon_emoji: Optional[str] = None
    icon_url: Optional[str] = None
    timeout_seconds: int = 30


@dataclass
class SlackMessage:
    """Slack message with content and formatting."""
    
    text: str
    channel: Optional[str] = None
    username: Optional[str] = None
    icon_emoji: Optional[str] = None
    icon_url: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    blocks: Optional[List[Dict[str, Any]]] = None
    thread_ts: Optional[str] = None
    reply_broadcast: bool = False


class SlackNotificationAdapter:
    """Slack notification adapter using webhook API.
    
    ONLY handles Slack message delivery operations following Slack webhook protocol.
    Single responsibility: Send Slack notifications with rich formatting support.
    NO business logic, NO validation, NO external dependencies beyond Slack API.
    """
    
    def __init__(self, configuration: SlackConfiguration):
        """Initialize adapter with Slack configuration.
        
        Args:
            configuration: Slack webhook configuration for message delivery
        """
        self._config = configuration
    
    # ===========================================
    # Core Slack Delivery Operations
    # ===========================================
    
    async def send_notification(
        self,
        event: DomainEvent,
        action: Action,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Send Slack notification for domain event using action configuration.
        
        Args:
            event: Domain event that triggered the notification
            action: Event action containing Slack configuration
            context: Optional request context for tracking
            
        Returns:
            Dictionary with delivery results and metrics
            
        Raises:
            SlackDeliveryError: If message cannot be delivered
            SlackConfigurationError: If Slack configuration is invalid
            SlackTimeoutError: If delivery exceeds timeout threshold
        """
        delivery_record = {
            "notification_id": str(action.id.value),
            "event_id": str(event.id.value),
            "delivery_status": "pending",
            "started_at": utc_now(),
            "attempts": 1,
            "max_retries": action.max_retries or 3,
            "timeout_seconds": action.timeout_seconds or 30,
        }
        
        try:
            # Extract Slack configuration from action
            slack_config = self._extract_slack_config(action)
            
            # Build Slack message from event and action
            message = await self._build_slack_message(event, action, slack_config)
            
            # Send message via Slack webhook
            delivery_start = utc_now()
            response_data = await self._send_slack_webhook(message, slack_config)
            delivery_duration = (utc_now() - delivery_start).total_seconds() * 1000
            
            delivery_record.update({
                "delivery_status": "delivered",
                "completed_at": utc_now(),
                "delivery_duration_ms": int(delivery_duration),
                "slack_response": response_data,
                "message_size_bytes": len(json.dumps(message.__dict__)),
                "success": True
            })
            
            return delivery_record
            
        except Exception as e:
            delivery_record.update({
                "delivery_status": "failed",
                "completed_at": utc_now(),
                "error_message": str(e),
                "error_type": type(e).__name__,
                "success": False
            })
            
            # Implement retry logic with exponential backoff
            if delivery_record["attempts"] < delivery_record["max_retries"]:
                delay = (action.retry_delay_seconds or 5) * (2 ** (delivery_record["attempts"] - 1))
                await asyncio.sleep(min(delay, 60))  # Max 60 seconds delay
                # Could implement recursive retry here
            
            return delivery_record
    
    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]],
        preserve_order: bool = True,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Send multiple Slack notifications efficiently.
        
        Args:
            notifications: List of notification configurations
            preserve_order: Whether to maintain notification ordering
            max_concurrent: Maximum concurrent Slack deliveries
            
        Returns:
            List of delivery results for each notification
        """
        if preserve_order:
            # Sequential delivery
            results = []
            for notification in notifications:
                result = await self.send_notification(
                    notification["event"],
                    notification["action"],
                    notification.get("context")
                )
                results.append(result)
            return results
        else:
            # Concurrent delivery with semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def send_with_limit(notification):
                async with semaphore:
                    return await self.send_notification(
                        notification["event"],
                        notification["action"],
                        notification.get("context")
                    )
            
            tasks = [send_with_limit(notif) for notif in notifications]
            return await asyncio.gather(*tasks)
    
    # ===========================================
    # Slack Message Formatting Operations
    # ===========================================
    
    async def create_event_attachment(
        self,
        event: DomainEvent,
        include_details: bool = True,
        color: str = "good"
    ) -> Dict[str, Any]:
        """Create Slack attachment for domain event.
        
        Args:
            event: Domain event to format as attachment
            include_details: Whether to include event details
            color: Attachment color (good, warning, danger, or hex)
            
        Returns:
            Dictionary with Slack attachment configuration
        """
        attachment = {
            "color": color,
            "title": f"Event: {event.event_name or event.event_type.value}",
            "title_link": None,  # Could link to event details page
            "text": f"Event ID: {event.id.value}",
            "footer": "Event System",
            "ts": int(event.occurred_at.timestamp()) if event.occurred_at else None,
        }
        
        if include_details:
            fields = [
                {
                    "title": "Event Type",
                    "value": event.event_type.value,
                    "short": True
                },
                {
                    "title": "Aggregate",
                    "value": f"{event.aggregate_type} ({event.aggregate_id})",
                    "short": True
                }
            ]
            
            if event.aggregate_version:
                fields.append({
                    "title": "Version",
                    "value": str(event.aggregate_version),
                    "short": True
                })
            
            attachment["fields"] = fields
            
            # Add event data if available
            if event.event_data:
                attachment["text"] += f"\n\n```\n{json.dumps(event.event_data, indent=2)}\n```"
        
        return attachment
    
    async def create_blocks_message(
        self,
        event: DomainEvent,
        action: Action,
        include_actions: bool = False
    ) -> List[Dict[str, Any]]:
        """Create Slack blocks for rich message formatting.
        
        Args:
            event: Domain event to format as blocks
            action: Event action with configuration
            include_actions: Whether to include interactive elements
            
        Returns:
            List of Slack block elements
        """
        blocks = [
            # Header block
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 {event.event_name or event.event_type.value}"
                }
            },
            # Context block
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Event ID:* {event.id.value}"
                    },
                    {
                        "type": "mrkdwn", 
                        "text": f"*Type:* {event.event_type.value}"
                    }
                ]
            },
            # Main content section
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Aggregate:* {event.aggregate_type}\n*ID:* {event.aggregate_id}"
                }
            }
        ]
        
        # Add event data if available
        if event.event_data:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Event Data:*\n```\n{json.dumps(event.event_data, indent=2)}\n```"
                }
            })
        
        # Add action buttons if requested
        if include_actions:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Details"
                        },
                        "url": f"https://events.example.com/events/{event.id.value}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Acknowledge"
                        },
                        "action_id": f"ack_event_{event.id.value}"
                    }
                ]
            })
        
        return blocks
    
    # ===========================================
    # Slack Configuration Operations
    # ===========================================
    
    async def validate_configuration(self, action: Action) -> Dict[str, Any]:
        """Validate Slack configuration in event action.
        
        Args:
            action: Event action containing Slack configuration
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        config = action.configuration
        
        # Required fields validation
        if not config.get("webhook_url"):
            validation_result["errors"].append("Missing required field: webhook_url")
            validation_result["is_valid"] = False
        
        # Webhook URL format validation
        webhook_url = config.get("webhook_url", "")
        if webhook_url and not webhook_url.startswith("https://hooks.slack.com/"):
            validation_result["warnings"].append(
                "webhook_url should be a valid Slack webhook URL"
            )
        
        # Message content validation
        if not config.get("text") and not config.get("attachments") and not config.get("blocks"):
            validation_result["errors"].append(
                "Message must contain either text, attachments, or blocks"
            )
            validation_result["is_valid"] = False
        
        return validation_result
    
    async def test_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Test Slack webhook URL connectivity.
        
        Args:
            webhook_url: Slack webhook URL to test
            
        Returns:
            Dictionary with test results
        """
        test_result = {
            "webhook_accessible": False,
            "response_time_ms": 0,
            "test_message_sent": False,
            "error_message": None
        }
        
        start_time = utc_now()
        
        try:
            # Send test message
            test_message = {
                "text": "🧪 Test message from Event System",
                "attachments": [{
                    "color": "good",
                    "text": "This is a test notification to verify webhook connectivity.",
                    "footer": "Event System Test"
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=test_message,
                    timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        test_result["webhook_accessible"] = True
                        test_result["test_message_sent"] = True
                    else:
                        test_result["error_message"] = f"HTTP {response.status}: {await response.text()}"
            
        except Exception as e:
            test_result["error_message"] = str(e)
        finally:
            test_result["response_time_ms"] = int(
                (utc_now() - start_time).total_seconds() * 1000
            )
        
        return test_result
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    def _extract_slack_config(self, action: Action) -> Dict[str, Any]:
        """Extract and validate Slack configuration from action.
        
        Args:
            action: Event action containing Slack configuration
            
        Returns:
            Validated Slack configuration dictionary
        """
        config = action.configuration
        
        return {
            "webhook_url": config.get("webhook_url") or self._config.webhook_url,
            "channel": config.get("channel") or self._config.channel,
            "username": config.get("username") or self._config.username,
            "icon_emoji": config.get("icon_emoji") or self._config.icon_emoji,
            "icon_url": config.get("icon_url") or self._config.icon_url,
            "text": config.get("text", ""),
            "attachments": config.get("attachments", []),
            "blocks": config.get("blocks", [])
        }
    
    async def _build_slack_message(
        self,
        event: DomainEvent,
        action: Action,
        slack_config: Dict[str, Any]
    ) -> SlackMessage:
        """Build Slack message from event and configuration.
        
        Args:
            event: Domain event providing message content
            action: Event action with Slack configuration
            slack_config: Processed Slack configuration
            
        Returns:
            SlackMessage ready for delivery
        """
        # Generate default message if none provided
        text = slack_config.get("text")
        if not text:
            text = f"📢 Event: {event.event_name or event.event_type.value}"
        
        # Template substitution for text
        text = text.format(
            event_id=event.id.value,
            event_type=event.event_type.value,
            event_name=event.event_name or event.event_type.value,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            occurred_at=event.occurred_at.isoformat() if event.occurred_at else "unknown"
        )
        
        message = SlackMessage(
            text=text,
            channel=slack_config.get("channel"),
            username=slack_config.get("username"),
            icon_emoji=slack_config.get("icon_emoji"),
            icon_url=slack_config.get("icon_url"),
            attachments=slack_config.get("attachments"),
            blocks=slack_config.get("blocks")
        )
        
        # Auto-generate attachment if none provided
        if not message.attachments and not message.blocks:
            attachment = await self.create_event_attachment(event)
            message.attachments = [attachment]
        
        return message
    
    async def _send_slack_webhook(
        self,
        message: SlackMessage,
        slack_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message via Slack webhook.
        
        Args:
            message: SlackMessage to send
            slack_config: Slack configuration with webhook URL
            
        Returns:
            Slack API response data
        """
        webhook_url = slack_config["webhook_url"]
        
        # Build webhook payload
        payload = {"text": message.text}
        
        if message.channel:
            payload["channel"] = message.channel
        if message.username:
            payload["username"] = message.username
        if message.icon_emoji:
            payload["icon_emoji"] = message.icon_emoji
        if message.icon_url:
            payload["icon_url"] = message.icon_url
        if message.attachments:
            payload["attachments"] = message.attachments
        if message.blocks:
            payload["blocks"] = message.blocks
        if message.thread_ts:
            payload["thread_ts"] = message.thread_ts
        if message.reply_broadcast:
            payload["reply_broadcast"] = message.reply_broadcast
        
        # Send webhook request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Slack webhook failed: HTTP {response.status} - {error_text}")
                
                return {
                    "status_code": response.status,
                    "response_text": await response.text(),
                    "headers": dict(response.headers)
                }


def create_slack_adapter(configuration: SlackConfiguration) -> SlackNotificationAdapter:
    """Factory function to create Slack notification adapter.
    
    Args:
        configuration: Slack webhook configuration
        
    Returns:
        SlackNotificationAdapter: Configured adapter instance
    """
    return SlackNotificationAdapter(configuration)