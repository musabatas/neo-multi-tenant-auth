"""
Request context middleware for metadata collection.
Minimal overhead implementation using contextvars.
"""

import time
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.common.utils.datetime import utc_now


# Context variables for request-scoped data (thread-safe, async-friendly)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
start_time_var: ContextVar[Optional[float]] = ContextVar('start_time', default=None)
db_queries_var: ContextVar[List[str]] = ContextVar('db_queries', default_factory=list)
cache_operations_var: ContextVar[Dict[str, int]] = ContextVar('cache_operations', default_factory=dict)
performance_markers_var: ContextVar[List[Dict[str, Any]]] = ContextVar('performance_markers', default_factory=list)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for collecting request metadata.
    Uses contextvars for minimal performance overhead.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]  # Short ID for performance
        request_id_var.set(request_id)
        
        # Record start time with high precision
        start_time = time.perf_counter()
        start_time_var.set(start_time)
        
        # Initialize counters
        db_queries_var.set([])
        cache_operations_var.set({'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0})
        performance_markers_var.set([])
        
        # Add request ID to headers for tracing
        request.state.request_id = request_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate total processing time
            processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            
            # Add metadata to response headers (for debugging)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
            
            return response
            
        except Exception as e:
            # Even on error, include metadata
            processing_time = (time.perf_counter() - start_time) * 1000
            raise


class RequestContext:
    """Helper class for accessing request context data."""
    
    @staticmethod
    def get_request_id() -> Optional[str]:
        """Get current request ID."""
        return request_id_var.get()
    
    @staticmethod
    def get_processing_time() -> Optional[float]:
        """Get processing time in milliseconds."""
        start_time = start_time_var.get()
        if start_time is None:
            return None
        return (time.perf_counter() - start_time) * 1000
    
    @staticmethod
    def track_db_query(query_type: str):
        """Track a database query (minimal overhead)."""
        queries = db_queries_var.get()
        queries.append(query_type)
        db_queries_var.set(queries)
    
    @staticmethod
    def track_cache_hit():
        """Track cache hit."""
        ops = cache_operations_var.get()
        ops['hits'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_miss():
        """Track cache miss."""
        ops = cache_operations_var.get()
        ops['misses'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_set():
        """Track cache set operation."""
        ops = cache_operations_var.get()
        ops['sets'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_delete():
        """Track cache delete operation."""
        ops = cache_operations_var.get()
        ops['deletes'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def add_performance_marker(name: str, duration_ms: Optional[float] = None):
        """Add a performance marker."""
        markers = performance_markers_var.get()
        marker = {
            'name': name,
            'timestamp': time.perf_counter(),
            'duration_ms': duration_ms
        }
        markers.append(marker)
        performance_markers_var.set(markers)
    
    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        """Get all collected metadata for this request."""
        start_time = start_time_var.get()
        processing_time = None
        if start_time is not None:
            processing_time = (time.perf_counter() - start_time) * 1000
        
        db_queries = db_queries_var.get()
        cache_ops = cache_operations_var.get()
        
        # Calculate cache hit rate
        total_cache_ops = cache_ops['hits'] + cache_ops['misses']
        cache_hit_rate = (cache_ops['hits'] / total_cache_ops * 100) if total_cache_ops > 0 else 0
        
        metadata = {
            'request_id': request_id_var.get(),
            'processing_time_ms': round(processing_time, 2) if processing_time else None,
            'timestamp': utc_now().isoformat(),
        }
        
        # Only include non-zero metrics to reduce payload size
        if db_queries:
            metadata['db_queries'] = len(db_queries)
            
        if total_cache_ops > 0:
            metadata['cache'] = {
                'hit_rate': round(cache_hit_rate, 1),
                'operations': cache_ops
            }
        
        # Include performance markers if any
        markers = performance_markers_var.get()
        if markers:
            metadata['performance_markers'] = len(markers)
        
        return metadata
    
    @staticmethod
    def get_debug_metadata() -> Dict[str, Any]:
        """Get detailed metadata for debugging (more verbose)."""
        metadata = RequestContext.get_metadata()
        
        # Add detailed information for debugging
        db_queries = db_queries_var.get()
        if db_queries:
            metadata['db_query_types'] = db_queries
        
        markers = performance_markers_var.get()
        if markers:
            metadata['markers'] = markers
        
        return metadata


# Performance monitoring decorator
def track_performance(operation_name: str):
    """Decorator to track operation performance."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                RequestContext.add_performance_marker(operation_name, duration)
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                RequestContext.add_performance_marker(f"{operation_name}_error", duration)
                raise
        
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                RequestContext.add_performance_marker(operation_name, duration)
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                RequestContext.add_performance_marker(f"{operation_name}_error", duration)
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        return sync_wrapper
    
    return decorator