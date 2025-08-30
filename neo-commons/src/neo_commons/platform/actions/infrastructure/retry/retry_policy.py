"""Retry policy implementation for action executions."""

import random
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class BackoffType(Enum):
    """Types of backoff strategies."""
    
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class RetryPolicy:
    """Configuration for action retry behavior."""
    
    max_retries: int
    backoff_type: BackoffType
    initial_delay_ms: int
    max_delay_ms: int = 60000  # 1 minute max
    jitter: bool = True
    retry_on_timeout: bool = True
    retry_on_handler_error: bool = True
    retry_on_system_error: bool = False  # Network, DB issues
    
    def __post_init__(self):
        """Validate retry policy parameters."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.initial_delay_ms < 0:
            raise ValueError("initial_delay_ms must be non-negative")
        if self.max_delay_ms < self.initial_delay_ms:
            raise ValueError("max_delay_ms must be >= initial_delay_ms")
    
    def calculate_delay(self, attempt: int) -> int:
        """
        Calculate delay for a retry attempt.
        
        Args:
            attempt: Attempt number (1-based)
            
        Returns:
            Delay in milliseconds
        """
        if attempt <= 0:
            return 0
        
        if self.backoff_type == BackoffType.EXPONENTIAL:
            delay = self.initial_delay_ms * (2 ** (attempt - 1))
        elif self.backoff_type == BackoffType.LINEAR:
            delay = self.initial_delay_ms * attempt
        else:  # FIXED
            delay = self.initial_delay_ms
        
        # Cap at max delay
        delay = min(delay, self.max_delay_ms)
        
        # Add jitter to prevent thundering herd
        if self.jitter and delay > 0:
            jitter_range = int(delay * 0.1)  # 10% jitter
            delay += random.randint(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def should_retry(self, attempt: int, error_type: str) -> bool:
        """
        Determine if an execution should be retried.
        
        Args:
            attempt: Current attempt number (1-based)
            error_type: Type of error that occurred
            
        Returns:
            True if should retry, False otherwise
        """
        # Check max retries
        if attempt > self.max_retries:
            return False
        
        # Check error type against retry policy
        if error_type == "timeout" and not self.retry_on_timeout:
            return False
        if error_type == "handler_error" and not self.retry_on_handler_error:
            return False
        if error_type == "system_error" and not self.retry_on_system_error:
            return False
        
        return True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetryPolicy":
        """Create retry policy from dictionary."""
        backoff_type = data.get("backoff_type", "exponential")
        if isinstance(backoff_type, str):
            backoff_type = BackoffType(backoff_type)
        
        return cls(
            max_retries=data.get("max_retries", 3),
            backoff_type=backoff_type,
            initial_delay_ms=data.get("initial_delay_ms", 1000),
            max_delay_ms=data.get("max_delay_ms", 60000),
            jitter=data.get("jitter", True),
            retry_on_timeout=data.get("retry_on_timeout", True),
            retry_on_handler_error=data.get("retry_on_handler_error", True),
            retry_on_system_error=data.get("retry_on_system_error", False)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert retry policy to dictionary."""
        return {
            "max_retries": self.max_retries,
            "backoff_type": self.backoff_type.value,
            "initial_delay_ms": self.initial_delay_ms,
            "max_delay_ms": self.max_delay_ms,
            "jitter": self.jitter,
            "retry_on_timeout": self.retry_on_timeout,
            "retry_on_handler_error": self.retry_on_handler_error,
            "retry_on_system_error": self.retry_on_system_error
        }


class RetryScheduler:
    """Scheduler for managing action retries."""
    
    def __init__(self):
        self._scheduled_retries: Dict[str, asyncio.Task] = {}
    
    async def schedule_retry(
        self,
        execution_id: str,
        retry_policy: RetryPolicy,
        attempt_number: int,
        retry_callback,
        *callback_args,
        **callback_kwargs
    ) -> bool:
        """
        Schedule a retry for an execution.
        
        Args:
            execution_id: Unique execution identifier
            retry_policy: Retry policy to follow
            attempt_number: Current attempt number (1-based)
            retry_callback: Function to call for retry
            *callback_args: Arguments for retry callback
            **callback_kwargs: Keyword arguments for retry callback
            
        Returns:
            True if retry was scheduled, False if no more retries
        """
        error_type = callback_kwargs.pop("error_type", "handler_error")
        
        # Check if retry should be attempted
        if not retry_policy.should_retry(attempt_number, error_type):
            return False
        
        # Calculate delay
        delay_ms = retry_policy.calculate_delay(attempt_number)
        
        # Cancel existing retry if any
        await self.cancel_retry(execution_id)
        
        # Schedule new retry
        task = asyncio.create_task(
            self._execute_delayed_retry(
                delay_ms / 1000.0,  # Convert to seconds
                retry_callback,
                *callback_args,
                **callback_kwargs
            )
        )
        
        self._scheduled_retries[execution_id] = task
        return True
    
    async def cancel_retry(self, execution_id: str) -> bool:
        """
        Cancel a scheduled retry.
        
        Args:
            execution_id: Execution ID to cancel
            
        Returns:
            True if retry was cancelled, False if no retry was scheduled
        """
        if execution_id in self._scheduled_retries:
            task = self._scheduled_retries.pop(execution_id)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            return True
        return False
    
    async def _execute_delayed_retry(self, delay_seconds: float, callback, *args, **kwargs):
        """Execute a retry after a delay."""
        try:
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            await callback(*args, **kwargs)
        except asyncio.CancelledError:
            raise  # Re-raise cancellation
        except Exception:
            # Log error but don't re-raise to prevent unhandled exceptions
            # TODO: Add proper logging
            pass
    
    def get_scheduled_count(self) -> int:
        """Get number of currently scheduled retries."""
        return len(self._scheduled_retries)
    
    def get_scheduled_executions(self) -> list[str]:
        """Get list of execution IDs with scheduled retries."""
        return list(self._scheduled_retries.keys())
    
    async def shutdown(self):
        """Cancel all scheduled retries and shutdown."""
        for execution_id in list(self._scheduled_retries.keys()):
            await self.cancel_retry(execution_id)


class ErrorClassifier:
    """Classifier for different types of errors."""
    
    TIMEOUT_ERRORS = [
        "TimeoutError",
        "asyncio.TimeoutError",
        "concurrent.futures.TimeoutError"
    ]
    
    SYSTEM_ERRORS = [
        "ConnectionError",
        "ConnectionRefusedError", 
        "ConnectionResetError",
        "ConnectionAbortedError",
        "NetworkError",
        "DNSError",
        "psycopg.OperationalError",
        "redis.ConnectionError"
    ]
    
    HANDLER_ERRORS = [
        "ValueError",
        "TypeError",
        "AttributeError",
        "KeyError",
        "IndexError",
        "ValidationError"
    ]
    
    @classmethod
    def classify_error(cls, exception: Exception) -> str:
        """
        Classify an exception into error type categories.
        
        Args:
            exception: Exception to classify
            
        Returns:
            Error type string: "timeout", "system_error", "handler_error", or "unknown"
        """
        exception_name = type(exception).__name__
        exception_full_name = f"{type(exception).__module__}.{exception_name}"
        
        # Check for timeout errors
        if exception_name in cls.TIMEOUT_ERRORS or exception_full_name in cls.TIMEOUT_ERRORS:
            return "timeout"
        
        # Check for system errors
        if exception_name in cls.SYSTEM_ERRORS or exception_full_name in cls.SYSTEM_ERRORS:
            return "system_error"
        
        # Check for handler errors
        if exception_name in cls.HANDLER_ERRORS or exception_full_name in cls.HANDLER_ERRORS:
            return "handler_error"
        
        # Default to handler error for unknown exceptions
        return "handler_error"


# Default retry policies
DEFAULT_RETRY_POLICIES = {
    "default": RetryPolicy(
        max_retries=3,
        backoff_type=BackoffType.EXPONENTIAL,
        initial_delay_ms=1000,
        max_delay_ms=30000,
        jitter=True
    ),
    
    "aggressive": RetryPolicy(
        max_retries=5,
        backoff_type=BackoffType.EXPONENTIAL,
        initial_delay_ms=500,
        max_delay_ms=60000,
        jitter=True
    ),
    
    "conservative": RetryPolicy(
        max_retries=2,
        backoff_type=BackoffType.LINEAR,
        initial_delay_ms=2000,
        max_delay_ms=10000,
        jitter=False
    ),
    
    "no_retry": RetryPolicy(
        max_retries=0,
        backoff_type=BackoffType.FIXED,
        initial_delay_ms=0,
        max_delay_ms=0,
        jitter=False
    )
}