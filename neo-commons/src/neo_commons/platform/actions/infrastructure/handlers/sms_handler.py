"""SMS action handler for platform actions infrastructure.

This module implements SMS action handling for domain events.
Single responsibility: Handle SMS actions by delegating to SMS adapter.

Extracted to platform/actions following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import asyncio
from typing import Any, Dict, Optional

from ...core.entities import DomainEvent, Action
from ...core.protocols import ActionHandler
from .....core.shared.context import RequestContext
from .....utils import utc_now
from ..adapters.sms_notification_adapter import SMSNotificationAdapter, TwilioConfiguration


class SMSHandler(ActionHandler):
    """SMS action handler using SMS notification adapter.
    
    ONLY handles SMS action execution by delegating to SMS notification adapter.
    Single responsibility: Bridge between action execution and SMS delivery.
    NO business logic, NO validation, NO external dependencies beyond SMS adapter.
    """
    
    def __init__(self, sms_adapter: SMSNotificationAdapter):
        """Initialize handler with SMS adapter.
        
        Args:
            sms_adapter: SMS notification adapter for delivery
        """
        self._sms_adapter = sms_adapter
    
    # ===========================================
    # ActionHandler Protocol Implementation
    # ===========================================
    
    @property
    def handler_type(self) -> str:
        """Get the handler type identifier.
        
        Returns:
            Handler type string for SMS actions
        """
        return "sms"
    
    async def can_handle(self, action: Action) -> bool:
        """Check if this handler can process the given action.
        
        Args:
            action: Event action to check
            
        Returns:
            True if this handler can process the action
        """
        return (
            action.handler_type == self.handler_type and
            action.configuration.get("to_number") is not None
        )
    
    async def handle(
        self,
        event: DomainEvent,
        action: Action,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Handle SMS action by sending SMS notification for domain event.
        
        Args:
            event: Domain event that triggered the action
            action: Event action configuration for SMS delivery
            context: Optional request context for tracking
            
        Returns:
            Dictionary with action execution results
            
        Raises:
            SMSDeliveryError: If SMS cannot be delivered
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
            validation_result = await self._validate_sms_config(action)
            if not validation_result["is_valid"]:
                raise ValueError(f"Invalid SMS configuration: {validation_result['errors']}")
            
            # Execute SMS delivery using adapter
            delivery_result = await self._sms_adapter.send_notification(
                event=event,
                action=action,
                context=context
            )
            
            execution_record.update({
                "execution_status": "completed" if delivery_result["success"] else "failed",
                "completed_at": utc_now(),
                "delivery_result": delivery_result,
                "message_sid": delivery_result.get("message_sid"),
                "recipient_number": delivery_result.get("recipient_number"),
                "message_length": delivery_result.get("message_length", 0),
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
        """Handle multiple SMS actions efficiently.
        
        Args:
            events_and_actions: List of (event, action) tuples to process
            context: Optional request context for tracking
            
        Returns:
            List of execution results for each action
        """
        # Filter for SMS actions only
        sms_items = [
            (event, action) for event, action in events_and_actions
            if await self.can_handle(action)
        ]
        
        if not sms_items:
            return []
        
        # Process SMS messages with conservative concurrency
        sms_notifications = []
        for event, action in sms_items:
            sms_notifications.append({
                "event": event,
                "action": action,
                "context": context
            })
        
        # Use adapter batch delivery with conservative limits for SMS
        delivery_results = await self._sms_adapter.send_batch_notifications(
            sms_notifications,
            preserve_order=False,  # Allow concurrent delivery
            max_concurrent=2  # Very conservative limit for SMS APIs
        )
        
        # Convert delivery results to execution results
        execution_results = []
        for i, (event, action) in enumerate(sms_items):
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
    # SMS Handler Operations
    # ===========================================
    
    async def test_sms_configuration(self, action: Action) -> Dict[str, Any]:
        """Test SMS configuration for action.
        
        Args:
            action: Event action with SMS configuration to test
            
        Returns:
            Dictionary with configuration test results
        """
        try:
            # Use adapter's validation
            validation_result = await self._sms_adapter.validate_configuration(action)
            
            # Test Twilio credentials if configuration is valid
            if validation_result["is_valid"]:
                credentials_test = await self._sms_adapter.test_credentials()
                validation_result.update({
                    "twilio_credentials": credentials_test
                })
            
            return validation_result
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Configuration test failed: {str(e)}"],
                "twilio_credentials": {
                    "credentials_valid": False,
                    "error_message": str(e)
                }
            }
    
    async def preview_sms_content(
        self,
        event: DomainEvent,
        action: Action
    ) -> Dict[str, Any]:
        """Preview SMS content that would be sent for event and action.
        
        Args:
            event: Domain event for content generation
            action: Event action with SMS template
            
        Returns:
            Dictionary with preview content
        """
        try:
            # Extract SMS configuration
            config = action.configuration
            
            # Generate message content using adapter's formatting logic
            template = config.get("template")
            message_body = await self._sms_adapter.format_event_message(
                event=event,
                template=template,
                max_length=160  # SMS limit
            )
            
            # Validate phone number
            phone_validation = await self._sms_adapter.validate_phone_number(
                config.get("to_number", "")
            )
            
            return {
                "preview_successful": True,
                "message_body": message_body,
                "message_length": len(message_body),
                "recipient_number": phone_validation.get("formatted_number"),
                "estimated_segments": 1 if len(message_body) <= 160 else (len(message_body) // 153) + 1,
                "is_valid_number": phone_validation.get("is_valid", False),
                "country_code": phone_validation.get("country_code")
            }
            
        except Exception as e:
            return {
                "preview_successful": False,
                "error": f"Preview generation failed: {str(e)}"
            }
    
    async def get_message_delivery_status(self, message_sid: str) -> Dict[str, Any]:
        """Get delivery status for specific SMS message.
        
        Args:
            message_sid: Twilio message SID to check
            
        Returns:
            Dictionary with message delivery status
        """
        try:
            return await self._sms_adapter.get_message_status(message_sid)
        except Exception as e:
            return {
                "error": f"Failed to get message status: {str(e)}",
                "message_sid": message_sid
            }
    
    async def get_handler_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get SMS handler performance metrics.
        
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
            "total_segments_sent": 0,
            "average_execution_time_ms": 0,
            "success_rate": 0.0,
            "delivery_rate": 0.0,  # Would track from Twilio status callbacks
            "error_rate": 0.0
        }
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    async def _validate_sms_config(self, action: Action) -> Dict[str, Any]:
        """Validate SMS configuration in action.
        
        Args:
            action: Event action with SMS configuration
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        config = action.configuration
        
        # Required phone number validation
        to_number = config.get("to_number")
        if not to_number:
            validation_result["errors"].append("SMS recipient phone number is required")
            validation_result["is_valid"] = False
        else:
            # Basic phone number format validation
            cleaned_number = ''.join(filter(str.isdigit, to_number))
            if len(cleaned_number) < 10:
                validation_result["errors"].append("Phone number appears to be too short")
                validation_result["is_valid"] = False
        
        # Message content validation
        if not config.get("body") and not config.get("template"):
            validation_result["errors"].append("SMS message body or template is required")
            validation_result["is_valid"] = False
        
        # Message length validation
        message_body = config.get("body", "")
        if len(message_body) > 1600:  # MMS limit
            validation_result["warnings"].append("Message exceeds SMS limit, will be sent as MMS")
        elif len(message_body) > 160:  # SMS limit
            segments = (len(message_body) // 153) + 1
            validation_result["warnings"].append(f"Message will be sent as {segments} SMS segments")
        
        # Media URLs validation (if present)
        media_urls = config.get("media_urls", [])
        if media_urls:
            if not isinstance(media_urls, list):
                validation_result["errors"].append("media_urls must be a list")
                validation_result["is_valid"] = False
            else:
                for url in media_urls:
                    if not (url.startswith("http://") or url.startswith("https://")):
                        validation_result["errors"].append(f"Invalid media URL: {url}")
                        validation_result["is_valid"] = False
        
        return validation_result


def create_sms_handler(sms_adapter: SMSNotificationAdapter) -> SMSHandler:
    """Factory function to create SMS action handler.
    
    Args:
        sms_adapter: SMS notification adapter for delivery
        
    Returns:
        SMSHandler: Configured handler instance
    """
    return SMSHandler(sms_adapter)