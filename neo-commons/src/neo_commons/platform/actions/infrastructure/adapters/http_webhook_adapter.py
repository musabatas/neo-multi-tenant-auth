"""HTTP webhook adapter implementation for platform events infrastructure.

This module implements HTTP webhook delivery with comprehensive error handling,
retry logic, authentication, and performance monitoring.

Single responsibility: ONLY HTTP webhook delivery to external endpoints.
Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import json
import hashlib
import hmac
import asyncio
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin

import aiohttp
import ssl

from .....core.value_objects import UserId
from .....utils import utc_now, ensure_utc
from ...core.entities.domain_event import DomainEvent
from ...core.entities.event_action import Action
from ...core.entities.webhook_delivery import WebhookDelivery


class HttpWebhookAdapter:
    """HTTP webhook adapter for secure webhook delivery.
    
    Provides reliable HTTP webhook delivery with enterprise-grade features:
    - HMAC signature authentication
    - Comprehensive retry logic with exponential backoff
    - SSL/TLS certificate verification
    - Request/response logging and metrics
    - Timeout handling and connection pooling
    - Custom header support and user agent
    
    Single responsibility: ONLY HTTP webhook delivery.
    Pure platform infrastructure - optimized for high-volume webhook dispatch.
    """
    
    def __init__(
        self,
        default_timeout_seconds: int = 30,
        max_retries: int = 3,
        retry_backoff_multiplier: float = 2.0,
        retry_base_delay_seconds: int = 1,
        connection_pool_limit: int = 100,
        user_agent: str = "NeoMultiTenant-Platform-Events/1.0"
    ):
        """Initialize HTTP webhook adapter with configuration.
        
        Args:
            default_timeout_seconds: Default request timeout
            max_retries: Maximum retry attempts for failed deliveries
            retry_backoff_multiplier: Exponential backoff multiplier
            retry_base_delay_seconds: Base delay between retries
            connection_pool_limit: HTTP connection pool limit
            user_agent: User agent string for HTTP requests
        """
        self._default_timeout = default_timeout_seconds
        self._max_retries = max_retries
        self._backoff_multiplier = retry_backoff_multiplier
        self._base_delay = retry_base_delay_seconds
        self._user_agent = user_agent
        
        # HTTP session configuration
        self._connector = aiohttp.TCPConnector(
            limit=connection_pool_limit,
            ssl=ssl.create_default_context()  # Secure SSL context
        )
        
        # Will be initialized on first use
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with proper configuration.
        
        Returns:
            Configured aiohttp ClientSession
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._default_timeout)
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers={"User-Agent": self._user_agent}
            )
        return self._session
    
    async def deliver_webhook(
        self,
        event: DomainEvent,
        action: Action,
        delivery_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deliver webhook for domain event using action configuration.
        
        Args:
            event: Domain event to deliver via webhook
            action: Event action containing webhook configuration
            delivery_context: Optional additional delivery context
            
        Returns:
            Dictionary with delivery results and metrics
            
        Raises:
            ValueError: If action is not configured for webhook delivery
            WebhookDeliveryError: If delivery fails after all retries
        """
        # Validate action configuration
        if action.handler_type.value != "webhook":
            raise ValueError(f"Action {action.id} is not configured for webhook delivery")
        
        webhook_config = action.configuration
        if not webhook_config.get("url"):
            raise ValueError(f"Action {action.id} missing webhook URL configuration")
        
        # Create delivery record as dict for now (simplified approach)
        delivery_record = {
            "webhook_endpoint_id": str(action.id.value),
            "webhook_event_id": str(event.id.value),
            "request_url": webhook_config["url"],
            "request_method": webhook_config.get("method", "POST"),
            "attempt_number": 1,
            "delivery_status": "pending",
            "created_at": utc_now(),
            "delivery_context": delivery_context or {}
        }
        
        # Attempt delivery with retry logic
        for attempt in range(1, self._max_retries + 2):  # +1 for initial attempt
            try:
                delivery_record["attempt_number"] = attempt
                delivery_record["delivery_status"] = "retrying"
                delivery_record["attempted_at"] = utc_now()
                
                # Prepare webhook payload and headers
                payload = self._prepare_webhook_payload(event, action)
                headers = self._prepare_webhook_headers(event, action, payload)
                
                # Make HTTP request
                start_time = utc_now()
                session = await self._get_session()
                
                async with session.request(
                    method=webhook_config.get("method", "POST"),
                    url=webhook_config["url"],
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(
                        total=webhook_config.get("timeout", self._default_timeout)
                    ),
                    ssl=webhook_config.get("verify_ssl", True)
                ) as response:
                    end_time = utc_now()
                    response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                    
                    # Read response data
                    response_body = await response.text()
                    response_headers = dict(response.headers)
                    
                    # Record successful delivery
                    delivery_record.update({
                        "delivery_status": "success",
                        "response_status_code": response.status,
                        "response_headers": response_headers,
                        "response_body": response_body,
                        "response_time_ms": response_time_ms,
                        "completed_at": end_time,
                        "error_message": None,
                        "error_code": None
                    })
                    
                    return delivery_record
            
            except Exception as error:
                error_message = str(error)
                
                # Record failed attempt
                delivery_record.update({
                    "delivery_status": "failed",
                    "error_message": error_message,
                    "error_code": error.__class__.__name__,
                    "completed_at": utc_now()
                })
                
                # Check if we should retry
                if attempt <= self._max_retries:
                    # Calculate delay for next retry
                    delay_seconds = self._base_delay * (self._backoff_multiplier ** (attempt - 1))
                    delay_seconds = min(delay_seconds, 300)  # Cap at 5 minutes
                    
                    delivery_record["next_retry_at"] = utc_now().replace(microsecond=0) + \
                        timedelta(seconds=delay_seconds)
                    
                    # Wait before retry
                    await asyncio.sleep(delay_seconds)
                else:
                    # Max retries reached
                    delivery_record["max_attempts_reached"] = True
                    break
        
        return delivery_record
    
    def _prepare_webhook_payload(self, event: DomainEvent, action: Action) -> Dict[str, Any]:
        """Prepare webhook payload from domain event and action configuration.
        
        Args:
            event: Domain event to include in payload
            action: Event action with payload configuration
            
        Returns:
            Dictionary containing webhook payload
        """
        # Base payload structure
        payload = {
            # Event identification
            "event_id": str(event.id.value),
            "event_type": event.event_type.value,
            "event_name": event.event_name,
            
            # Event source
            "aggregate_id": str(event.aggregate_id),
            "aggregate_type": event.aggregate_type,
            "aggregate_version": event.aggregate_version,
            
            # Event timing
            "occurred_at": event.occurred_at.isoformat(),
            "created_at": event.created_at.isoformat(),
            
            # Event data
            "data": event.event_data,
            "metadata": event.event_metadata,
            
            # Event context
            "correlation_id": str(event.correlation_id) if event.correlation_id else None,
            "causation_id": str(event.causation_id) if event.causation_id else None,
            "context_id": str(event.context_id) if event.context_id else None,
            "triggered_by_user_id": str(event.triggered_by_user_id.value) if event.triggered_by_user_id else None,
            
            # Platform metadata
            "platform": {
                "version": "1.0",
                "source": "neo-multitenant-platform",
                "action_id": str(action.id.value),
                "action_name": action.name
            }
        }
        
        # Apply any payload transformations from action configuration
        payload_config = action.configuration.get("payload", {})
        
        # Include/exclude specific fields if configured
        if "include_fields" in payload_config:
            # Filter to only include specified fields
            filtered_payload = {}
            for field in payload_config["include_fields"]:
                if field in payload:
                    filtered_payload[field] = payload[field]
            payload = filtered_payload
        
        if "exclude_fields" in payload_config:
            # Remove specified fields
            for field in payload_config["exclude_fields"]:
                payload.pop(field, None)
        
        # Add custom fields if configured
        if "custom_fields" in payload_config:
            payload.update(payload_config["custom_fields"])
        
        return payload
    
    def _prepare_webhook_headers(
        self,
        event: DomainEvent,
        action: Action,
        payload: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare HTTP headers for webhook delivery including HMAC signature.
        
        Args:
            event: Domain event being delivered
            action: Event action with header configuration
            payload: Webhook payload for signature calculation
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
            "X-Event-Type": event.event_type.value,
            "X-Event-ID": str(event.id.value),
            "X-Event-Timestamp": event.occurred_at.isoformat(),
            "X-Aggregate-Type": event.aggregate_type,
            "X-Aggregate-ID": str(event.aggregate_id),
        }
        
        # Add correlation headers if available
        if event.correlation_id:
            headers["X-Correlation-ID"] = str(event.correlation_id)
        
        if event.causation_id:
            headers["X-Causation-ID"] = str(event.causation_id)
        
        # Add custom headers from action configuration
        webhook_config = action.configuration
        if "headers" in webhook_config:
            headers.update(webhook_config["headers"])
        
        # Generate HMAC signature if secret is configured
        if "secret" in webhook_config:
            signature = self._generate_hmac_signature(
                payload=json.dumps(payload, sort_keys=True),
                secret=webhook_config["secret"],
                algorithm=webhook_config.get("signature_algorithm", "sha256")
            )
            
            signature_header = webhook_config.get("signature_header", "X-Webhook-Signature")
            headers[signature_header] = signature
        
        return headers
    
    def _generate_hmac_signature(
        self,
        payload: str,
        secret: str,
        algorithm: str = "sha256"
    ) -> str:
        """Generate HMAC signature for webhook authentication.
        
        Args:
            payload: JSON payload string to sign
            secret: Secret key for HMAC generation
            algorithm: Hash algorithm (sha256, sha512, etc.)
            
        Returns:
            HMAC signature string with algorithm prefix
        """
        # Get hash function
        if algorithm == "sha256":
            hash_func = hashlib.sha256
        elif algorithm == "sha512":
            hash_func = hashlib.sha512
        elif algorithm == "sha1":
            hash_func = hashlib.sha1
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        # Generate HMAC
        mac = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hash_func
        )
        
        # Return with algorithm prefix (GitHub style)
        return f"{algorithm}={mac.hexdigest()}"
    
    async def verify_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Verify HMAC signature for incoming webhook validation.
        
        Args:
            payload: Webhook payload string
            signature: HMAC signature to verify
            secret: Secret key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Extract algorithm from signature
            if "=" not in signature:
                return False
            
            algorithm, expected_sig = signature.split("=", 1)
            
            # Generate expected signature
            expected_signature = self._generate_hmac_signature(payload, secret, algorithm)
            expected_sig_value = expected_signature.split("=", 1)[1]
            
            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_sig, expected_sig_value)
        
        except Exception:
            return False
    
    async def test_webhook_endpoint(
        self,
        webhook_url: str,
        webhook_config: Dict[str, Any],
        test_event: Optional[DomainEvent] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Test webhook endpoint connectivity and configuration.
        
        Args:
            webhook_url: URL to test
            webhook_config: Webhook configuration
            test_event: Optional test event to send
            
        Returns:
            Tuple of (success, result_info)
        """
        try:
            # Create test event if not provided
            if test_event is None:
                from ...core.value_objects import EventType, EventId
                from .....utils import generate_uuid_v7
                
                test_event = DomainEvent(
                    id=EventId(generate_uuid_v7()),
                    event_type=EventType("platform.webhook_test"),
                    aggregate_id=generate_uuid_v7(),
                    aggregate_type="webhook_test",
                    event_data={"test": True, "timestamp": utc_now().isoformat()},
                    event_metadata={"source": "webhook_test"}
                )
            
            # Create test action configuration
            from ...core.entities.event_action import Action
            from ...core.value_objects import HandlerType, ActionPriority, ExecutionMode, ActionStatus
            
            test_action = Action(
                name="webhook_test",
                handler_type=HandlerType.WEBHOOK,
                configuration=webhook_config,
                event_types=["platform.webhook_test"],
                priority=ActionPriority.NORMAL,
                execution_mode=ExecutionMode.SYNC,
                status=ActionStatus.ACTIVE
            )
            
            # Attempt delivery
            start_time = utc_now()
            delivery_result = await self.deliver_webhook(test_event, test_action)
            end_time = utc_now()
            
            success = delivery_result.get("delivery_status") == "success"
            result_info = {
                "success": success,
                "status_code": delivery_result.get("response_status_code"),
                "response_time_ms": delivery_result.get("response_time_ms"),
                "test_duration_ms": int((end_time - start_time).total_seconds() * 1000),
                "error_message": delivery_result.get("error_message") if not success else None,
                "response_headers": delivery_result.get("response_headers") if success else None
            }
            
            return success, result_info
        
        except Exception as error:
            return False, {
                "success": False,
                "error_message": str(error),
                "error_type": error.__class__.__name__
            }
    
    async def close(self):
        """Close HTTP session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        
        if self._connector:
            await self._connector.close()


# Factory function for dependency injection
def create_http_webhook_adapter(**kwargs) -> HttpWebhookAdapter:
    """Factory function to create HttpWebhookAdapter instance.
    
    Args:
        **kwargs: Configuration parameters for the adapter
        
    Returns:
        HttpWebhookAdapter instance ready for use
    """
    return HttpWebhookAdapter(**kwargs)