"""
Notification delivery extension interface.

ONLY handles notification extension contracts and customization points.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol, Union
from dataclasses import dataclass
from enum import Enum

from ....core.value_objects import NotificationId, TenantId, EventId, UserId


class NotificationType(Enum):
    """Notification types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    SLACK = "slack"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    URGENT = "urgent"


class NotificationDeliveryStage(Enum):
    """Notification delivery stages."""
    PRE_DELIVERY = "pre_delivery"
    POST_DELIVERY = "post_delivery"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    ON_RETRY = "on_retry"


@dataclass
class NotificationRecipient:
    """Notification recipient information."""
    user_id: Optional[UserId] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    device_token: Optional[str] = None
    slack_channel: Optional[str] = None
    webhook_url: Optional[str] = None
    custom_identifier: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id.value if self.user_id else None,
            "email": self.email,
            "phone": self.phone,
            "device_token": self.device_token,
            "slack_channel": self.slack_channel,
            "webhook_url": self.webhook_url,
            "custom_identifier": self.custom_identifier,
        }


@dataclass
class NotificationContent:
    """Notification content structure."""
    subject: Optional[str] = None
    body: str = ""
    html_body: Optional[str] = None
    template_id: Optional[str] = None
    template_variables: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "subject": self.subject,
            "body": self.body,
            "html_body": self.html_body,
            "template_id": self.template_id,
            "template_variables": self.template_variables or {},
            "attachments": self.attachments or [],
        }


@dataclass
class NotificationExtensionContext:
    """Context provided to notification extensions."""
    notification_id: NotificationId
    tenant_id: TenantId
    event_id: EventId
    notification_type: NotificationType
    priority: NotificationPriority
    recipient: NotificationRecipient
    content: NotificationContent
    delivery_stage: NotificationDeliveryStage
    metadata: Dict[str, Any]
    retry_count: int = 0
    delivery_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "notification_id": self.notification_id.value,
            "tenant_id": self.tenant_id.value,
            "event_id": self.event_id.value,
            "notification_type": self.notification_type.value,
            "priority": self.priority.value,
            "recipient": self.recipient.to_dict(),
            "content": self.content.to_dict(),
            "delivery_stage": self.delivery_stage.value,
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "delivery_time_ms": self.delivery_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class NotificationExtensionResult:
    """Result from notification extension processing."""
    continue_delivery: bool = True
    modified_content: Optional[NotificationContent] = None
    modified_recipient: Optional[NotificationRecipient] = None
    should_retry: bool = False
    retry_delay_seconds: Optional[int] = None
    error_message: Optional[str] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "continue_delivery": self.continue_delivery,
            "modified_content": self.modified_content.to_dict() if self.modified_content else None,
            "modified_recipient": self.modified_recipient.to_dict() if self.modified_recipient else None,
            "should_retry": self.should_retry,
            "retry_delay_seconds": self.retry_delay_seconds,
            "error_message": self.error_message,
            "additional_metadata": self.additional_metadata,
        }


class NotificationExtension(ABC):
    """
    Abstract base class for notification delivery extensions.
    
    Extensions can modify, validate, or react to notification delivery.
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
    def supported_notification_types(self) -> List[NotificationType]:
        """List of supported notification types (empty list means all types)."""
        pass
        
    @property
    @abstractmethod
    def delivery_stages(self) -> List[NotificationDeliveryStage]:
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
    async def process_notification(
        self,
        context: NotificationExtensionContext
    ) -> NotificationExtensionResult:
        """
        Process a notification at a specific delivery stage.
        
        Args:
            context: Notification processing context
            
        Returns:
            NotificationExtensionResult indicating processing outcome
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
        
    def supports_notification_type(self, notification_type: NotificationType) -> bool:
        """
        Check if extension supports a specific notification type.
        
        Args:
            notification_type: Notification type to check
            
        Returns:
            True if notification type is supported
        """
        if not self.supported_notification_types:
            return True  # Empty list means all types supported
            
        return notification_type in self.supported_notification_types
        
    def supports_delivery_stage(self, stage: NotificationDeliveryStage) -> bool:
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
            "supported_notification_types": [nt.value for nt in self.supported_notification_types],
            "delivery_stages": [stage.value for stage in self.delivery_stages],
            "priority": self.priority,
            "enabled": self.enabled,
        }


class NotificationTemplateExtension(NotificationExtension):
    """
    Specialized extension for notification templating.
    
    Applies templates and variable substitution to notifications.
    """
    
    @property
    def delivery_stages(self) -> List[NotificationDeliveryStage]:
        """Template extensions run at pre_delivery stage."""
        return [NotificationDeliveryStage.PRE_DELIVERY]
        
    @abstractmethod
    async def render_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        notification_type: NotificationType,
        tenant_id: TenantId
    ) -> NotificationContent:
        """
        Render notification template with variables.
        
        Args:
            template_id: Template identifier
            variables: Template variables
            notification_type: Type of notification
            tenant_id: Tenant context
            
        Returns:
            Rendered notification content
        """
        pass
        
    async def process_notification(
        self,
        context: NotificationExtensionContext
    ) -> NotificationExtensionResult:
        """Process notification using templating logic."""
        if context.content.template_id:
            try:
                rendered_content = await self.render_template(
                    context.content.template_id,
                    context.content.template_variables or {},
                    context.notification_type,
                    context.tenant_id
                )
                
                return NotificationExtensionResult(
                    continue_delivery=True,
                    modified_content=rendered_content
                )
                
            except Exception as e:
                return NotificationExtensionResult(
                    continue_delivery=False,
                    error_message=f"Template rendering failed: {str(e)}"
                )
                
        return NotificationExtensionResult(continue_delivery=True)


class NotificationPersonalizationExtension(NotificationExtension):
    """
    Specialized extension for notification personalization.
    
    Personalizes content based on recipient preferences and context.
    """
    
    @property
    def delivery_stages(self) -> List[NotificationDeliveryStage]:
        """Personalization extensions run at pre_delivery stage."""
        return [NotificationDeliveryStage.PRE_DELIVERY]
        
    @abstractmethod
    async def personalize_content(
        self,
        content: NotificationContent,
        recipient: NotificationRecipient,
        tenant_id: TenantId,
        context: Dict[str, Any]
    ) -> NotificationContent:
        """
        Personalize notification content for recipient.
        
        Args:
            content: Original content
            recipient: Notification recipient
            tenant_id: Tenant context
            context: Additional personalization context
            
        Returns:
            Personalized content
        """
        pass
        
    async def process_notification(
        self,
        context: NotificationExtensionContext
    ) -> NotificationExtensionResult:
        """Process notification using personalization logic."""
        try:
            personalized_content = await self.personalize_content(
                context.content,
                context.recipient,
                context.tenant_id,
                context.metadata
            )
            
            return NotificationExtensionResult(
                continue_delivery=True,
                modified_content=personalized_content
            )
            
        except Exception as e:
            return NotificationExtensionResult(
                continue_delivery=False,
                error_message=f"Personalization failed: {str(e)}"
            )


class NotificationFilterExtension(NotificationExtension):
    """
    Specialized extension for notification filtering.
    
    Filters notifications based on recipient preferences and rules.
    """
    
    @property
    def delivery_stages(self) -> List[NotificationDeliveryStage]:
        """Filter extensions run at pre_delivery stage."""
        return [NotificationDeliveryStage.PRE_DELIVERY]
        
    @abstractmethod
    async def should_deliver_notification(
        self,
        context: NotificationExtensionContext
    ) -> bool:
        """
        Determine if notification should be delivered.
        
        Args:
            context: Notification processing context
            
        Returns:
            True if notification should be delivered
        """
        pass
        
    async def get_filter_reason(self, context: NotificationExtensionContext) -> Optional[str]:
        """
        Get reason why notification was filtered.
        
        Args:
            context: Notification processing context
            
        Returns:
            Filter reason or None
        """
        return None
        
    async def process_notification(
        self,
        context: NotificationExtensionContext
    ) -> NotificationExtensionResult:
        """Process notification using filtering logic."""
        should_deliver = await self.should_deliver_notification(context)
        
        if not should_deliver:
            reason = await self.get_filter_reason(context)
            return NotificationExtensionResult(
                continue_delivery=False,
                error_message=f"Notification filtered: {reason or 'No reason provided'}"
            )
            
        return NotificationExtensionResult(continue_delivery=True)


class NotificationRateLimitExtension(NotificationExtension):
    """
    Specialized extension for notification rate limiting.
    
    Prevents notification spam by rate limiting per recipient.
    """
    
    @property
    def delivery_stages(self) -> List[NotificationDeliveryStage]:
        """Rate limit extensions run at pre_delivery stage."""
        return [NotificationDeliveryStage.PRE_DELIVERY]
        
    @abstractmethod
    async def is_rate_limited(
        self,
        recipient: NotificationRecipient,
        notification_type: NotificationType,
        tenant_id: TenantId
    ) -> bool:
        """
        Check if recipient is rate limited.
        
        Args:
            recipient: Notification recipient
            notification_type: Type of notification
            tenant_id: Tenant context
            
        Returns:
            True if recipient is rate limited
        """
        pass
        
    @abstractmethod
    async def record_delivery_attempt(
        self,
        recipient: NotificationRecipient,
        notification_type: NotificationType,
        tenant_id: TenantId
    ) -> None:
        """
        Record a delivery attempt for rate limiting.
        
        Args:
            recipient: Notification recipient
            notification_type: Type of notification
            tenant_id: Tenant context
        """
        pass
        
    async def process_notification(
        self,
        context: NotificationExtensionContext
    ) -> NotificationExtensionResult:
        """Process notification using rate limiting logic."""
        if await self.is_rate_limited(
            context.recipient,
            context.notification_type,
            context.tenant_id
        ):
            return NotificationExtensionResult(
                continue_delivery=False,
                error_message="Recipient rate limited"
            )
            
        # Record this delivery attempt
        await self.record_delivery_attempt(
            context.recipient,
            context.notification_type,
            context.tenant_id
        )
        
        return NotificationExtensionResult(continue_delivery=True)


# Protocol for notification extension factories
class NotificationExtensionFactory(Protocol):
    """Protocol for creating notification extensions."""
    
    def create_extension(
        self,
        extension_type: str,
        config: Dict[str, Any]
    ) -> NotificationExtension:
        """Create an extension instance."""
        ...
        
    def list_available_extensions(self) -> List[Dict[str, Any]]:
        """List available extension types."""
        ...