"""Notification service protocol for platform events infrastructure.

This module defines the NotificationService protocol contract following maximum separation architecture.
Single responsibility: Send notifications for events, failures, and alerts.

Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class NotificationService(Protocol):
    """Notification service protocol for sending event-related notifications.
    
    This protocol defines the contract for notification operations following
    maximum separation architecture. Single responsibility: send notifications
    for events, failures, alerts, and other system activities.
    
    Supports:
    - Event notifications
    - Failure alerts  
    - System alerts
    - Recovery notifications
    - Status updates
    """
    
    @abstractmethod
    async def send_notification(
        self,
        recipient: str,
        notification_type: str,
        data: Dict[str, Any],
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send a notification to a recipient.
        
        Args:
            recipient: Notification recipient identifier (email, user_id, webhook_url)
            notification_type: Type of notification (event, alert, failure, recovery)
            data: Notification data including title, message, context
            priority: Notification priority (low, normal, high, critical)
            metadata: Additional metadata for notification processing
            
        Returns:
            Notification ID for tracking delivery status
            
        Raises:
            NotificationSendError: If notification fails to send
            InvalidRecipientError: If recipient is invalid or unreachable
        """
        pass
    
    @abstractmethod
    async def send_bulk_notification(
        self,
        recipients: list[str],
        notification_type: str,
        data: Dict[str, Any],
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Send notifications to multiple recipients.
        
        Args:
            recipients: List of recipient identifiers
            notification_type: Type of notification
            data: Notification data
            priority: Notification priority
            metadata: Additional metadata
            
        Returns:
            Dictionary mapping recipient to notification ID
            
        Raises:
            NotificationSendError: If bulk send operation fails
        """
        pass
    
    @abstractmethod
    async def get_notification_status(self, notification_id: str) -> Dict[str, Any]:
        """Get the delivery status of a notification.
        
        Args:
            notification_id: ID of the notification to check
            
        Returns:
            Dictionary with status, delivery_time, retry_count, error_message
            
        Raises:
            NotificationNotFoundError: If notification ID not found
        """
        pass