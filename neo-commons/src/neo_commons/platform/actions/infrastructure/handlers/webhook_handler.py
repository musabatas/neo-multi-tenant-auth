"""Webhook action handler for platform actions infrastructure.

This module implements webhook action handling for domain events.
Single responsibility: Handle webhook actions by delegating to webhook adapter.

Extracted to platform/actions following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import asyncio
from typing import Any, Dict, Optional

from ...core.entities import DomainEvent, Action
from ...core.protocols import ActionHandler
from .....core.shared.context import RequestContext
from .....utils import utc_now
from ..adapters.http_webhook_adapter import HTTPWebhookAdapter, WebhookConfiguration


class WebhookHandler(ActionHandler):
    """Webhook action handler using HTTP webhook adapter.
    
    ONLY handles webhook action execution by delegating to HTTP webhook adapter.
    Single responsibility: Bridge between action execution and webhook delivery.
    NO business logic, NO validation, NO external dependencies beyond webhook adapter.
    """
    
    def __init__(self, webhook_adapter: HTTPWebhookAdapter):
        """Initialize handler with webhook adapter.
        
        Args:
            webhook_adapter: HTTP webhook adapter for delivery
        """
        self._webhook_adapter = webhook_adapter
    
    # ===========================================
    # ActionHandler Protocol Implementation
    # ===========================================
    
    @property
    def handler_type(self) -> str:
        """Get the handler type identifier.
        
        Returns:
            Handler type string for webhook actions
        """
        return "webhook"
    
    async def can_handle(self, action: Action) -> bool:
        """Check if this handler can process the given action.
        
        Args:
            action: Action to check
            
        Returns:
            True if this handler can process the action
        """
        return (
            action.handler_type == self.handler_type and
            action.configuration.get("url") is not None
        )
    
    async def handle(
        self,
        event: DomainEvent,
        action: Action,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Handle webhook action by delivering webhook for domain event.
        
        Args:
            event: Domain event that triggered the action
            action: Action configuration for webhook delivery
            context: Optional request context for tracking
            
        Returns:
            Dictionary with action execution results
            
        Raises:
            WebhookDeliveryError: If webhook cannot be delivered
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
            validation_result = await self._validate_webhook_config(action)
            if not validation_result["is_valid"]:
                raise ValueError(f"Invalid webhook configuration: {validation_result['errors']}")
            
            # Execute webhook delivery using adapter
            delivery_result = await self._webhook_adapter.deliver_webhook(
                event=event,
                action=action,
                context=context
            )
            
            execution_record.update({
                "execution_status": "completed" if delivery_result["success"] else "failed",
                "completed_at": utc_now(),
                "delivery_result": delivery_result,
                "webhook_url": delivery_result.get("request_url"),
                "response_status": delivery_result.get("response_status"),
                "response_time_ms": delivery_result.get("delivery_duration_ms"),
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
        """Handle multiple webhook actions efficiently.
        
        Args:
            events_and_actions: List of (event, action) tuples to process
            context: Optional request context for tracking
            
        Returns:
            List of execution results for each action
        """
        # Filter for webhook actions only
        webhook_items = [
            (event, action) for event, action in events_and_actions
            if await self.can_handle(action)
        ]
        
        if not webhook_items:
            return []
        
        # Process webhooks concurrently with adapter batch support
        webhook_notifications = []
        for event, action in webhook_items:
            webhook_notifications.append({
                "event": event,
                "action": action,
                "context": context
            })
        
        # Use adapter batch delivery
        delivery_results = await self._webhook_adapter.deliver_batch_webhooks(
            webhook_notifications,
            preserve_order=False,  # Allow concurrent delivery
            max_concurrent=5
        )
        
        # Convert delivery results to execution results
        execution_results = []
        for i, (event, action) in enumerate(webhook_items):
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
    # Webhook Handler Operations
    # ===========================================
    
    async def test_webhook_connectivity(self, action: Action) -> Dict[str, Any]:
        """Test webhook connectivity for action configuration.
        
        Args:
            action: Action with webhook configuration to test
            
        Returns:
            Dictionary with connectivity test results
        """
        try:
            webhook_url = action.configuration.get("url")
            if not webhook_url:
                return {
                    "connectivity_test": False,
                    "error": "No webhook URL configured"
                }
            
            # Use adapter's test functionality (if available)
            if hasattr(self._webhook_adapter, 'test_webhook_endpoint'):
                return await self._webhook_adapter.test_webhook_endpoint(webhook_url)
            
            # Basic connectivity test
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(webhook_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        return {
                            "connectivity_test": True,
                            "status_code": response.status,
                            "response_time_ms": 0,  # Simplified
                            "endpoint_reachable": True
                        }
                except Exception as e:
                    return {
                        "connectivity_test": False,
                        "error": str(e),
                        "endpoint_reachable": False
                    }
                    
        except Exception as e:
            return {
                "connectivity_test": False,
                "error": f"Connectivity test failed: {str(e)}"
            }
    
    async def get_handler_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get webhook handler performance metrics.
        
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
            "average_execution_time_ms": 0,
            "success_rate": 0.0,
            "error_rate": 0.0
        }
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    async def _validate_webhook_config(self, action: Action) -> Dict[str, Any]:
        """Validate webhook configuration in action.
        
        Args:
            action: Action with webhook configuration
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        config = action.configuration
        
        # Required URL validation
        if not config.get("url"):
            validation_result["errors"].append("Webhook URL is required")
            validation_result["is_valid"] = False
        
        # URL format validation
        webhook_url = config.get("url", "")
        if webhook_url and not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
            validation_result["errors"].append("Webhook URL must be a valid HTTP/HTTPS URL")
            validation_result["is_valid"] = False
        
        # Method validation
        method = config.get("method", "POST").upper()
        if method not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            validation_result["errors"].append(f"Invalid HTTP method: {method}")
            validation_result["is_valid"] = False
        
        # Timeout validation
        timeout = config.get("timeout", 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            validation_result["errors"].append("Timeout must be a positive number")
            validation_result["is_valid"] = False
        elif timeout > 300:  # 5 minutes max
            validation_result["warnings"].append("Timeout exceeds recommended maximum of 300 seconds")
        
        # Headers validation
        headers = config.get("headers", {})
        if headers and not isinstance(headers, dict):
            validation_result["errors"].append("Headers must be a dictionary")
            validation_result["is_valid"] = False
        
        return validation_result


def create_webhook_handler(webhook_adapter: HTTPWebhookAdapter) -> WebhookHandler:
    """Factory function to create webhook action handler.
    
    Args:
        webhook_adapter: HTTP webhook adapter for delivery
        
    Returns:
        WebhookHandler: Configured handler instance
    """
    return WebhookHandler(webhook_adapter)