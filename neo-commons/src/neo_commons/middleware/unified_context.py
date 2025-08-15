"""
Unified request context middleware combining logging, timing, and metadata collection.

This middleware consolidates functionality from:
- RequestContextMiddleware (request_context.py)
- StructuredLoggingMiddleware (logging.py) 
- TimingMiddleware (timing.py)
- MetadataCollector (utils/metadata.py)

Features:
- Request ID and correlation ID generation
- User and tenant context extraction
- Performance timing and metrics
- Cache operation tracking
- Database query tracking
- Structured logging integration
- Performance threshold monitoring
"""

import time
import json
import logging
import uuid
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional, Dict, Any, List, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def generate_uuid_v7() -> str:
    """Generate UUIDv7 or fallback to uuid4."""
    try:
        # Try to import uuid7 library if available
        import uuid7
        return str(uuid7.uuid7())
    except ImportError:
        # Fallback to uuid4
        return str(uuid.uuid4())


# Unified context variables for request-scoped data (thread-safe, async-friendly)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)
start_time_var: ContextVar[Optional[float]] = ContextVar('start_time', default=None)

# Performance tracking variables
db_queries_var: ContextVar[Optional[List[str]]] = ContextVar('db_queries', default=None)
cache_operations_var: ContextVar[Optional[Dict[str, int]]] = ContextVar('cache_operations', default=None)
performance_markers_var: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar('performance_markers', default=None)


class UnifiedContextMiddleware(BaseHTTPMiddleware):
    """
    Unified middleware for request context, logging, timing, and metadata collection.
    
    Consolidates all request-scoped tracking into a single, efficient middleware.
    """
    
    def __init__(
        self,
        app,
        *,
        # Request context options
        generate_request_id: bool = True,
        generate_correlation_id: bool = True,
        extract_user_context: bool = True,
        
        # Logging options
        log_requests: bool = True,
        log_responses: bool = True,
        log_response_body: bool = False,
        sensitive_headers: Optional[List[str]] = None,
        
        # Timing options
        add_timing_header: bool = True,
        log_slow_requests: bool = True,
        slow_request_threshold: float = 1.0,  # seconds
        very_slow_threshold: float = 5.0,  # seconds
        
        # Metadata tracking options
        track_cache_operations: bool = True,
        track_db_queries: bool = True,
        track_performance_markers: bool = True,
        
        # Path filtering
        exclude_paths: Optional[List[str]] = None,
        include_health_endpoints: bool = False
    ):
        super().__init__(app)
        
        # Store configuration
        self.generate_request_id = generate_request_id
        self.generate_correlation_id = generate_correlation_id
        self.extract_user_context = extract_user_context
        
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_response_body = log_response_body
        self.sensitive_headers = sensitive_headers or ['authorization', 'cookie', 'x-api-key']
        
        self.add_timing_header = add_timing_header
        self.log_slow_requests = log_slow_requests
        self.slow_request_threshold = slow_request_threshold
        self.very_slow_threshold = very_slow_threshold
        
        self.track_cache_operations = track_cache_operations
        self.track_db_queries = track_db_queries
        self.track_performance_markers = track_performance_markers
        
        self.exclude_paths = exclude_paths or []
        if not include_health_endpoints:
            self.exclude_paths.extend(["/health", "/metrics", "/docs", "/openapi.json"])
        
        logger.info("UnifiedContextMiddleware initialized with comprehensive tracking")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch with unified context management."""
        
        # Check if path should be excluded
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Initialize request context
        await self._initialize_context(request)
        
        # Start timing
        start_time = time.perf_counter()
        start_time_var.set(start_time)
        
        # Log request if enabled
        if self.log_requests:
            self._log_request(request)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            
            # Add response headers
            self._add_response_headers(response, processing_time)
            
            # Log response if enabled
            if self.log_responses:
                self._log_response(request, response, processing_time)
            
            # Log slow requests
            if self.log_slow_requests and processing_time > (self.slow_request_threshold * 1000):
                self._log_slow_request(request, processing_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time even for errors
            processing_time = (time.perf_counter() - start_time) * 1000
            
            # Log error with context
            self._log_error(request, e, processing_time)
            raise
    
    async def _initialize_context(self, request: Request) -> None:
        """Initialize all context variables for the request."""
        
        # Generate or extract request ID
        if self.generate_request_id:
            request_id = self._get_or_generate_request_id(request)
            request_id_var.set(request_id)
            request.state.request_id = request_id
        
        # Generate or extract correlation ID
        if self.generate_correlation_id:
            correlation_id = self._get_or_generate_correlation_id(request)
            correlation_id_var.set(correlation_id)
            request.state.correlation_id = correlation_id
        
        # Extract user and tenant context
        if self.extract_user_context:
            user_id, tenant_id = await self._extract_user_context(request)
            user_id_var.set(user_id)
            tenant_id_var.set(tenant_id)
            if user_id:
                request.state.user_id = user_id
            if tenant_id:
                request.state.tenant_id = tenant_id
        
        # Initialize tracking variables
        if self.track_db_queries:
            db_queries_var.set([])
        
        if self.track_cache_operations:
            cache_operations_var.set({'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0})
        
        if self.track_performance_markers:
            performance_markers_var.set([])
    
    def _get_or_generate_request_id(self, request: Request) -> str:
        """Get existing request ID or generate new one."""
        # Check headers for existing request ID
        request_id = request.headers.get('x-request-id') or request.headers.get('request-id')
        if not request_id:
            request_id = generate_uuid_v7()[:8]  # Short ID for performance
        return request_id
    
    def _get_or_generate_correlation_id(self, request: Request) -> str:
        """Get existing correlation ID or generate new one."""
        # Check headers for existing correlation ID
        correlation_id = request.headers.get('x-correlation-id') or request.headers.get('correlation-id')
        if not correlation_id:
            correlation_id = generate_uuid_v7()
        return correlation_id
    
    async def _extract_user_context(self, request: Request) -> tuple[Optional[str], Optional[str]]:
        """Extract user and tenant context from request."""
        user_id = None
        tenant_id = None
        
        # Try to get from request state (set by auth middleware)
        if hasattr(request.state, 'user'):
            user_data = getattr(request.state, 'user', {})
            if isinstance(user_data, dict):
                user_id = user_data.get('sub') or user_data.get('user_id')
                tenant_id = user_data.get('tenant_id')
        
        # Fallback to headers
        if not user_id:
            user_id = request.headers.get('x-user-id')
        if not tenant_id:
            tenant_id = request.headers.get('x-tenant-id')
        
        return user_id, tenant_id
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from tracking."""
        return any(path.startswith(exclude_path) for exclude_path in self.exclude_paths)
    
    def _add_response_headers(self, response: Response, processing_time: float) -> None:
        """Add context and timing headers to response."""
        
        # Add request tracking headers
        request_id = request_id_var.get()
        if request_id:
            response.headers["X-Request-ID"] = request_id
        
        correlation_id = correlation_id_var.get()
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id
        
        # Add timing headers
        if self.add_timing_header:
            response.headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
        
        # Add metadata headers (only non-zero values)
        metadata = self._get_current_metadata()
        if metadata.get('db_queries', 0) > 0:
            response.headers["X-DB-Queries"] = str(metadata['db_queries'])
        
        cache_data = metadata.get('cache', {})
        if cache_data and cache_data.get('operations', {}).get('hits', 0) > 0:
            response.headers["X-Cache-Hit-Rate"] = f"{cache_data.get('hit_rate', 0):.1f}%"
    
    def _log_request(self, request: Request) -> None:
        """Log incoming request with context."""
        headers = self._filter_sensitive_headers(dict(request.headers))
        
        logger.info(
            "Request started",
            extra={
                "event_type": "request_started",
                "request_id": request_id_var.get(),
                "correlation_id": correlation_id_var.get(),
                "method": request.method,
                "url": str(request.url),
                "user_agent": headers.get("user-agent"),
                "remote_addr": getattr(request.client, 'host', None) if request.client else None,
                "user_id": user_id_var.get(),
                "tenant_id": tenant_id_var.get(),
            }
        )
    
    def _log_response(self, request: Request, response: Response, processing_time: float) -> None:
        """Log response with context and metrics."""
        metadata = self._get_current_metadata()
        
        logger.info(
            "Request completed",
            extra={
                "event_type": "request_completed",
                "request_id": request_id_var.get(),
                "correlation_id": correlation_id_var.get(),
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "processing_time_ms": round(processing_time, 2),
                "user_id": user_id_var.get(),
                "tenant_id": tenant_id_var.get(),
                **metadata
            }
        )
    
    def _log_slow_request(self, request: Request, processing_time: float) -> None:
        """Log slow request with detailed context."""
        level = logging.WARNING if processing_time > (self.very_slow_threshold * 1000) else logging.INFO
        metadata = self._get_current_metadata()
        
        logger.log(
            level,
            f"Slow request detected: {processing_time:.2f}ms",
            extra={
                "event_type": "slow_request",
                "request_id": request_id_var.get(),
                "correlation_id": correlation_id_var.get(),
                "method": request.method,
                "url": str(request.url),
                "processing_time_ms": round(processing_time, 2),
                "is_very_slow": processing_time > (self.very_slow_threshold * 1000),
                "user_id": user_id_var.get(),
                "tenant_id": tenant_id_var.get(),
                **metadata
            }
        )
    
    def _log_error(self, request: Request, error: Exception, processing_time: float) -> None:
        """Log error with full context."""
        metadata = self._get_current_metadata()
        
        logger.error(
            f"Request failed: {error}",
            extra={
                "event_type": "request_error",
                "request_id": request_id_var.get(),
                "correlation_id": correlation_id_var.get(),
                "method": request.method,
                "url": str(request.url),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "processing_time_ms": round(processing_time, 2),
                "user_id": user_id_var.get(),
                "tenant_id": tenant_id_var.get(),
                **metadata
            },
            exc_info=True
        )
    
    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter out sensitive headers for logging."""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "[REDACTED]"
            else:
                filtered[key] = value
        return filtered
    
    def _get_current_metadata(self) -> Dict[str, Any]:
        """Get current request metadata."""
        metadata = {}
        
        # Database queries
        if self.track_db_queries:
            db_queries = db_queries_var.get() or []
            if db_queries:
                metadata['db_queries'] = len(db_queries)
        
        # Cache operations
        if self.track_cache_operations:
            cache_ops = cache_operations_var.get() or {}
            hits = cache_ops.get('hits', 0)
            misses = cache_ops.get('misses', 0)
            total_cache_ops = hits + misses
            
            if total_cache_ops > 0:
                cache_hit_rate = (hits / total_cache_ops * 100)
                metadata['cache'] = {
                    'hit_rate': round(cache_hit_rate, 1),
                    'operations': cache_ops
                }
        
        # Performance markers
        if self.track_performance_markers:
            markers = performance_markers_var.get() or []
            if markers:
                metadata['performance_markers'] = len(markers)
        
        return metadata


class UnifiedRequestContext:
    """Helper class for accessing unified request context data."""
    
    @staticmethod
    def get_request_id() -> Optional[str]:
        """Get current request ID."""
        return request_id_var.get()
    
    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """Get current correlation ID."""
        return correlation_id_var.get()
    
    @staticmethod
    def get_user_id() -> Optional[str]:
        """Get current user ID."""
        return user_id_var.get()
    
    @staticmethod
    def get_tenant_id() -> Optional[str]:
        """Get current tenant ID."""
        return tenant_id_var.get()
    
    @staticmethod
    def get_processing_time() -> Optional[float]:
        """Get processing time in milliseconds."""
        start_time = start_time_var.get()
        if start_time is None:
            return None
        return (time.perf_counter() - start_time) * 1000
    
    @staticmethod
    def track_db_query(query_type: str) -> None:
        """Track a database query (minimal overhead)."""
        queries = db_queries_var.get()
        if queries is None:
            queries = []
        queries.append(query_type)
        db_queries_var.set(queries)
    
    @staticmethod
    def track_cache_hit() -> None:
        """Track cache hit."""
        ops = cache_operations_var.get()
        if ops is None:
            ops = {}
        ops['hits'] = ops.get('hits', 0) + 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_miss() -> None:
        """Track cache miss."""
        ops = cache_operations_var.get()
        if ops is None:
            ops = {}
        ops['misses'] = ops.get('misses', 0) + 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_set() -> None:
        """Track cache set operation."""
        ops = cache_operations_var.get()
        if ops is None:
            ops = {}
        ops['sets'] = ops.get('sets', 0) + 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def track_cache_delete() -> None:
        """Track cache delete operation."""
        ops = cache_operations_var.get()
        if ops is None:
            ops = {}
        ops['deletes'] = ops.get('deletes', 0) + 1
        cache_operations_var.set(ops)
    
    @staticmethod
    def add_performance_marker(name: str, duration_ms: Optional[float] = None) -> None:
        """Add a performance marker."""
        markers = performance_markers_var.get()
        if markers is None:
            markers = []
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
        cache_ops = cache_operations_var.get() or {}
        
        # Calculate cache hit rate
        hits = cache_ops.get('hits', 0)
        misses = cache_ops.get('misses', 0)
        total_cache_ops = hits + misses
        cache_hit_rate = (hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
        
        metadata = {
            'request_id': request_id_var.get(),
            'correlation_id': correlation_id_var.get(),
            'user_id': user_id_var.get(),
            'tenant_id': tenant_id_var.get(),
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


# Compatibility functions for existing code
def get_request_context() -> Dict[str, Any]:
    """Get current request context (compatibility function)."""
    return UnifiedRequestContext.get_metadata()


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID (compatibility function)."""
    return UnifiedRequestContext.get_correlation_id()


def get_request_id() -> Optional[str]:
    """Get current request ID (compatibility function)."""
    return UnifiedRequestContext.get_request_id()


# Performance monitoring decorator
def track_performance(operation_name: str):
    """Decorator to track operation performance."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                UnifiedRequestContext.add_performance_marker(operation_name, duration)
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                UnifiedRequestContext.add_performance_marker(f"{operation_name}_error", duration)
                raise
        
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                UnifiedRequestContext.add_performance_marker(operation_name, duration)
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                UnifiedRequestContext.add_performance_marker(f"{operation_name}_error", duration)
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Compatibility aliases
RequestContext = UnifiedRequestContext  # For backward compatibility
RequestContextMiddleware = UnifiedContextMiddleware  # For backward compatibility