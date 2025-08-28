"""Email action handler for platform actions infrastructure.

This module implements email action handling for domain events.
Single responsibility: Handle email actions by delegating to email adapter.

Extracted to platform/actions following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import asyncio
from typing import Any, Dict, Optional

from ...core.entities import DomainEvent, Action
from ...core.protocols import ActionHandler
from .....core.shared.context import RequestContext
from .....utils import utc_now
from ..adapters.email_notification_adapter import EmailNotificationAdapter, EmailConfiguration


class EmailHandler(ActionHandler):
    """Email action handler using email notification adapter.
    
    ONLY handles email action execution by delegating to email notification adapter.
    Single responsibility: Bridge between action execution and email delivery.
    NO business logic, NO validation, NO external dependencies beyond email adapter.
    """
    
    def __init__(self, email_adapter: EmailNotificationAdapter):
        """Initialize handler with email adapter.
        
        Args:
            email_adapter: Email notification adapter for delivery
        """
        self._email_adapter = email_adapter
    
    # ===========================================
    # ActionHandler Protocol Implementation
    # ===========================================
    
    @property
    def handler_type(self) -> str:
        """Get the handler type identifier.
        
        Returns:
            Handler type string for email actions
        """
        return "email"
    
    async def can_handle(self, action: Action) -> bool:
        """Check if this handler can process the given action.
        
        Args:
            action: Event action to check
            
        Returns:
            True if this handler can process the action
        """
        return (
            action.handler_type == self.handler_type and
            action.configuration.get("to") is not None
        )
    
    async def handle(
        self,
        event: DomainEvent,
        action: Action,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Handle email action by sending email notification for domain event.
        
        Args:
            event: Domain event that triggered the action
            action: Event action configuration for email delivery
            context: Optional request context for tracking
            
        Returns:
            Dictionary with action execution results
            
        Raises:
            EmailDeliveryError: If email cannot be delivered
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
            validation_result = await self._validate_email_config(action)
            if not validation_result["is_valid"]:
                raise ValueError(f"Invalid email configuration: {validation_result['errors']}")
            
            # Execute email delivery using adapter
            delivery_result = await self._email_adapter.send_notification(
                event=event,
                action=action,
                context=context
            )
            
            execution_record.update({
                "execution_status": "completed" if delivery_result["success"] else "failed",
                "completed_at": utc_now(),
                "delivery_result": delivery_result,
                "recipient_count": delivery_result.get("recipient_count", 0),
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
        """Handle multiple email actions efficiently.
        
        Args:
            events_and_actions: List of (event, action) tuples to process
            context: Optional request context for tracking
            
        Returns:
            List of execution results for each action
        """
        # Filter for email actions only
        email_items = [
            (event, action) for event, action in events_and_actions
            if await self.can_handle(action)
        ]
        
        if not email_items:
            return []
        
        # Process emails concurrently with adapter batch support
        email_notifications = []
        for event, action in email_items:
            email_notifications.append({
                "event": event,
                "action": action,
                "context": context
            })
        
        # Use adapter batch delivery
        delivery_results = await self._email_adapter.send_batch_notifications(
            email_notifications,
            preserve_order=False,  # Allow concurrent delivery
            max_concurrent=3  # Conservative limit for SMTP
        )
        
        # Convert delivery results to execution results
        execution_results = []
        for i, (event, action) in enumerate(email_items):
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
    # Email Handler Operations
    # ===========================================
    
    async def test_email_configuration(self, action: Action) -> Dict[str, Any]:
        """Test email configuration for action.
        
        Args:
            action: Event action with email configuration to test
            
        Returns:
            Dictionary with configuration test results
        """
        try:
            # Use adapter's validation
            validation_result = await self._email_adapter.validate_configuration(action)
            
            # Test SMTP connection if configuration is valid
            if validation_result["is_valid"]:
                connection_test = await self._email_adapter.test_connection()
                validation_result.update({
                    "smtp_connection": connection_test
                })
            
            return validation_result
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Configuration test failed: {str(e)}"],
                "smtp_connection": {
                    "connection_successful": False,
                    "error_message": str(e)
                }
            }
    
    async def preview_email_content(
        self,
        event: DomainEvent,
        action: Action
    ) -> Dict[str, Any]:
        """Preview email content that would be sent for event and action.
        
        Args:
            event: Domain event for content generation
            action: Event action with email template
            
        Returns:
            Dictionary with preview content
        """
        try:
            # Extract email configuration
            config = action.configuration
            
            # Build preview content using adapter's template logic
            from ..adapters.email_notification_adapter import EmailTemplate
            
            template = EmailTemplate(
                subject_template=config.get("subject", "Event Notification"),
                body_template=config.get("body", ""),
                is_html=config.get("is_html", False)
            )
            
            rendered_content = await self._email_adapter.render_template(
                template=template,
                event=event,
                context={"preview_mode": True}
            )
            
            return {
                "preview_successful": True,
                "subject": rendered_content["subject"],
                "body": rendered_content["body"],
                "is_html": rendered_content["is_html"],
                "recipients": config.get("to", []),
                "estimated_size_bytes": len(rendered_content["body"]),
                "character_count": len(rendered_content["body"])
            }
            
        except Exception as e:
            return {
                "preview_successful": False,
                "error": f"Preview generation failed: {str(e)}"
            }
    
    async def get_handler_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get email handler performance metrics.
        
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
            "total_emails_sent": 0,
            "total_recipients": 0,
            "average_execution_time_ms": 0,
            "success_rate": 0.0,
            "bounce_rate": 0.0,  # Would track from SMTP responses
            "error_rate": 0.0
        }
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    async def _validate_email_config(self, action: Action) -> Dict[str, Any]:
        """Validate email configuration in action.
        
        Args:
            action: Event action with email configuration
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        config = action.configuration
        
        # Required recipient validation
        recipients = config.get("to")
        if not recipients:
            validation_result["errors"].append("Email recipient(s) required")
            validation_result["is_valid"] = False
        elif isinstance(recipients, str):
            # Single recipient - validate format
            if "@" not in recipients:
                validation_result["errors"].append(f"Invalid email address: {recipients}")
                validation_result["is_valid"] = False
        elif isinstance(recipients, list):
            # Multiple recipients - validate each
            for email in recipients:
                if "@" not in email:
                    validation_result["errors"].append(f"Invalid email address: {email}")
                    validation_result["is_valid"] = False
        
        # Subject validation
        if not config.get("subject"):
            validation_result["warnings"].append("Email subject is empty")
        
        # Body validation
        if not config.get("body") and not config.get("template"):
            validation_result["errors"].append("Email body or template is required")
            validation_result["is_valid"] = False
        
        # Content length validation
        body = config.get("body", "")
        if len(body) > 1000000:  # 1MB limit
            validation_result["warnings"].append("Email body exceeds recommended size limit")
        
        # HTML validation
        if config.get("is_html") and not isinstance(config.get("is_html"), bool):
            validation_result["errors"].append("is_html must be a boolean value")
            validation_result["is_valid"] = False
        
        return validation_result


def create_email_handler(email_adapter: EmailNotificationAdapter) -> EmailHandler:
    """Factory function to create email action handler.
    
    Args:
        email_adapter: Email notification adapter for delivery
        
    Returns:
        EmailHandler: Configured handler instance
    """
    return EmailHandler(email_adapter)