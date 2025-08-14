"""
Metadata collection utilities for API responses.
Enhanced for neo-commons with configurable tracking and better integration.
"""

import time
from typing import Dict, Any, Optional, Callable, Union
from contextvars import ContextVar
from datetime import datetime
from functools import wraps

# Performance-tracking context variables
db_query_count: ContextVar[int] = ContextVar('db_query_count', default=0)
cache_hit_count: ContextVar[int] = ContextVar('cache_hit_count', default=0)
cache_miss_count: ContextVar[int] = ContextVar('cache_miss_count', default=0)
cache_set_count: ContextVar[int] = ContextVar('cache_set_count', default=0)
request_start_time: ContextVar[Optional[float]] = ContextVar('request_start_time', default=None)


class MetadataCollector:
    """Lightweight metadata collection for performance and request tracking."""
    
    @staticmethod
    def reset_counters():
        """Reset performance counters for new request."""
        db_query_count.set(0)
        cache_hit_count.set(0)
        cache_miss_count.set(0)
        cache_set_count.set(0)
        request_start_time.set(time.time())
    
    @staticmethod
    def increment_db_queries(count: int = 1):
        """Track database query execution."""
        current = db_query_count.get()
        db_query_count.set(current + count)
    
    @staticmethod
    def increment_cache_hits(count: int = 1):
        """Track cache hit."""
        current = cache_hit_count.get()
        cache_hit_count.set(current + count)
    
    @staticmethod
    def increment_cache_misses(count: int = 1):
        """Track cache miss."""
        current = cache_miss_count.get()
        cache_miss_count.set(current + count)
    
    @staticmethod
    def increment_cache_sets(count: int = 1):
        """Track cache set operation."""
        current = cache_set_count.get()
        cache_set_count.set(current + count)
    
    @staticmethod
    def get_request_duration() -> Optional[float]:
        """Get request duration in milliseconds if available."""
        start_time = request_start_time.get()
        if start_time is not None:
            return (time.time() - start_time) * 1000
        return None
    
    @staticmethod
    def get_performance_metadata(include_timing: bool = True) -> Dict[str, Any]:
        """
        Get performance metadata from current request context.
        
        Args:
            include_timing: Whether to include request timing information
            
        Returns:
            Dict[str, Any]: Performance metadata
        """
        db_queries = db_query_count.get()
        cache_hits = cache_hit_count.get()
        cache_misses = cache_miss_count.get()
        cache_sets = cache_set_count.get()
        
        metadata = {}
        
        # Database performance
        if db_queries > 0:
            metadata['db_queries'] = db_queries
        
        # Cache performance
        total_cache_ops = cache_hits + cache_misses
        if total_cache_ops > 0:
            cache_data = {
                'hit_rate': round((cache_hits / total_cache_ops) * 100, 1),
                'hits': cache_hits,
                'misses': cache_misses
            }
            if cache_sets > 0:
                cache_data['sets'] = cache_sets
            metadata['cache'] = cache_data
        
        # Request timing
        if include_timing:
            duration = MetadataCollector.get_request_duration()
            if duration is not None:
                metadata['request_duration_ms'] = round(duration, 2)
        
        return metadata
    
    @staticmethod
    def collect_request_metadata(
        include_performance: bool = True,
        include_timing: bool = True,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Collect comprehensive metadata with error handling.
        
        Args:
            include_performance: Whether to include performance counters
            include_timing: Whether to include timing information
            custom_metadata: Additional metadata to include
            
        Returns:
            Dict[str, Any]: Complete metadata or empty dict if collection fails
        """
        try:
            from neo_commons.utils.datetime import utc_now
            
            metadata = {}
            
            # Add timestamp
            metadata['timestamp'] = utc_now().isoformat()
            
            # Add performance data if enabled
            if include_performance:
                perf_data = MetadataCollector.get_performance_metadata(include_timing)
                if perf_data:
                    metadata.update(perf_data)
            
            # Add custom metadata
            if custom_metadata:
                metadata.update(custom_metadata)
            
            return metadata
            
        except Exception:
            # Never fail response due to metadata collection
            return {}
    
    @staticmethod
    def get_context_metadata(
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create context metadata dictionary.
        
        Args:
            request_id: Request identifier
            user_id: User identifier
            tenant_id: Tenant identifier
            session_id: Session identifier
            
        Returns:
            Dict[str, Any]: Context metadata
        """
        metadata = {}
        
        if request_id:
            metadata['request_id'] = request_id
        
        if user_id:
            metadata['user_id'] = user_id
        
        if tenant_id:
            metadata['tenant_id'] = tenant_id
        
        if session_id:
            metadata['session_id'] = session_id
        
        return metadata


class PerformanceTracker:
    """Context manager for tracking operation performance."""
    
    def __init__(self, operation_name: str, track_as_db: bool = False):
        """
        Initialize performance tracker.
        
        Args:
            operation_name: Name of the operation being tracked
            track_as_db: Whether to count this as a database operation
        """
        self.operation_name = operation_name
        self.track_as_db = track_as_db
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None
    
    def __enter__(self):
        """Start timing the operation."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record the operation."""
        if self.start_time is not None:
            self.duration = (time.time() - self.start_time) * 1000
            
            if self.track_as_db:
                MetadataCollector.increment_db_queries()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)
    
    def get_duration(self) -> Optional[float]:
        """Get operation duration in milliseconds."""
        return self.duration


# Decorator for tracking database operations
def track_db_operation(func: Optional[Callable] = None, *, count: int = 1):
    """
    Decorator to track database operations.
    
    Args:
        func: Function to wrap (when used without parameters)
        count: Number of queries this operation represents
    """
    def decorator(f: Callable) -> Callable:
        if hasattr(f, '__code__') and f.__code__.co_flags & 0x80:  # Async function
            @wraps(f)
            async def async_wrapper(*args, **kwargs):
                MetadataCollector.increment_db_queries(count)
                return await f(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(f)
            def sync_wrapper(*args, **kwargs):
                MetadataCollector.increment_db_queries(count)
                return f(*args, **kwargs)
            return sync_wrapper
    
    if func is None:
        # Used with parameters: @track_db_operation(count=2)
        return decorator
    else:
        # Used without parameters: @track_db_operation
        return decorator(func)


def track_cache_operation_decorator(operation: str):
    """
    Decorator factory for tracking cache operations.
    
    Args:
        operation: Type of operation ('hit', 'miss', 'set')
    """
    def decorator(func: Callable) -> Callable:
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # Async function
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                track_cache_operation(operation)
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                track_cache_operation(operation)
                return result
            return sync_wrapper
    return decorator


# Helper functions for easy integration
def get_api_metadata(
    include_performance: bool = True,
    include_timing: bool = True,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive metadata for API responses.
    
    Args:
        include_performance: Whether to include performance metrics
        include_timing: Whether to include timing information
        request_id: Request identifier
        user_id: User identifier
        tenant_id: Tenant identifier
        
    Returns:
        Dict[str, Any]: Complete metadata
    """
    # Get base metadata
    metadata = MetadataCollector.collect_request_metadata(
        include_performance=include_performance,
        include_timing=include_timing
    )
    
    # Add context if provided
    context = MetadataCollector.get_context_metadata(
        request_id=request_id,
        user_id=user_id,
        tenant_id=tenant_id
    )
    metadata.update(context)
    
    return metadata


def track_cache_operation(operation: str, count: int = 1):
    """
    Track cache operations by type.
    
    Args:
        operation: Type of operation ('hit', 'miss', 'set')
        count: Number of operations
    """
    if operation == 'hit':
        MetadataCollector.increment_cache_hits(count)
    elif operation == 'miss':
        MetadataCollector.increment_cache_misses(count)
    elif operation == 'set':
        MetadataCollector.increment_cache_sets(count)


def create_operation_metadata(
    operation_name: str,
    success: bool,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create metadata for a specific operation.
    
    Args:
        operation_name: Name of the operation
        success: Whether the operation succeeded
        duration_ms: Operation duration in milliseconds
        error: Error message if operation failed
        **kwargs: Additional metadata
        
    Returns:
        Dict[str, Any]: Operation metadata
    """
    from neo_commons.utils.datetime import utc_now
    
    metadata = {
        'operation': operation_name,
        'success': success,
        'timestamp': utc_now().isoformat()
    }
    
    if duration_ms is not None:
        metadata['duration_ms'] = round(duration_ms, 2)
    
    if error:
        metadata['error'] = error
    
    metadata.update(kwargs)
    return metadata


def get_cache_statistics() -> Dict[str, Any]:
    """
    Get current cache statistics.
    
    Returns:
        Dict[str, Any]: Cache statistics
    """
    hits = cache_hit_count.get()
    misses = cache_miss_count.get()
    sets = cache_set_count.get()
    
    total_ops = hits + misses
    
    stats = {
        'hits': hits,
        'misses': misses,
        'sets': sets,
        'total_reads': total_ops
    }
    
    if total_ops > 0:
        stats['hit_rate'] = round((hits / total_ops) * 100, 1)
    else:
        stats['hit_rate'] = 0.0
    
    return stats


def reset_all_counters():
    """Reset all performance counters."""
    MetadataCollector.reset_counters()


# Context manager aliases for convenience
track_performance = PerformanceTracker