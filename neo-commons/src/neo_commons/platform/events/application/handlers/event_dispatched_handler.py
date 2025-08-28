"""Event dispatched handler for platform events infrastructure.

This module handles ONLY event dispatched notifications following maximum separation architecture.
Single responsibility: Handle post-dispatch event processing, notifications, and state updates.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...core.entities import DomainEvent
from ...core.value_objects import EventId
from ....actions.core.entities import Action  # Import from platform/actions module
from ....actions.core.value_objects import ActionId  # Import from platform/actions module
from .....core.value_objects import UserId
from ...core.events import EventDispatched
from ...core.protocols import EventRepository, NotificationService
from ....actions.core.protocols import ActionRepository  # Import from platform/actions module
from ...core.exceptions import EventHandlerFailed
from .....utils import utc_now


@dataclass
class EventDispatchedHandlerResult:
    """Result of event dispatched handling."""
    success: bool
    processed_at: datetime
    actions_triggered: List[str]  # Action IDs as strings (moved to platform/actions)
    notifications_sent: List[str]
    metrics_recorded: Dict[str, Any]
    errors: List[str]
    processing_duration_ms: float
    
    message: str = "Event dispatched processing completed"


class EventDispatchedHandler:
    """Handler for event dispatched notifications.
    
    Processes events after they have been successfully dispatched,
    triggering follow-up actions, notifications, and metric recording.
    
    Single responsibility: ONLY post-dispatch event processing logic.
    Uses dependency injection through protocols for clean architecture.
    """
    
    def __init__(self, 
                 event_repository: EventRepository,
                 action_repository: ActionRepository,
                 notification_service: Optional[NotificationService] = None):
        """Initialize handler with required dependencies.
        
        Args:
            event_repository: Repository for event persistence operations
            action_repository: Repository for action operations
            notification_service: Optional service for sending notifications
        """
        self._event_repository = event_repository
        self._action_repository = action_repository
        self._notification_service = notification_service
    
    async def handle(self, event_dispatched: EventDispatched) -> EventDispatchedHandlerResult:
        """Handle event dispatched notification.
        
        Processes the dispatched event by:
        1. Recording dispatch metrics
        2. Triggering follow-up actions
        3. Sending notifications if configured
        4. Updating event status and metadata
        
        Args:
            event_dispatched: Event dispatched notification
            
        Returns:
            EventDispatchedHandlerResult with processing outcome
            
        Raises:
            EventHandlerFailed: If handler processing fails
        """
        start_time = utc_now()
        result = EventDispatchedHandlerResult(
            success=True,
            processed_at=start_time,
            actions_triggered=[],
            notifications_sent=[],
            metrics_recorded={},
            errors=[],
            processing_duration_ms=0.0
        )
        
        try:
            # Retrieve the dispatched event
            event = await self._get_dispatched_event(event_dispatched.event_id, result)
            if not event:
                result.success = False
                result.message = f"Event {event_dispatched.event_id} not found for post-dispatch processing"
                return result
            
            # Record dispatch metrics
            await self._record_dispatch_metrics(event, event_dispatched, result)
            
            # Process follow-up actions
            await self._process_follow_up_actions(event, event_dispatched, result)
            
            # Send notifications if configured
            await self._send_dispatch_notifications(event, event_dispatched, result)
            
            # Update event status and metadata
            await self._update_event_status(event, event_dispatched, result)
            
            # Calculate processing duration
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            result.message = f"Event {event_dispatched.event_id} dispatch processing completed successfully"
            return result
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Handler processing failed: {str(e)}")
            result.message = f"Event dispatch processing failed: {str(e)}"
            
            # Calculate duration even on failure
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log error but don't re-raise to avoid breaking event flow
            await self._log_handler_error(event_dispatched.event_id, str(e))
            
            return result
    
    async def _get_dispatched_event(self, event_id: EventId, result: EventDispatchedHandlerResult) -> Optional[DomainEvent]:
        """Retrieve the dispatched event from repository.
        
        Args:
            event_id: ID of the event to retrieve
            result: Result object to update with errors
            
        Returns:
            DomainEvent if found, None otherwise
        """
        try:
            return await self._event_repository.get_by_id(event_id)
        except Exception as e:
            result.errors.append(f"Failed to retrieve event {event_id}: {str(e)}")
            return None
    
    async def _record_dispatch_metrics(self, event: DomainEvent, event_dispatched: EventDispatched, 
                                     result: EventDispatchedHandlerResult):
        """Record metrics about the event dispatch.
        
        Args:
            event: The dispatched event
            event_dispatched: Dispatch notification
            result: Result object to update with metrics
        """
        try:
            # Calculate dispatch latency
            dispatch_latency_ms = None
            if event_dispatched.dispatched_at and event.created_at:
                dispatch_latency_ms = (event_dispatched.dispatched_at - event.created_at).total_seconds() * 1000
            
            # Record various metrics
            metrics = {
                "event_type": event.event_type,
                "dispatch_latency_ms": dispatch_latency_ms,
                "actions_created": event_dispatched.actions_created,
                "total_actions": len(event_dispatched.actions_created),
                "dispatch_timestamp": event_dispatched.dispatched_at.isoformat() if event_dispatched.dispatched_at else None,
                "event_size_bytes": len(str(event.data)) if event.data else 0,
                "tenant_id": getattr(event, "tenant_id", None),
                "user_id": str(event_dispatched.triggered_by) if event_dispatched.triggered_by else None
            }
            
            # Store metrics in result
            result.metrics_recorded.update(metrics)
            
            # TODO: Send metrics to monitoring system
            # This would integrate with monitoring service when available
            
        except Exception as e:
            result.errors.append(f"Failed to record dispatch metrics: {str(e)}")
    
    async def _process_follow_up_actions(self, event: DomainEvent, event_dispatched: EventDispatched,
                                       result: EventDispatchedHandlerResult):
        """Process any follow-up actions that should be triggered after dispatch.
        
        Args:
            event: The dispatched event
            event_dispatched: Dispatch notification
            result: Result object to update with triggered actions
        """
        try:
            # Check if there are any conditional follow-up actions to create
            follow_up_actions = await self._identify_follow_up_actions(event, event_dispatched)
            
            for follow_up_action in follow_up_actions:
                try:
                    # Create the follow-up action
                    action_id = await self._create_follow_up_action(follow_up_action, event)
                    result.actions_triggered.append(action_id)
                    
                except Exception as e:
                    result.errors.append(f"Failed to create follow-up action: {str(e)}")
                    
        except Exception as e:
            result.errors.append(f"Failed to process follow-up actions: {str(e)}")
    
    async def _identify_follow_up_actions(self, event: DomainEvent, event_dispatched: EventDispatched) -> List[Dict[str, Any]]:
        """Identify follow-up actions that should be created after dispatch.
        
        Args:
            event: The dispatched event
            event_dispatched: Dispatch notification
            
        Returns:
            List of follow-up action specifications
        """
        follow_up_actions = []
        
        # Example follow-up actions based on event patterns
        
        # If this was a high-priority event, create monitoring action
        if hasattr(event, "priority") and getattr(event, "priority", "normal") == "high":
            follow_up_actions.append({
                "action_type": "monitor_event_impact",
                "handler_type": "function",
                "configuration": {
                    "monitor_duration_minutes": 30,
                    "check_interval_seconds": 60,
                    "event_id": str(event.id)
                },
                "description": f"Monitor impact of high-priority event {event.id}"
            })
        
        # If multiple actions were created, add coordination action
        if len(event_dispatched.actions_created) > 3:
            follow_up_actions.append({
                "action_type": "coordinate_parallel_actions",
                "handler_type": "function", 
                "configuration": {
                    "action_ids": [str(action_id) for action_id in event_dispatched.actions_created],
                    "coordination_timeout_minutes": 15
                },
                "description": f"Coordinate {len(event_dispatched.actions_created)} parallel actions for event {event.id}"
            })
        
        # If event contains sensitive data, add audit action
        if self._contains_sensitive_data(event):
            follow_up_actions.append({
                "action_type": "audit_data_access",
                "handler_type": "function",
                "configuration": {
                    "event_id": str(event.id),
                    "audit_level": "detailed",
                    "retention_days": 90
                },
                "description": f"Audit sensitive data access for event {event.id}"
            })
        
        return follow_up_actions
    
    async def _create_follow_up_action(self, action_spec: Dict[str, Any], event: DomainEvent) -> ActionId:
        """Create a follow-up action based on specification.
        
        Args:
            action_spec: Action specification dictionary
            event: The originating event
            
        Returns:
            ActionId of the created follow-up action
        """
        # Create Action entity for the follow-up action using platform/actions service
        # TODO: Use proper Action creation service from platform/actions module
        # For now, this is a placeholder - actual Action creation should be
        # handled by the action management service
        from ....actions.core.entities import Action
        from ....actions.core.value_objects import HandlerType, ActionPriority, ExecutionMode, ActionStatus
        
        action = Action(
            name=action_spec.get("description", "Follow-up action"),
            handler_type=HandlerType.FUNCTION,  # Default to function handler
            configuration=action_spec.get("configuration", {}),
            priority=ActionPriority.NORMAL,
            max_retries=3
        )
        
        # Save to repository
        saved_action = await self._action_repository.save(action)
        return saved_action.id
    
    async def _send_dispatch_notifications(self, event: DomainEvent, event_dispatched: EventDispatched,
                                         result: EventDispatchedHandlerResult):
        """Send notifications about successful event dispatch.
        
        Args:
            event: The dispatched event
            event_dispatched: Dispatch notification
            result: Result object to update with notification results
        """
        if not self._notification_service:
            return  # No notification service configured
        
        try:
            # Determine who should be notified based on event properties
            notification_recipients = await self._determine_notification_recipients(event, event_dispatched)
            
            for recipient in notification_recipients:
                try:
                    notification_id = await self._send_dispatch_notification(
                        recipient, event, event_dispatched
                    )
                    result.notifications_sent.append(notification_id)
                    
                except Exception as e:
                    result.errors.append(f"Failed to send notification to {recipient}: {str(e)}")
                    
        except Exception as e:
            result.errors.append(f"Failed to process dispatch notifications: {str(e)}")
    
    async def _determine_notification_recipients(self, event: DomainEvent, event_dispatched: EventDispatched) -> List[str]:
        """Determine who should receive dispatch notifications.
        
        Args:
            event: The dispatched event
            event_dispatched: Dispatch notification
            
        Returns:
            List of notification recipient identifiers
        """
        recipients = []
        
        # Notify the user who triggered the event (if specified)
        if event_dispatched.triggered_by:
            recipients.append(f"user:{event_dispatched.triggered_by}")
        
        # Notify based on event type and priority
        if hasattr(event, "priority") and getattr(event, "priority", "normal") == "critical":
            recipients.append("admin:critical_events")
        
        # Notify based on tenant (if multi-tenant)
        if hasattr(event, "tenant_id") and getattr(event, "tenant_id"):
            recipients.append(f"tenant_admin:{getattr(event, 'tenant_id')}")
        
        return recipients
    
    async def _send_dispatch_notification(self, recipient: str, event: DomainEvent, 
                                        event_dispatched: EventDispatched) -> str:
        """Send notification to specific recipient.
        
        Args:
            recipient: Notification recipient identifier
            event: The dispatched event
            event_dispatched: Dispatch notification
            
        Returns:
            Notification ID
        """
        notification_data = {
            "type": "event_dispatched",
            "event_id": str(event.id),
            "event_type": event.event_type,
            "dispatched_at": event_dispatched.dispatched_at.isoformat() if event_dispatched.dispatched_at else None,
            "actions_created": len(event_dispatched.actions_created),
            "recipient": recipient
        }
        
        return await self._notification_service.send_notification(
            recipient=recipient,
            notification_type="event_dispatched",
            data=notification_data
        )
    
    async def _update_event_status(self, event: DomainEvent, event_dispatched: EventDispatched,
                                 result: EventDispatchedHandlerResult):
        """Update event status and metadata after dispatch processing.
        
        Args:
            event: The dispatched event
            event_dispatched: Dispatch notification
            result: Processing result
        """
        try:
            # Update event with post-dispatch metadata
            metadata_updates = {
                "post_dispatch_processed_at": utc_now().isoformat(),
                "actions_triggered_count": len(result.actions_triggered),
                "notifications_sent_count": len(result.notifications_sent),
                "follow_up_actions": [str(action_id) for action_id in result.actions_triggered],
                "dispatch_processing_duration_ms": result.processing_duration_ms,
                "metrics_recorded": result.metrics_recorded
            }
            
            # Add any errors that occurred during processing
            if result.errors:
                metadata_updates["post_dispatch_errors"] = result.errors
            
            # Update event metadata
            await self._event_repository.update_metadata(event.id, metadata_updates)
            
        except Exception as e:
            result.errors.append(f"Failed to update event status: {str(e)}")
    
    def _contains_sensitive_data(self, event: DomainEvent) -> bool:
        """Check if event contains sensitive data requiring audit.
        
        Args:
            event: Event to check for sensitive data
            
        Returns:
            True if event contains sensitive data
        """
        # Define sensitive data indicators
        sensitive_keywords = [
            "password", "credit_card", "ssn", "social_security", "bank_account",
            "personal_data", "pii", "medical", "financial", "confidential"
        ]
        
        # Check event type
        event_type_lower = event.event_type.lower()
        if any(keyword in event_type_lower for keyword in sensitive_keywords):
            return True
        
        # Check event data keys and values
        if event.data:
            event_data_str = str(event.data).lower()
            if any(keyword in event_data_str for keyword in sensitive_keywords):
                return True
        
        # Check metadata
        if hasattr(event, "metadata") and event.metadata:
            metadata_str = str(event.metadata).lower()
            if any(keyword in metadata_str for keyword in sensitive_keywords):
                return True
        
        return False
    
    async def _log_handler_error(self, event_id: EventId, error_message: str):
        """Log handler error for monitoring and debugging.
        
        Args:
            event_id: ID of the event being processed
            error_message: Error message to log
        """
        # TODO: Integrate with logging system
        # For now, this is a placeholder for structured logging
        error_log = {
            "handler": "EventDispatchedHandler",
            "event_id": str(event_id),
            "error": error_message,
            "timestamp": utc_now().isoformat(),
            "level": "error"
        }
        
        # In a real implementation, this would be sent to a logging service
        print(f"Handler Error: {error_log}")


def create_event_dispatched_handler(
    event_repository: EventRepository,
    action_repository: ActionRepository,
    notification_service: Optional[NotificationService] = None
) -> EventDispatchedHandler:
    """Factory function to create EventDispatchedHandler instance.
    
    Args:
        event_repository: Repository for event persistence operations
        action_repository: Repository for action operations
        notification_service: Optional service for sending notifications
        
    Returns:
        Configured EventDispatchedHandler instance
    """
    return EventDispatchedHandler(
        event_repository=event_repository,
        action_repository=action_repository,
        notification_service=notification_service
    )