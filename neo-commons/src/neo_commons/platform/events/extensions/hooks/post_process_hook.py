"""
Post-processing hook implementation.

ONLY handles post-processing lifecycle hooks for events.
"""

import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from .event_hook_registry import HookContext, HookResult
from ....core.value_objects import EventId, TenantId, EventType
from .....actions.core.value_objects import ActionId  # Import from platform/actions module


class PostProcessHook(ABC):
    """
    Abstract base class for post-processing hooks.
    
    Executed after event processing completes.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Hook name for identification."""
        pass
        
    @property
    def supported_event_types(self) -> Optional[List[str]]:
        """
        List of supported event types.
        
        Returns:
            List of event type strings, or None for all types
        """
        return None
        
    @property
    def enabled(self) -> bool:
        """Whether this hook is enabled."""
        return True
        
    @abstractmethod
    async def after_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        processing_result: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute post-processing logic.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            event_data: Original event payload
            processing_result: Result of event processing
            metadata: Processing metadata
            
        Returns:
            Additional metadata to add to processing context
        """
        pass
        
    async def should_execute_hook(
        self,
        processing_result: Dict[str, Any],
        event_type: EventType
    ) -> bool:
        """
        Determine if hook should execute based on processing result.
        
        Args:
            processing_result: Result of event processing
            event_type: Type of event
            
        Returns:
            True if hook should execute
        """
        return True
        
    async def handle_processing_success(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        actions_executed: List[ActionId]
    ) -> None:
        """
        Handle successful event processing.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            actions_executed: List of actions that were executed
        """
        pass
        
    async def handle_processing_failure(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error_message: str,
        failed_actions: List[ActionId]
    ) -> None:
        """
        Handle failed event processing.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            error_message: Processing error message
            failed_actions: List of actions that failed
        """
        pass
        
    async def execute_hook(self, context: HookContext) -> HookResult:
        """
        Execute the post-processing hook.
        
        This method is called by the hook registry.
        
        Args:
            context: Hook execution context
            
        Returns:
            Hook execution result
        """
        try:
            # Extract processing result from metadata
            processing_result = context.metadata.get("processing_result", {})
            
            # Check if hook should execute
            should_execute = await self.should_execute_hook(
                processing_result,
                context.event_type
            )
            
            if not should_execute:
                return HookResult(
                    success=True,
                    continue_processing=True,
                    error_message=f"Hook {self.name} skipped based on conditions"
                )
                
            # Handle success or failure
            success = processing_result.get("success", False)
            if success:
                actions_executed = processing_result.get("actions_executed", [])
                action_ids = [ActionId(aid) for aid in actions_executed if isinstance(aid, str)]
                await self.handle_processing_success(
                    context.event_id,
                    context.tenant_id,
                    context.event_type,
                    action_ids
                )
            else:
                error_message = processing_result.get("error_message", "Unknown error")
                failed_actions = processing_result.get("failed_actions", [])
                action_ids = [ActionId(aid) for aid in failed_actions if isinstance(aid, str)]
                await self.handle_processing_failure(
                    context.event_id,
                    context.tenant_id,
                    context.event_type,
                    error_message,
                    action_ids
                )
                
            # Execute post-processing
            additional_metadata = await self.after_processing(
                context.event_id,
                context.tenant_id,
                context.event_type,
                context.event_data,
                processing_result,
                context.metadata
            )
            
            return HookResult(
                success=True,
                continue_processing=True,
                additional_metadata=additional_metadata
            )
            
        except Exception as e:
            return HookResult(
                success=False,
                continue_processing=True,  # Continue despite hook failure
                error_message=f"Post-processing hook failed: {str(e)}"
            )


class EventAuditHook(PostProcessHook):
    """
    Post-processing hook for event auditing.
    
    Logs event processing for compliance and monitoring.
    """
    
    @property
    def name(self) -> str:
        return "event_audit"
        
    @abstractmethod
    async def log_event_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        processing_result: Dict[str, Any],
        processing_time_ms: float
    ) -> None:
        """
        Log event processing for audit purposes.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            processing_result: Processing result
            processing_time_ms: Processing time in milliseconds
        """
        pass
        
    async def after_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        processing_result: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log event processing."""
        processing_start = metadata.get("processing_start_time", time.time())
        processing_time_ms = (time.time() - processing_start) * 1000
        
        await self.log_event_processing(
            event_id,
            tenant_id,
            event_type,
            processing_result,
            processing_time_ms
        )
        
        return {
            "audit_time": time.time(),
            "audited_by": self.name,
            "processing_time_ms": processing_time_ms,
        }


class EventNotificationHook(PostProcessHook):
    """
    Post-processing hook for event notifications.
    
    Sends notifications based on event processing results.
    """
    
    @property
    def name(self) -> str:
        return "event_notification"
        
    @abstractmethod
    async def send_success_notification(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        actions_executed: List[ActionId]
    ) -> None:
        """
        Send notification for successful event processing.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            actions_executed: List of executed actions
        """
        pass
        
    @abstractmethod
    async def send_failure_notification(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error_message: str,
        failed_actions: List[ActionId]
    ) -> None:
        """
        Send notification for failed event processing.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            error_message: Processing error message
            failed_actions: List of failed actions
        """
        pass
        
    async def handle_processing_success(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        actions_executed: List[ActionId]
    ) -> None:
        """Send success notification."""
        await self.send_success_notification(
            event_id,
            tenant_id,
            event_type,
            actions_executed
        )
        
    async def handle_processing_failure(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error_message: str,
        failed_actions: List[ActionId]
    ) -> None:
        """Send failure notification."""
        await self.send_failure_notification(
            event_id,
            tenant_id,
            event_type,
            error_message,
            failed_actions
        )
        
    async def after_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        processing_result: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add notification metadata."""
        return {
            "notification_time": time.time(),
            "notified_by": self.name,
            "notification_sent": True,
        }


class EventCleanupHook(PostProcessHook):
    """
    Post-processing hook for event cleanup.
    
    Performs cleanup operations after event processing.
    """
    
    @property
    def name(self) -> str:
        return "event_cleanup"
        
    @abstractmethod
    async def cleanup_temporary_resources(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType
    ) -> Dict[str, Any]:
        """
        Clean up temporary resources created during processing.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            
        Returns:
            Cleanup summary
        """
        pass
        
    @abstractmethod
    async def archive_event_data(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_data: Dict[str, Any],
        processing_result: Dict[str, Any]
    ) -> bool:
        """
        Archive event data for long-term storage.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_data: Event payload
            processing_result: Processing result
            
        Returns:
            True if archival was successful
        """
        pass
        
    async def should_execute_hook(
        self,
        processing_result: Dict[str, Any],
        event_type: EventType
    ) -> bool:
        """Execute cleanup regardless of processing result."""
        return True
        
    async def after_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        processing_result: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform cleanup operations."""
        # Clean up temporary resources
        cleanup_summary = await self.cleanup_temporary_resources(
            event_id,
            tenant_id,
            event_type
        )
        
        # Archive event data if processing was successful
        archived = False
        if processing_result.get("success", False):
            archived = await self.archive_event_data(
                event_id,
                tenant_id,
                event_data,
                processing_result
            )
            
        return {
            "cleanup_time": time.time(),
            "cleaned_by": self.name,
            "cleanup_summary": cleanup_summary,
            "archived": archived,
        }