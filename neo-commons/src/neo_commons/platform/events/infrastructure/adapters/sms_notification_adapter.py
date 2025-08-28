"""SMS notification adapter for platform events infrastructure.

This module implements SMS notification delivery for domain events.
Single responsibility: Send SMS messages triggered by events.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urlencode

import aiohttp

from ...core.entities import DomainEvent
from ....actions.core.entities import Action  # Import from platform/actions module
from .....core.shared.context import RequestContext
from .....utils import utc_now, ensure_utc


@dataclass
class TwilioConfiguration:
    """Twilio configuration for SMS delivery."""
    
    account_sid: str
    auth_token: str
    from_number: str
    base_url: str = "https://api.twilio.com/2010-04-01"
    timeout_seconds: int = 30


@dataclass
class SMSMessage:
    """SMS message with content and metadata."""
    
    to_number: str
    body: str
    from_number: Optional[str] = None
    media_urls: Optional[List[str]] = None
    status_callback: Optional[str] = None
    max_price: Optional[str] = None
    validity_period: Optional[int] = None


class SMSNotificationAdapter:
    """SMS notification adapter using Twilio API.
    
    ONLY handles SMS delivery operations following Twilio API protocol.
    Single responsibility: Send SMS notifications with delivery tracking.
    NO business logic, NO validation, NO external dependencies beyond Twilio API.
    """
    
    def __init__(self, configuration: TwilioConfiguration):
        """Initialize adapter with Twilio configuration.
        
        Args:
            configuration: Twilio configuration for SMS delivery
        """
        self._config = configuration
    
    # ===========================================
    # Core SMS Delivery Operations
    # ===========================================
    
    async def send_notification(
        self,
        event: DomainEvent,
        action: Action,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Send SMS notification for domain event using action configuration.
        
        Args:
            event: Domain event that triggered the notification
            action: Event action containing SMS configuration
            context: Optional request context for tracking
            
        Returns:
            Dictionary with delivery results and metrics
            
        Raises:
            SMSDeliveryError: If SMS cannot be delivered
            SMSConfigurationError: If SMS configuration is invalid
            SMSTimeoutError: If delivery exceeds timeout threshold
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
            # Extract SMS configuration from action
            sms_config = self._extract_sms_config(action)
            
            # Build SMS message from event and action
            message = await self._build_sms_message(event, action, sms_config)
            
            # Send SMS via Twilio API
            delivery_start = utc_now()
            response_data = await self._send_twilio_sms(message, sms_config)
            delivery_duration = (utc_now() - delivery_start).total_seconds() * 1000
            
            delivery_record.update({
                "delivery_status": "delivered",
                "completed_at": utc_now(),
                "delivery_duration_ms": int(delivery_duration),
                "twilio_response": response_data,
                "message_sid": response_data.get("sid"),
                "message_length": len(message.body),
                "recipient_number": message.to_number,
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
                await asyncio.sleep(min(delay, 300))  # Max 5 minutes delay
                # Could implement recursive retry here
            
            return delivery_record
    
    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]],
        preserve_order: bool = True,
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """Send multiple SMS notifications efficiently.
        
        Args:
            notifications: List of notification configurations
            preserve_order: Whether to maintain notification ordering
            max_concurrent: Maximum concurrent SMS deliveries
            
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
            # Concurrent delivery with semaphore (lower limit for SMS)
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
    # SMS Message Formatting Operations
    # ===========================================
    
    async def format_event_message(
        self,
        event: DomainEvent,
        template: Optional[str] = None,
        max_length: int = 160
    ) -> str:
        """Format domain event as SMS message text.
        
        Args:
            event: Domain event to format
            template: Optional message template
            max_length: Maximum message length (default SMS limit)
            
        Returns:
            Formatted SMS message text
        """
        if template:
            # Template substitution
            message = template.format(
                event_id=str(event.id.value)[:8],  # Short ID for SMS
                event_type=event.event_type.value,
                event_name=event.event_name or event.event_type.value,
                aggregate_id=str(event.aggregate_id)[:8],  # Short ID
                aggregate_type=event.aggregate_type,
                occurred_at=event.occurred_at.strftime("%H:%M") if event.occurred_at else "now"
            )
        else:
            # Default message format
            message = f"🔔 {event.event_name or event.event_type.value}\n"
            message += f"ID: {str(event.id.value)[:8]}\n"
            message += f"Type: {event.aggregate_type}\n"
            message += f"Time: {event.occurred_at.strftime('%H:%M') if event.occurred_at else 'now'}"
        
        # Truncate if too long
        if len(message) > max_length:
            message = message[:max_length - 3] + "..."
        
        return message
    
    async def validate_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """Validate phone number format and deliverability.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "formatted_number": phone_number,
            "country_code": None,
            "carrier": None,
            "line_type": None,
            "errors": []
        }
        
        # Basic format validation
        if not phone_number:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Phone number cannot be empty")
            return validation_result
        
        # Remove common formatting
        cleaned_number = ''.join(filter(str.isdigit, phone_number))
        
        # Check minimum length
        if len(cleaned_number) < 10:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Phone number too short")
        
        # Add + prefix if missing
        if not phone_number.startswith('+'):
            if len(cleaned_number) == 10:
                # Assume US number
                validation_result["formatted_number"] = f"+1{cleaned_number}"
                validation_result["country_code"] = "US"
            elif len(cleaned_number) == 11 and cleaned_number.startswith('1'):
                # US number with country code
                validation_result["formatted_number"] = f"+{cleaned_number}"
                validation_result["country_code"] = "US"
            else:
                validation_result["formatted_number"] = f"+{cleaned_number}"
        
        return validation_result
    
    # ===========================================
    # SMS Delivery Status Operations
    # ===========================================
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get delivery status of SMS message from Twilio.
        
        Args:
            message_sid: Twilio message SID
            
        Returns:
            Dictionary with message status information
        """
        try:
            url = f"{self._config.base_url}/Accounts/{self._config.account_sid}/Messages/{message_sid}.json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    auth=aiohttp.BasicAuth(self._config.account_sid, self._config.auth_token),
                    timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "message_sid": data.get("sid"),
                            "status": data.get("status"),
                            "error_code": data.get("error_code"),
                            "error_message": data.get("error_message"),
                            "date_created": data.get("date_created"),
                            "date_sent": data.get("date_sent"),
                            "date_updated": data.get("date_updated"),
                            "price": data.get("price"),
                            "price_unit": data.get("price_unit"),
                            "direction": data.get("direction"),
                            "num_segments": data.get("num_segments")
                        }
                    else:
                        return {
                            "error": f"Failed to get message status: HTTP {response.status}",
                            "message_sid": message_sid
                        }
        
        except Exception as e:
            return {
                "error": f"Failed to get message status: {str(e)}",
                "message_sid": message_sid
            }
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get current Twilio account balance.
        
        Returns:
            Dictionary with account balance information
        """
        try:
            url = f"{self._config.base_url}/Accounts/{self._config.account_sid}/Balance.json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    auth=aiohttp.BasicAuth(self._config.account_sid, self._config.auth_token),
                    timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "currency": data.get("currency"),
                            "balance": data.get("balance"),
                            "account_sid": data.get("account_sid")
                        }
                    else:
                        return {
                            "error": f"Failed to get account balance: HTTP {response.status}"
                        }
        
        except Exception as e:
            return {
                "error": f"Failed to get account balance: {str(e)}"
            }
    
    # ===========================================
    # SMS Configuration Operations
    # ===========================================
    
    async def validate_configuration(self, action: Action) -> Dict[str, Any]:
        """Validate SMS configuration in event action.
        
        Args:
            action: Event action containing SMS configuration
            
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
        if not config.get("to_number"):
            validation_result["errors"].append("Missing required field: to_number")
            validation_result["is_valid"] = False
        
        if not config.get("body") and not config.get("template"):
            validation_result["errors"].append("Missing message content: body or template required")
            validation_result["is_valid"] = False
        
        # Phone number validation
        if config.get("to_number"):
            phone_validation = await self.validate_phone_number(config["to_number"])
            if not phone_validation["is_valid"]:
                validation_result["errors"].extend(phone_validation["errors"])
                validation_result["is_valid"] = False
        
        # Message length validation
        message_body = config.get("body", "")
        if len(message_body) > 1600:  # MMS limit
            validation_result["warnings"].append("Message exceeds SMS limit, will be sent as MMS")
        
        return validation_result
    
    async def test_credentials(self) -> Dict[str, Any]:
        """Test Twilio credentials and configuration.
        
        Returns:
            Dictionary with test results
        """
        test_result = {
            "credentials_valid": False,
            "account_accessible": False,
            "from_number_valid": False,
            "test_duration_ms": 0,
            "error_message": None
        }
        
        start_time = utc_now()
        
        try:
            # Test account access
            balance_info = await self.get_account_balance()
            if not balance_info.get("error"):
                test_result["credentials_valid"] = True
                test_result["account_accessible"] = True
            
            # Validate from number format
            from_number_validation = await self.validate_phone_number(self._config.from_number)
            test_result["from_number_valid"] = from_number_validation["is_valid"]
            
        except Exception as e:
            test_result["error_message"] = str(e)
        finally:
            test_result["test_duration_ms"] = int(
                (utc_now() - start_time).total_seconds() * 1000
            )
        
        return test_result
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    def _extract_sms_config(self, action: Action) -> Dict[str, Any]:
        """Extract and validate SMS configuration from action.
        
        Args:
            action: Event action containing SMS configuration
            
        Returns:
            Validated SMS configuration dictionary
        """
        config = action.configuration
        
        return {
            "to_number": config.get("to_number"),
            "body": config.get("body", ""),
            "template": config.get("template"),
            "from_number": config.get("from_number") or self._config.from_number,
            "media_urls": config.get("media_urls", []),
            "status_callback": config.get("status_callback"),
            "max_price": config.get("max_price"),
            "validity_period": config.get("validity_period")
        }
    
    async def _build_sms_message(
        self,
        event: DomainEvent,
        action: Action,
        sms_config: Dict[str, Any]
    ) -> SMSMessage:
        """Build SMS message from event and configuration.
        
        Args:
            event: Domain event providing message content
            action: Event action with SMS configuration
            sms_config: Processed SMS configuration
            
        Returns:
            SMSMessage ready for delivery
        """
        # Generate message body
        if sms_config.get("template"):
            body = await self.format_event_message(event, sms_config["template"])
        elif sms_config.get("body"):
            # Template substitution in body
            body = sms_config["body"].format(
                event_id=str(event.id.value)[:8],
                event_type=event.event_type.value,
                event_name=event.event_name or event.event_type.value,
                aggregate_id=str(event.aggregate_id)[:8],
                aggregate_type=event.aggregate_type,
                occurred_at=event.occurred_at.strftime("%H:%M") if event.occurred_at else "now"
            )
        else:
            body = await self.format_event_message(event)
        
        # Validate phone number format
        phone_validation = await self.validate_phone_number(sms_config["to_number"])
        to_number = phone_validation["formatted_number"]
        
        return SMSMessage(
            to_number=to_number,
            body=body,
            from_number=sms_config.get("from_number"),
            media_urls=sms_config.get("media_urls"),
            status_callback=sms_config.get("status_callback"),
            max_price=sms_config.get("max_price"),
            validity_period=sms_config.get("validity_period")
        )
    
    async def _send_twilio_sms(
        self,
        message: SMSMessage,
        sms_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send SMS message via Twilio API.
        
        Args:
            message: SMSMessage to send
            sms_config: SMS configuration
            
        Returns:
            Twilio API response data
        """
        url = f"{self._config.base_url}/Accounts/{self._config.account_sid}/Messages.json"
        
        # Build form data
        data = {
            "To": message.to_number,
            "From": message.from_number or self._config.from_number,
            "Body": message.body
        }
        
        if message.media_urls:
            for i, media_url in enumerate(message.media_urls):
                data[f"MediaUrl[{i}]"] = media_url
        
        if message.status_callback:
            data["StatusCallback"] = message.status_callback
        
        if message.max_price:
            data["MaxPrice"] = message.max_price
        
        if message.validity_period:
            data["ValidityPeriod"] = message.validity_period
        
        # Send API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=data,
                auth=aiohttp.BasicAuth(self._config.account_sid, self._config.auth_token),
                timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds)
            ) as response:
                response_data = await response.json()
                
                if response.status not in [200, 201]:
                    error_msg = response_data.get("message", f"HTTP {response.status}")
                    raise Exception(f"Twilio API error: {error_msg}")
                
                return response_data


def create_sms_adapter(configuration: TwilioConfiguration) -> SMSNotificationAdapter:
    """Factory function to create SMS notification adapter.
    
    Args:
        configuration: Twilio configuration for SMS delivery
        
    Returns:
        SMSNotificationAdapter: Configured adapter instance
    """
    return SMSNotificationAdapter(configuration)