"""
Webhook delivery extension interface.

ONLY handles webhook extension contracts and customization points.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass
from enum import Enum
import time

from ....core.value_objects import WebhookId, TenantId, EventId


class WebhookDeliveryStage(Enum):
    """Webhook delivery stages."""
    PRE_DELIVERY = "pre_delivery"
    POST_DELIVERY = "post_delivery"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    ON_RETRY = "on_retry"
    ON_TIMEOUT = "on_timeout"


class WebhookDeliveryStatus(Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


@dataclass
class WebhookExtensionContext:
    """Context provided to webhook extensions."""
    webhook_id: WebhookId
    tenant_id: TenantId
    event_id: EventId
    webhook_url: str
    payload: Dict[str, Any]
    headers: Dict[str, str]
    delivery_stage: WebhookDeliveryStage
    retry_count: int = 0
    response_status_code: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[Dict[str, str]] = None
    delivery_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "webhook_id": self.webhook_id.value,
            "tenant_id": self.tenant_id.value,
            "event_id": self.event_id.value,
            "webhook_url": self.webhook_url,
            "payload": self.payload,
            "headers": self.headers,
            "delivery_stage": self.delivery_stage.value,
            "retry_count": self.retry_count,
            "response_status_code": self.response_status_code,
            "response_body": self.response_body,
            "response_headers": self.response_headers or {},
            "delivery_time_ms": self.delivery_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class WebhookExtensionResult:
    """Result from webhook extension processing."""
    continue_delivery: bool = True
    modified_payload: Optional[Dict[str, Any]] = None
    modified_headers: Optional[Dict[str, str]] = None
    modified_url: Optional[str] = None
    should_retry: bool = False
    retry_delay_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "continue_delivery": self.continue_delivery,
            "modified_payload": self.modified_payload,
            "modified_headers": self.modified_headers,
            "modified_url": self.modified_url,
            "should_retry": self.should_retry,
            "retry_delay_seconds": self.retry_delay_seconds,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "error_message": self.error_message,
        }


class WebhookExtension(ABC):
    """
    Abstract base class for webhook delivery extensions.
    
    Extensions can modify, validate, or react to webhook delivery.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Extension name."""
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        """Extension version."""
        pass
        
    @property
    @abstractmethod
    def supported_webhook_patterns(self) -> List[str]:
        """List of supported webhook URL patterns (empty list means all URLs)."""
        pass
        
    @property
    @abstractmethod
    def delivery_stages(self) -> List[WebhookDeliveryStage]:
        """List of delivery stages this extension handles."""
        pass
        
    @property
    def priority(self) -> int:
        """
        Extension priority (lower numbers run first).
        
        Returns:
            Priority value (0-1000, default 500)
        """
        return 500
        
    @property
    def enabled(self) -> bool:
        """Whether this extension is enabled."""
        return True
        
    @abstractmethod
    async def process_webhook(
        self,
        context: WebhookExtensionContext
    ) -> WebhookExtensionResult:
        """
        Process a webhook at a specific delivery stage.
        
        Args:
            context: Webhook processing context
            
        Returns:
            WebhookExtensionResult indicating processing outcome
        """
        pass
        
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate extension configuration.
        
        Args:
            config: Extension configuration
            
        Returns:
            True if configuration is valid
        """
        return True
        
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the extension with configuration.
        
        Args:
            config: Extension configuration
        """
        pass
        
    async def cleanup(self) -> None:
        """Clean up extension resources."""
        pass
        
    def supports_webhook_url(self, webhook_url: str) -> bool:
        """
        Check if extension supports a specific webhook URL.
        
        Args:
            webhook_url: Webhook URL to check
            
        Returns:
            True if webhook URL is supported
        """
        if not self.supported_webhook_patterns:
            return True  # Empty list means all URLs supported
            
        # Simple pattern matching - could be enhanced with regex
        for pattern in self.supported_webhook_patterns:
            if pattern in webhook_url or webhook_url.startswith(pattern):
                return True
                
        return False
        
    def supports_delivery_stage(self, stage: WebhookDeliveryStage) -> bool:
        """
        Check if extension supports a specific delivery stage.
        
        Args:
            stage: Delivery stage to check
            
        Returns:
            True if stage is supported
        """
        return stage in self.delivery_stages
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get extension metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "supported_webhook_patterns": self.supported_webhook_patterns,
            "delivery_stages": [stage.value for stage in self.delivery_stages],
            "priority": self.priority,
            "enabled": self.enabled,
        }


class WebhookAuthenticationExtension(WebhookExtension):
    """
    Specialized extension for webhook authentication.
    
    Adds authentication headers and signatures to webhook requests.
    """
    
    @property
    def delivery_stages(self) -> List[WebhookDeliveryStage]:
        """Authentication extensions run at pre_delivery stage."""
        return [WebhookDeliveryStage.PRE_DELIVERY]
        
    @abstractmethod
    async def add_authentication(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        tenant_id: TenantId
    ) -> Dict[str, str]:
        """
        Add authentication to webhook request.
        
        Args:
            webhook_url: Target webhook URL
            payload: Webhook payload
            headers: Current headers
            tenant_id: Tenant context
            
        Returns:
            Updated headers with authentication
        """
        pass
        
    async def process_webhook(
        self,
        context: WebhookExtensionContext
    ) -> WebhookExtensionResult:
        """Process webhook using authentication logic."""
        try:
            auth_headers = await self.add_authentication(
                context.webhook_url,
                context.payload,
                context.headers,
                context.tenant_id
            )
            
            return WebhookExtensionResult(
                continue_delivery=True,
                modified_headers=auth_headers
            )
            
        except Exception as e:
            return WebhookExtensionResult(
                continue_delivery=False,
                error_message=f"Authentication failed: {str(e)}"
            )


class WebhookRetryExtension(WebhookExtension):
    """
    Specialized extension for webhook retry logic.
    
    Provides retry-specific methods and configuration.
    """
    
    @property
    def delivery_stages(self) -> List[WebhookDeliveryStage]:
        """Retry extensions run at on_failure and on_retry stages."""
        return [WebhookDeliveryStage.ON_FAILURE, WebhookDeliveryStage.ON_RETRY]
        
    @abstractmethod
    async def should_retry_webhook(
        self,
        context: WebhookExtensionContext
    ) -> bool:
        """
        Determine if a webhook should be retried.
        
        Args:
            context: Webhook processing context
            
        Returns:
            True if webhook should be retried
        """
        pass
        
    @abstractmethod
    async def calculate_retry_delay(
        self,
        context: WebhookExtensionContext
    ) -> int:
        """
        Calculate delay before retry attempt.
        
        Args:
            context: Webhook processing context
            
        Returns:
            Delay in seconds before retry
        """
        pass
        
    async def get_max_retries(self, context: WebhookExtensionContext) -> int:
        """
        Get maximum number of retries for webhook.
        
        Args:
            context: Webhook processing context
            
        Returns:
            Maximum retry count
        """
        return 3  # Default max retries
        
    async def process_webhook(
        self,
        context: WebhookExtensionContext
    ) -> WebhookExtensionResult:
        """Process webhook using retry logic."""
        if context.delivery_stage == WebhookDeliveryStage.ON_FAILURE:
            max_retries = await self.get_max_retries(context)
            
            if context.retry_count < max_retries and await self.should_retry_webhook(context):
                delay = await self.calculate_retry_delay(context)
                return WebhookExtensionResult(
                    continue_delivery=False,
                    should_retry=True,
                    retry_delay_seconds=delay,
                    max_retries=max_retries
                )
            else:
                return WebhookExtensionResult(
                    continue_delivery=False,
                    error_message=f"Webhook failed after {max_retries} retries"
                )
                
        return WebhookExtensionResult(continue_delivery=True)


class WebhookTransformationExtension(WebhookExtension):
    """
    Specialized extension for webhook payload transformation.
    
    Transforms payload before delivery.
    """
    
    @property
    def delivery_stages(self) -> List[WebhookDeliveryStage]:
        """Transformation extensions run at pre_delivery stage."""
        return [WebhookDeliveryStage.PRE_DELIVERY]
        
    @abstractmethod
    async def transform_payload(
        self,
        payload: Dict[str, Any],
        webhook_url: str,
        tenant_id: TenantId
    ) -> Dict[str, Any]:
        """
        Transform webhook payload.
        
        Args:
            payload: Original payload
            webhook_url: Target webhook URL
            tenant_id: Tenant context
            
        Returns:
            Transformed payload
        """
        pass
        
    async def process_webhook(
        self,
        context: WebhookExtensionContext
    ) -> WebhookExtensionResult:
        """Process webhook using transformation logic."""
        try:
            transformed_payload = await self.transform_payload(
                context.payload,
                context.webhook_url,
                context.tenant_id
            )
            
            return WebhookExtensionResult(
                continue_delivery=True,
                modified_payload=transformed_payload
            )
            
        except Exception as e:
            return WebhookExtensionResult(
                continue_delivery=False,
                error_message=f"Payload transformation failed: {str(e)}"
            )


class WebhookMonitoringExtension(WebhookExtension):
    """
    Specialized extension for webhook monitoring and metrics.
    
    Collects delivery metrics and logs.
    """
    
    @property
    def delivery_stages(self) -> List[WebhookDeliveryStage]:
        """Monitoring extensions run at all stages."""
        return list(WebhookDeliveryStage)
        
    @abstractmethod
    async def record_delivery_metric(
        self,
        context: WebhookExtensionContext,
        metric_name: str,
        metric_value: Any,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a webhook delivery metric.
        
        Args:
            context: Webhook processing context
            metric_name: Name of the metric
            metric_value: Value of the metric
            tags: Optional metric tags
        """
        pass
        
    async def process_webhook(
        self,
        context: WebhookExtensionContext
    ) -> WebhookExtensionResult:
        """Process webhook using monitoring logic."""
        await self.record_delivery_metric(
            context,
            f"webhook.delivery.{context.delivery_stage.value}",
            1,
            {
                "tenant_id": context.tenant_id.value,
                "webhook_url": context.webhook_url,
                "retry_count": str(context.retry_count),
            }
        )
        
        # Record response time if available
        if context.delivery_time_ms is not None:
            await self.record_delivery_metric(
                context,
                "webhook.delivery.response_time_ms",
                context.delivery_time_ms,
                {"tenant_id": context.tenant_id.value}
            )
            
        return WebhookExtensionResult(continue_delivery=True)


# Protocol for webhook extension factories
class WebhookExtensionFactory(Protocol):
    """Protocol for creating webhook extensions."""
    
    def create_extension(
        self,
        extension_type: str,
        config: Dict[str, Any]
    ) -> WebhookExtension:
        """Create an extension instance."""
        ...
        
    def list_available_extensions(self) -> List[Dict[str, Any]]:
        """List available extension types."""
        ...