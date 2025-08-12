"""
Metadata collection utilities for API responses.
Leverages existing middleware infrastructure for minimal performance impact.
"""

import time
from typing import Dict, Any, Optional
from contextvars import ContextVar

# Performance-tracking context variables
db_query_count: ContextVar[int] = ContextVar('db_query_count', default=0)
cache_hit_count: ContextVar[int] = ContextVar('cache_hit_count', default=0)
cache_miss_count: ContextVar[int] = ContextVar('cache_miss_count', default=0)
cache_set_count: ContextVar[int] = ContextVar('cache_set_count', default=0)


class MetadataCollector:
    """Lightweight metadata collection without additional middleware overhead."""
    
    @staticmethod
    def reset_counters():
        """Reset performance counters for new request."""
        db_query_count.set(0)
        cache_hit_count.set(0)
        cache_miss_count.set(0)
        cache_set_count.set(0)
    
    @staticmethod
    def increment_db_queries():
        """Track database query execution."""
        current = db_query_count.get()
        db_query_count.set(current + 1)
    
    @staticmethod
    def increment_cache_hits():
        """Track cache hit."""
        current = cache_hit_count.get()
        cache_hit_count.set(current + 1)
    
    @staticmethod
    def increment_cache_misses():
        """Track cache miss."""
        current = cache_miss_count.get()
        cache_miss_count.set(current + 1)
    
    @staticmethod
    def increment_cache_sets():
        """Track cache set operation."""
        current = cache_set_count.get()
        cache_set_count.set(current + 1)
    
    @staticmethod
    def get_performance_metadata() -> Dict[str, Any]:
        """Get performance metadata from current request context."""
        db_queries = db_query_count.get()
        cache_hits = cache_hit_count.get()
        cache_misses = cache_miss_count.get()
        cache_sets = cache_set_count.get()
        
        metadata = {}
        
        # Only include non-zero counters to minimize payload
        if db_queries > 0:
            metadata['db_queries'] = db_queries
        
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
        
        return metadata
    
    @staticmethod
    def collect_request_metadata(include_performance: bool = True) -> Dict[str, Any]:
        """
        Collect comprehensive metadata from existing middleware.
        
        Args:
            include_performance: Whether to include performance counters
            
        Returns:
            Dictionary with metadata or empty dict if collection fails
        """
        try:
            # Import here to avoid circular imports
            from src.common.middleware.logging import get_request_context
            from src.common.utils.datetime import utc_now
            
            # Get context from existing logging middleware
            context = get_request_context()
            metadata = {}
            
            # Add request tracking (lightweight)
            if context.get('request_id'):
                metadata['request_id'] = context['request_id']
            
            # Add user context if available
            if context.get('user_id'):
                metadata['user_id'] = context['user_id']
            
            if context.get('tenant_id'):
                metadata['tenant_id'] = context['tenant_id']
            
            # Add performance data if enabled
            if include_performance:
                perf_data = MetadataCollector.get_performance_metadata()
                if perf_data:
                    metadata.update(perf_data)
            
            # Add response timestamp
            metadata['timestamp'] = utc_now().isoformat()
            
            return metadata
            
        except Exception:
            # Never fail response due to metadata collection
            return {}


# Decorator for tracking database operations
def track_db_operation(func):
    """Decorator to track database operations."""
    if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # Async function
        async def async_wrapper(*args, **kwargs):
            MetadataCollector.increment_db_queries()
            return await func(*args, **kwargs)
        return async_wrapper
    else:
        def sync_wrapper(*args, **kwargs):
            MetadataCollector.increment_db_queries()
            return func(*args, **kwargs)
        return sync_wrapper


# Helper functions for easy integration
def get_api_metadata(include_performance: bool = True) -> Dict[str, Any]:
    """Get metadata for API responses."""
    return MetadataCollector.collect_request_metadata(include_performance)


def track_cache_operation(operation: str):
    """Track cache operations by type."""
    if operation == 'hit':
        MetadataCollector.increment_cache_hits()
    elif operation == 'miss':
        MetadataCollector.increment_cache_misses()
    elif operation == 'set':
        MetadataCollector.increment_cache_sets()