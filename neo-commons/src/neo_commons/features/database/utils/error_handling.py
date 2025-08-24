"""Standardized error handling utilities for database operations."""

import logging
import functools
from typing import Callable, Any, Optional, Dict, Union
from datetime import datetime

logger = logging.getLogger(__name__)


def database_error_handler(
    operation_name: str,
    log_level: int = logging.ERROR,
    reraise: bool = True,
    default_return: Any = None,
    context_fields: Optional[Dict[str, str]] = None
):
    """Decorator for standardized database error handling.
    
    Args:
        operation_name: Name of the operation for logging
        log_level: Logging level (default: ERROR)
        reraise: Whether to re-raise the exception (default: True)
        default_return: Default return value if not re-raising
        context_fields: Additional context fields for logging
        
    Usage:
        @database_error_handler("connection creation")
        async def create_connection():
            ...
            
        @database_error_handler("health check", reraise=False, default_return=False)
        async def health_check():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            operation_context = {
                "operation": operation_name,
                "timestamp": datetime.utcnow().isoformat(),
                "function": func.__name__,
            }
            
            # Add custom context fields
            if context_fields:
                operation_context.update(context_fields)
            
            # Extract context from function arguments if available
            if args:
                # Try to extract connection name from first argument
                first_arg = args[0]
                if hasattr(first_arg, 'connection_name'):
                    operation_context["connection_name"] = first_arg.connection_name
                elif hasattr(first_arg, 'name'):
                    operation_context["connection_name"] = first_arg.name
            
            try:
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                # Log the error with context
                context_str = ", ".join(f"{k}={v}" for k, v in operation_context.items())
                logger.log(
                    log_level,
                    f"Failed to {operation_name}: {e} | Context: {context_str}"
                )
                
                if reraise:
                    raise
                else:
                    return default_return
        
        return wrapper
    return decorator


def log_database_operation(
    operation_name: str,
    log_level: int = logging.DEBUG,
    include_args: bool = False,
    include_timing: bool = False
):
    """Decorator for logging database operations.
    
    Args:
        operation_name: Name of the operation for logging
        log_level: Logging level (default: DEBUG)
        include_args: Whether to include function arguments in logs
        include_timing: Whether to include execution timing
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = datetime.utcnow() if include_timing else None
            
            # Build log context
            log_context = {"operation": operation_name, "function": func.__name__}
            
            # Extract connection name if available
            if args:
                first_arg = args[0]
                if hasattr(first_arg, 'connection_name'):
                    log_context["connection_name"] = first_arg.connection_name
                elif hasattr(first_arg, 'name'):
                    log_context["connection_name"] = first_arg.name
            
            # Add arguments if requested
            if include_args and (args or kwargs):
                log_context["args"] = f"args={len(args)}, kwargs={list(kwargs.keys())}"
            
            logger.log(log_level, f"Starting {operation_name} | {log_context}")
            
            try:
                result = await func(*args, **kwargs)
                
                if include_timing and start_time:
                    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    log_context["duration_ms"] = f"{duration_ms:.2f}"
                
                logger.log(log_level, f"Completed {operation_name} | {log_context}")
                return result
                
            except Exception as e:
                if include_timing and start_time:
                    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    log_context["duration_ms"] = f"{duration_ms:.2f}"
                
                log_context["error"] = str(e)
                logger.log(logging.ERROR, f"Failed {operation_name} | {log_context}")
                raise
        
        return wrapper
    return decorator


class DatabaseOperationContext:
    """Context manager for database operations with standardized logging and error handling."""
    
    def __init__(
        self,
        operation_name: str,
        connection_name: Optional[str] = None,
        log_level: int = logging.DEBUG,
        track_timing: bool = True
    ):
        self.operation_name = operation_name
        self.connection_name = connection_name
        self.log_level = log_level
        self.track_timing = track_timing
        self.start_time: Optional[datetime] = None
        self.context: Dict[str, Any] = {
            "operation": operation_name,
            "connection_name": connection_name
        }
    
    async def __aenter__(self):
        self.start_time = datetime.utcnow() if self.track_timing else None
        logger.log(self.log_level, f"Starting {self.operation_name} | {self.context}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.track_timing and self.start_time:
            duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
            self.context["duration_ms"] = f"{duration_ms:.2f}"
        
        if exc_type:
            self.context["error"] = str(exc_val)
            logger.error(f"Failed {self.operation_name} | {self.context}")
        else:
            logger.log(self.log_level, f"Completed {self.operation_name} | {self.context}")
    
    def add_context(self, key: str, value: Any):
        """Add additional context information."""
        self.context[key] = value


def format_database_error(
    operation: str,
    error: Exception,
    connection_name: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """Format database error message with consistent structure.
    
    Args:
        operation: Name of the operation that failed
        error: The exception that occurred
        connection_name: Name of the database connection
        additional_context: Additional context information
        
    Returns:
        Formatted error message
    """
    context_parts = []
    
    if connection_name:
        context_parts.append(f"connection={connection_name}")
    
    if additional_context:
        for key, value in additional_context.items():
            context_parts.append(f"{key}={value}")
    
    context_str = " | ".join(context_parts)
    base_message = f"Failed to {operation}: {error}"
    
    if context_str:
        return f"{base_message} | {context_str}"
    else:
        return base_message


# Utility functions for common error patterns
def handle_connection_error(func: Callable) -> Callable:
    """Decorator specifically for connection-related errors."""
    return database_error_handler("establish connection", reraise=True)(func)


def handle_query_error(func: Callable) -> Callable:
    """Decorator specifically for query execution errors."""
    return database_error_handler("execute query", reraise=True)(func)


def handle_health_check_error(func: Callable) -> Callable:
    """Decorator specifically for health check errors with non-raising behavior."""
    return database_error_handler(
        "perform health check", 
        reraise=False, 
        default_return=False,
        log_level=logging.WARNING
    )(func)