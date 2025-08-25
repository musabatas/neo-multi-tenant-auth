"""Standardized error handling utilities for organization operations.

Provides decorators, context managers, and utilities for consistent error handling
across all organization feature components following DRY principles.
"""

import logging
import functools
from functools import wraps
from typing import Callable, Any, Optional, Dict, Union
from datetime import datetime

from ....core.exceptions import (
    OrganizationNotFoundError,
    EntityAlreadyExistsError,
    ValidationError
)

logger = logging.getLogger(__name__)


def organization_error_handler(
    operation_name: str,
    log_level: int = logging.ERROR,
    reraise: bool = True,
    default_return: Any = None,
    context_fields: Optional[Dict[str, str]] = None
):
    """Decorator for standardized organization error handling.
    
    Args:
        operation_name: Name of the operation for logging
        log_level: Logging level (default: ERROR)
        reraise: Whether to re-raise the exception (default: True)
        default_return: Default return value if not re-raising
        context_fields: Additional context fields for logging
        
    Usage:
        @organization_error_handler("organization creation")
        async def create_org(request):
            ...
            
        @organization_error_handler("get organization", reraise=False, default_return=None)
        async def get_organization_optional(org_id):
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
            
            # Extract context from function arguments
            if args:
                first_arg = args[0]
                # Try to extract organization context
                if hasattr(first_arg, 'id'):
                    operation_context["organization_id"] = str(first_arg.id)
                elif hasattr(first_arg, 'slug'):
                    operation_context["organization_slug"] = first_arg.slug
                elif hasattr(first_arg, 'name'):
                    operation_context["organization_name"] = first_arg.name
            
            # Check for organization ID in kwargs
            for key in ['organization_id', 'org_id', 'id']:
                if key in kwargs:
                    operation_context["organization_id"] = str(kwargs[key])
                    break
            
            try:
                result = await func(*args, **kwargs)
                return result
                
            except (OrganizationNotFoundError, EntityAlreadyExistsError, ValidationError) as e:
                # Domain exceptions - log at info level and re-raise
                context_str = ", ".join(f"{k}={v}" for k, v in operation_context.items())
                logger.info(f"Domain exception in {operation_name}: {e} | Context: {context_str}")
                
                if reraise:
                    raise
                else:
                    return default_return
                    
            except Exception as e:
                # Unexpected exceptions - log at error level
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


def log_organization_operation(
    operation_name: str,
    log_level: int = logging.DEBUG,
    include_args: bool = False,
    include_timing: bool = False,
    include_result_summary: bool = False
):
    """Decorator for logging organization operations.
    
    Args:
        operation_name: Name of the operation for logging
        log_level: Logging level (default: DEBUG)
        include_args: Whether to include function arguments in logs
        include_timing: Whether to include execution timing
        include_result_summary: Whether to include result summary
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = datetime.utcnow() if include_timing else None
            
            # Build log context
            log_context = {"operation": operation_name, "function": func.__name__}
            
            # Extract organization context
            if args:
                first_arg = args[0]
                if hasattr(first_arg, 'id'):
                    log_context["organization_id"] = str(first_arg.id)
                elif hasattr(first_arg, 'slug'):
                    log_context["organization_slug"] = first_arg.slug
                elif hasattr(first_arg, 'name'):
                    log_context["organization_name"] = first_arg.name
            
            # Check for organization ID in kwargs
            for key in ['organization_id', 'org_id', 'id']:
                if key in kwargs:
                    log_context["organization_id"] = str(kwargs[key])
                    break
            
            # Add arguments if requested
            if include_args and (args or kwargs):
                log_context["args"] = f"args={len(args)}, kwargs={list(kwargs.keys())}"
            
            logger.log(log_level, f"Starting {operation_name} | {log_context}")
            
            try:
                result = await func(*args, **kwargs)
                
                # Add timing if requested
                if include_timing and start_time:
                    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    log_context["duration_ms"] = f"{duration_ms:.2f}"
                
                # Add result summary if requested
                if include_result_summary and result:
                    if hasattr(result, 'id'):
                        log_context["result_id"] = str(result.id)
                    elif isinstance(result, list):
                        log_context["result_count"] = len(result)
                    elif isinstance(result, dict) and 'total' in result:
                        log_context["result_total"] = result['total']
                
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


class OrganizationOperationContext:
    """Context manager for organization operations with standardized logging and error handling."""
    
    def __init__(
        self,
        operation_name: str,
        organization_id: Optional[str] = None,
        organization_slug: Optional[str] = None,
        log_level: int = logging.DEBUG,
        track_timing: bool = True
    ):
        self.operation_name = operation_name
        self.organization_id = organization_id
        self.organization_slug = organization_slug
        self.log_level = log_level
        self.track_timing = track_timing
        self.start_time: Optional[datetime] = None
        self.context: Dict[str, Any] = {
            "operation": operation_name,
            "organization_id": organization_id,
            "organization_slug": organization_slug
        }
        
        # Remove None values
        self.context = {k: v for k, v in self.context.items() if v is not None}
    
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
            self.context["error_type"] = exc_type.__name__
            logger.error(f"Failed {self.operation_name} | {self.context}")
        else:
            logger.log(self.log_level, f"Completed {self.operation_name} | {self.context}")
    
    def add_context(self, key: str, value: Any):
        """Add additional context information."""
        self.context[key] = value
        
    def set_organization_context(self, organization):
        """Set organization context from an organization entity."""
        if hasattr(organization, 'id'):
            self.context["organization_id"] = str(organization.id)
        if hasattr(organization, 'slug'):
            self.context["organization_slug"] = organization.slug
        if hasattr(organization, 'name'):
            self.context["organization_name"] = organization.name


def format_organization_error(
    operation: str,
    error: Exception,
    organization_id: Optional[str] = None,
    organization_slug: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """Format organization error message with consistent structure.
    
    Args:
        operation: Name of the operation that failed
        error: The exception that occurred
        organization_id: Organization ID if available
        organization_slug: Organization slug if available
        additional_context: Additional context information
        
    Returns:
        Formatted error message
    """
    context_parts = []
    
    if organization_id:
        context_parts.append(f"organization_id={organization_id}")
    
    if organization_slug:
        context_parts.append(f"organization_slug={organization_slug}")
    
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
def handle_organization_creation_error(func: Callable) -> Callable:
    """Decorator specifically for organization creation errors."""
    return organization_error_handler(
        "organization creation", 
        reraise=True,
        context_fields={"operation_type": "create"}
    )(func)


def handle_organization_retrieval_error(func: Callable) -> Callable:
    """Decorator specifically for organization retrieval errors."""
    return organization_error_handler(
        "retrieve organization", 
        reraise=True,
        context_fields={"operation_type": "retrieve"}
    )(func)


def handle_organization_update_error(func: Callable) -> Callable:
    """Decorator specifically for organization update errors."""
    return organization_error_handler(
        "update organization", 
        reraise=True,
        context_fields={"operation_type": "update"}
    )(func)


def handle_organization_deletion_error(func: Callable) -> Callable:
    """Decorator specifically for organization deletion errors."""
    return organization_error_handler(
        "delete organization", 
        reraise=True,
        context_fields={"operation_type": "delete"}
    )(func)


def handle_organization_search_error(func: Callable) -> Callable:
    """Decorator specifically for organization search errors with non-raising behavior."""
    return organization_error_handler(
        "search organizations", 
        reraise=False, 
        default_return=[],
        log_level=logging.WARNING,
        context_fields={"operation_type": "search"}
    )(func)


def handle_organization_validation_error(func: Callable) -> Callable:
    """Decorator specifically for organization validation errors."""
    return organization_error_handler(
        "validate organization", 
        reraise=True,
        context_fields={"operation_type": "validation"}
    )(func)


def handle_organization_stats_error(func: Callable) -> Callable:
    """Decorator specifically for organization statistics errors with non-raising behavior."""
    return organization_error_handler(
        "generate organization statistics", 
        reraise=False, 
        default_return={},
        log_level=logging.WARNING,
        context_fields={"operation_type": "statistics"}
    )(func)


def handle_organization_service_errors(func: Callable) -> Callable:
    """Generic service error handler for organization operations."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Service error in {func.__name__}: {e}")
            raise
    return wrapper


def handle_organization_cache_error(func: Callable) -> Callable:
    """Decorator specifically for organization cache errors with non-raising behavior."""
    return organization_error_handler(
        "organization cache operation", 
        reraise=False, 
        default_return=None,
        log_level=logging.WARNING,
        context_fields={"operation_type": "cache"}
    )(func)