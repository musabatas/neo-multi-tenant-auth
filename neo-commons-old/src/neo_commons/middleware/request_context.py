"""
Request context middleware for metadata collection.

Generic request context middleware that can be used across all platform services
in the NeoMultiTenant ecosystem.
"""
import time
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from neo_commons.utils.datetime import utc_now


@runtime_checkable
class RequestContextConfig(Protocol):
    """Protocol for request context configuration."""
    
    @property
    def include_processing_time_header(self) -> bool:
        """Whether to include processing time in response headers."""
        ...
    
    @property
    def include_request_id_header(self) -> bool:
        """Whether to include request ID in response headers."""
        ...
    
    @property
    def short_request_id(self) -> bool:
        """Whether to use short request IDs for performance."""
        ...
    
    @property
    def enable_performance_tracking(self) -> bool:
        """Whether to enable detailed performance tracking."""
        ...


# Context variables for request-scoped data (thread-safe, async-friendly)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
start_time_var: ContextVar[Optional[float]] = ContextVar('start_time', default=None)
db_queries_var: ContextVar[Optional[List[str]]] = ContextVar('db_queries', default=None)
cache_operations_var: ContextVar[Optional[Dict[str, int]]] = ContextVar('cache_operations', default=None)
performance_markers_var: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar('performance_markers', default=None)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for collecting request metadata.
    Uses contextvars for minimal performance overhead.
    
    Features:
    - Request ID generation and tracking
    - Processing time measurement
    - Database query tracking
    - Cache operation tracking
    - Performance markers
    - Configurable header inclusion
    """
    
    def __init__(
        self,
        app,
        config: Optional[RequestContextConfig] = None,
        *,
        include_processing_time_header: bool = True,
        include_request_id_header: bool = True,
        short_request_id: bool = True,
        enable_performance_tracking: bool = True
    ):
        super().__init__(app)
        
        # Use config if provided, otherwise use parameters
        if config:
            self.include_processing_time_header = config.include_processing_time_header
            self.include_request_id_header = config.include_request_id_header
            self.short_request_id = config.short_request_id
            self.enable_performance_tracking = config.enable_performance_tracking
        else:
            self.include_processing_time_header = include_processing_time_header
            self.include_request_id_header = include_request_id_header
            self.short_request_id = short_request_id
            self.enable_performance_tracking = enable_performance_tracking
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with context tracking."""
        # Generate unique request ID
        if self.short_request_id:
            request_id = str(uuid.uuid4())[:8]  # Short ID for performance
        else:
            request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Record start time with high precision
        start_time = time.perf_counter()
        start_time_var.set(start_time)
        
        # Initialize counters with fresh instances
        db_queries_var.set([])
        cache_operations_var.set({'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0})
        if self.enable_performance_tracking:
            performance_markers_var.set([])
        
        # Add request ID to request state for access in handlers
        request.state.request_id = request_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate total processing time
            processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            
            # Add metadata to response headers (configurable)
            if self.include_request_id_header:
                response.headers["X-Request-ID"] = request_id
            
            if self.include_processing_time_header:
                response.headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
            
            return response
            
        except Exception as e:
            # Even on error, calculate processing time for logging
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
        queries = db_queries_var.get() or []
        queries.append(query_type)
        db_queries_var.set(queries)
    
    @staticmethod
    def track_cache_hit():
        """Track cache hit."""
        ops = cache_operations_var.get() or {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}
        ops['hits'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_miss():
        """Track cache miss."""
        ops = cache_operations_var.get() or {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}
        ops['misses'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_set():
        """Track cache set operation."""
        ops = cache_operations_var.get() or {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}
        ops['sets'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_delete():
        """Track cache delete operation."""
        ops = cache_operations_var.get() or {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}
        ops['deletes'] += 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def add_performance_marker(name: str, duration_ms: Optional[float] = None):
        """Add a performance marker."""
        markers = performance_markers_var.get() or []
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
        
        db_queries = db_queries_var.get() or []
        cache_ops = cache_operations_var.get() or {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}
        
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
        markers = performance_markers_var.get() or []
        if markers:
            metadata['performance_markers'] = len(markers)
        
        return metadata
    
    @staticmethod
    def get_debug_metadata() -> Dict[str, Any]:
        """Get detailed metadata for debugging (more verbose)."""
        metadata = RequestContext.get_metadata()
        
        # Add detailed information for debugging
        db_queries = db_queries_var.get() or []
        if db_queries:
            metadata['db_query_types'] = db_queries
        
        markers = performance_markers_var.get() or []
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


# Convenience functions for common operations
def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return RequestContext.get_request_id()


def get_processing_time() -> Optional[float]:
    """Get current processing time in milliseconds."""
    return RequestContext.get_processing_time()


def get_request_metadata() -> Dict[str, Any]:
    """Get current request metadata."""
    return RequestContext.get_metadata()