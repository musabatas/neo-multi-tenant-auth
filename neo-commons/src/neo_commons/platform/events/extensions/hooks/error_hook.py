"""
Error handling hook implementation.

ONLY handles error lifecycle hooks for events.
"""

import time
import traceback
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from enum import Enum

from .event_hook_registry import HookContext, HookResult
from ....core.value_objects import EventId, TenantId, EventType
from .....actions.core.value_objects import ActionId  # Import from platform/actions module


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""
    VALIDATION = "validation"
    PROCESSING = "processing"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ErrorHook(ABC):
    """
    Abstract base class for error handling hooks.
    
    Executed when errors occur during event processing.
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
    async def handle_error(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error: Exception,
        error_context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle an error that occurred during event processing.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            error: Exception that occurred
            error_context: Context where error occurred
            metadata: Processing metadata
            
        Returns:
            Additional metadata about error handling
        """
        pass
        
    async def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize the error type.
        
        Args:
            error: Exception that occurred
            
        Returns:
            Error category
        """
        error_type = type(error).__name__.lower()
        
        if "validation" in error_type or "invalid" in error_type:
            return ErrorCategory.VALIDATION
        elif "timeout" in error_type:
            return ErrorCategory.TIMEOUT
        elif "connection" in error_type or "network" in error_type:
            return ErrorCategory.NETWORK
        elif "auth" in error_type:
            return ErrorCategory.AUTHENTICATION
        elif "permission" in error_type or "forbidden" in error_type:
            return ErrorCategory.AUTHORIZATION
        elif "rate" in error_type or "limit" in error_type:
            return ErrorCategory.RATE_LIMIT
        elif "database" in error_type or "sql" in error_type:
            return ErrorCategory.DATABASE
        else:
            return ErrorCategory.UNKNOWN
            
    async def determine_severity(
        self,
        error: Exception,
        error_context: Dict[str, Any]
    ) -> ErrorSeverity:
        """
        Determine the severity of the error.
        
        Args:
            error: Exception that occurred
            error_context: Context where error occurred
            
        Returns:
            Error severity level
        """
        category = await self.categorize_error(error)
        
        # Critical errors that affect system operation
        if category in [ErrorCategory.DATABASE, ErrorCategory.AUTHENTICATION]:
            return ErrorSeverity.CRITICAL
            
        # High severity errors that affect functionality
        if category in [ErrorCategory.EXTERNAL_SERVICE, ErrorCategory.AUTHORIZATION]:
            return ErrorSeverity.HIGH
            
        # Medium severity errors that can be retried
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.RATE_LIMIT]:
            return ErrorSeverity.MEDIUM
            
        # Low severity errors
        return ErrorSeverity.LOW
        
    async def should_retry_after_error(
        self,
        error: Exception,
        error_context: Dict[str, Any],
        retry_count: int
    ) -> bool:
        """
        Determine if processing should be retried after error.
        
        Args:
            error: Exception that occurred
            error_context: Context where error occurred
            retry_count: Current retry count
            
        Returns:
            True if processing should be retried
        """
        category = await self.categorize_error(error)
        max_retries = 3
        
        # Don't retry validation errors
        if category == ErrorCategory.VALIDATION:
            return False
            
        # Don't retry authentication/authorization errors
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return False
            
        # Retry network/timeout/rate limit errors up to limit
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.RATE_LIMIT]:
            return retry_count < max_retries
            
        # Retry external service errors with limited attempts
        if category == ErrorCategory.EXTERNAL_SERVICE:
            return retry_count < 2
            
        return False
        
    async def execute_hook(self, context: HookContext) -> HookResult:
        """
        Execute the error handling hook.
        
        This method is called by the hook registry.
        
        Args:
            context: Hook execution context
            
        Returns:
            Hook execution result
        """
        try:
            # Extract error information from metadata
            error_info = context.metadata.get("error_info", {})
            error_message = error_info.get("error_message", "Unknown error")
            error_context = error_info.get("error_context", {})
            
            # Create a generic exception for handling
            error = Exception(error_message)
            
            # Handle the error
            additional_metadata = await self.handle_error(
                context.event_id,
                context.tenant_id,
                context.event_type,
                error,
                error_context,
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
                continue_processing=True,
                error_message=f"Error hook failed: {str(e)}"
            )


class ErrorLoggingHook(ErrorHook):
    """
    Error hook for logging errors.
    
    Logs errors with appropriate detail and context.
    """
    
    @property
    def name(self) -> str:
        return "error_logging"
        
    @abstractmethod
    async def log_error(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error: Exception,
        severity: ErrorSeverity,
        category: ErrorCategory,
        error_context: Dict[str, Any]
    ) -> None:
        """
        Log error with appropriate detail.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            error: Exception that occurred
            severity: Error severity
            category: Error category
            error_context: Context where error occurred
        """
        pass
        
    async def handle_error(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error: Exception,
        error_context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Log the error."""
        severity = await self.determine_severity(error, error_context)
        category = await self.categorize_error(error)
        
        await self.log_error(
            event_id,
            tenant_id,
            event_type,
            error,
            severity,
            category,
            error_context
        )
        
        return {
            "error_logged_time": time.time(),
            "logged_by": self.name,
            "error_severity": severity.value,
            "error_category": category.value,
            "stack_trace": traceback.format_exc(),
        }


class ErrorNotificationHook(ErrorHook):
    """
    Error hook for sending error notifications.
    
    Sends notifications for critical errors.
    """
    
    @property
    def name(self) -> str:
        return "error_notification"
        
    @abstractmethod
    async def send_error_notification(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error: Exception,
        severity: ErrorSeverity,
        category: ErrorCategory
    ) -> None:
        """
        Send error notification.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            error: Exception that occurred
            severity: Error severity
            category: Error category
        """
        pass
        
    async def should_send_notification(
        self,
        severity: ErrorSeverity,
        category: ErrorCategory
    ) -> bool:
        """
        Determine if notification should be sent.
        
        Args:
            severity: Error severity
            category: Error category
            
        Returns:
            True if notification should be sent
        """
        # Send notifications for critical and high severity errors
        return severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]
        
    async def handle_error(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error: Exception,
        error_context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send error notification if needed."""
        severity = await self.determine_severity(error, error_context)
        category = await self.categorize_error(error)
        
        notification_sent = False
        if await self.should_send_notification(severity, category):
            await self.send_error_notification(
                event_id,
                tenant_id,
                event_type,
                error,
                severity,
                category
            )
            notification_sent = True
            
        return {
            "error_notification_time": time.time(),
            "notified_by": self.name,
            "notification_sent": notification_sent,
            "error_severity": severity.value,
            "error_category": category.value,
        }


class ErrorRecoveryHook(ErrorHook):
    """
    Error hook for error recovery.
    
    Attempts to recover from errors and retry processing.
    """
    
    @property
    def name(self) -> str:
        return "error_recovery"
        
    @abstractmethod
    async def attempt_recovery(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error: Exception,
        error_context: Dict[str, Any]
    ) -> bool:
        """
        Attempt to recover from error.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            error: Exception that occurred
            error_context: Context where error occurred
            
        Returns:
            True if recovery was successful
        """
        pass
        
    async def calculate_retry_delay(
        self,
        retry_count: int,
        error_category: ErrorCategory
    ) -> int:
        """
        Calculate delay before retry.
        
        Args:
            retry_count: Current retry count
            error_category: Category of error
            
        Returns:
            Delay in seconds
        """
        base_delay = 1
        
        # Exponential backoff for most errors
        if error_category in [ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_SERVICE]:
            return min(base_delay * (2 ** retry_count), 60)
            
        # Longer delay for rate limit errors
        if error_category == ErrorCategory.RATE_LIMIT:
            return min(base_delay * (3 ** retry_count), 300)
            
        return base_delay
        
    async def handle_error(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        error: Exception,
        error_context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt error recovery."""
        recovery_attempted = False
        recovery_successful = False
        should_retry = False
        retry_delay = 0
        
        retry_count = error_context.get("retry_count", 0)
        category = await self.categorize_error(error)
        
        # Attempt recovery
        if retry_count == 0:  # Only attempt recovery on first error
            recovery_attempted = True
            recovery_successful = await self.attempt_recovery(
                event_id,
                tenant_id,
                event_type,
                error,
                error_context
            )
            
        # Determine if should retry
        if not recovery_successful:
            should_retry = await self.should_retry_after_error(
                error,
                error_context,
                retry_count
            )
            
            if should_retry:
                retry_delay = await self.calculate_retry_delay(retry_count, category)
                
        return {
            "error_recovery_time": time.time(),
            "recovered_by": self.name,
            "recovery_attempted": recovery_attempted,
            "recovery_successful": recovery_successful,
            "should_retry": should_retry,
            "retry_delay_seconds": retry_delay,
            "error_category": category.value,
        }