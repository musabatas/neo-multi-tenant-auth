"""
Timing and performance middleware for request processing metrics.
"""
import time
import logging
from typing import Callable, Dict, Any, Optional, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def get_request_context() -> Dict[str, Any]:
    """Get current request context from context variables."""
    try:
        from neo_commons.middleware.logging import get_request_context as _get_context
        return _get_context()
    except ImportError:
        return {}


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds timing headers and tracks performance metrics.
    
    Features:
    - Process time tracking
    - Performance thresholds and alerting
    - Detailed timing breakdown
    - Slow request logging
    - Performance metrics collection
    """
    
    def __init__(
        self,
        app,
        *,
        add_timing_header: bool = True,
        log_slow_requests: bool = True,
        slow_request_threshold: float = 1.0,  # seconds
        very_slow_threshold: float = 5.0,  # seconds
        exclude_paths: Optional[List[str]] = None,
        track_detailed_timing: bool = False
    ):
        super().__init__(app)
        self.add_timing_header = add_timing_header
        self.log_slow_requests = log_slow_requests
        self.slow_request_threshold = slow_request_threshold
        self.very_slow_threshold = very_slow_threshold
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs"]
        self.track_detailed_timing = track_detailed_timing
        
        # Performance tracking
        self._request_metrics = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timing measurement."""
        # Skip timing for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        
        # Track detailed timing if enabled
        timing_details = {}
        if self.track_detailed_timing:
            timing_details['middleware_start'] = start_perf_counter
        
        try:
            # Store timing info in request state
            request.state.start_time = start_time
            request.state.start_perf_counter = start_perf_counter
            
            # Process request
            response = await call_next(request)
            
            # Calculate timing
            end_time = time.time()
            end_perf_counter = time.perf_counter()
            
            process_time = end_time - start_time
            precise_process_time = end_perf_counter - start_perf_counter
            
            # Add timing details
            if self.track_detailed_timing:
                timing_details.update({
                    'middleware_end': end_perf_counter,
                    'total_time': precise_process_time,
                    'wall_clock_time': process_time
                })
            
            # Add timing headers
            if self.add_timing_header:
                response.headers["X-Process-Time"] = f"{precise_process_time:.6f}"
                response.headers["X-Process-Time-Ms"] = f"{precise_process_time * 1000:.2f}"
            
            # Log slow requests
            if self.log_slow_requests and process_time >= self.slow_request_threshold:
                await self._log_slow_request(
                    request, response, process_time, timing_details
                )
            
            # Track metrics
            self._track_request_metrics(request, response, process_time)
            
            return response
            
        except Exception as exc:
            # Calculate timing for failed requests too
            end_time = time.time()
            process_time = end_time - start_time
            
            # Log slow failed requests
            if self.log_slow_requests and process_time >= self.slow_request_threshold:
                await self._log_slow_request(
                    request, None, process_time, timing_details, error=str(exc)
                )
            
            raise
    
    async def _log_slow_request(
        self,
        request: Request,
        response: Optional[Response],
        process_time: float,
        timing_details: Dict[str, Any],
        error: Optional[str] = None
    ):
        """Log details of slow requests."""
        context = get_request_context()
        
        log_data = {
            "event": "slow_request",
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "process_time_ms": round(process_time * 1000, 2),
            "process_time_seconds": round(process_time, 3),
            "status_code": response.status_code if response else None,
            "error": error,
            **context
        }
        
        # Add performance classification
        if process_time >= self.very_slow_threshold:
            log_data["performance_class"] = "very_slow"
            log_level = logging.WARNING
        else:
            log_data["performance_class"] = "slow"
            log_level = logging.INFO
        
        # Add timing details if available
        if timing_details:
            log_data["timing_details"] = timing_details
        
        # Add query parameters for analysis
        if request.query_params:
            log_data["query_params"] = dict(request.query_params)
        
        # Log the slow request
        logger.log(log_level, "Slow request detected: %s", log_data)
    
    def _track_request_metrics(
        self,
        request: Request,
        response: Response,
        process_time: float
    ):
        """Track request metrics for performance analysis."""
        path_pattern = self._get_path_pattern(request.url.path)
        method = request.method
        status_code = response.status_code
        
        # Create metric key
        metric_key = f"{method}:{path_pattern}:{status_code}"
        
        # Initialize metrics if not exists
        if metric_key not in self._request_metrics:
            self._request_metrics[metric_key] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "slow_requests": 0,
                "very_slow_requests": 0
            }
        
        # Update metrics
        metrics = self._request_metrics[metric_key]
        metrics["count"] += 1
        metrics["total_time"] += process_time
        metrics["min_time"] = min(metrics["min_time"], process_time)
        metrics["max_time"] = max(metrics["max_time"], process_time)
        
        if process_time >= self.very_slow_threshold:
            metrics["very_slow_requests"] += 1
        elif process_time >= self.slow_request_threshold:
            metrics["slow_requests"] += 1
    
    def _get_path_pattern(self, path: str) -> str:
        """Convert path to pattern for metrics grouping."""
        # Simple pattern extraction - replace IDs with placeholders
        import re
        
        # Replace UUIDs
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', path, flags=re.IGNORECASE)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Replace other common patterns
        path = re.sub(r'/[a-zA-Z0-9_-]{20,}', '/{token}', path)
        
        return path
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics_summary = {}
        
        for metric_key, data in self._request_metrics.items():
            if data["count"] > 0:
                avg_time = data["total_time"] / data["count"]
                metrics_summary[metric_key] = {
                    "count": data["count"],
                    "avg_time_ms": round(avg_time * 1000, 2),
                    "min_time_ms": round(data["min_time"] * 1000, 2),
                    "max_time_ms": round(data["max_time"] * 1000, 2),
                    "slow_requests": data["slow_requests"],
                    "very_slow_requests": data["very_slow_requests"],
                    "slow_percentage": round((data["slow_requests"] + data["very_slow_requests"]) / data["count"] * 100, 2)
                }
        
        return metrics_summary
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self._request_metrics = {}


class ResponseSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks response sizes and adds size headers.
    
    Features:
    - Response size tracking
    - Size headers for debugging
    - Large response detection
    - Compression recommendations
    """
    
    def __init__(
        self,
        app,
        *,
        add_size_header: bool = True,
        log_large_responses: bool = True,
        large_response_threshold: int = 1024 * 1024,  # 1MB
        exclude_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.add_size_header = add_size_header
        self.log_large_responses = log_large_responses
        self.large_response_threshold = large_response_threshold
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track response size."""
        # Skip for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        response = await call_next(request)
        
        # Calculate response size
        response_size = 0
        if hasattr(response, 'body') and response.body:
            response_size = len(response.body)
        elif hasattr(response, 'content') and response.content:
            response_size = len(response.content)
        
        # Add size header
        if self.add_size_header and response_size > 0:
            response.headers["X-Response-Size"] = str(response_size)
            response.headers["X-Response-Size-KB"] = f"{response_size / 1024:.2f}"
        
        # Log large responses
        if (self.log_large_responses and 
            response_size >= self.large_response_threshold):
            await self._log_large_response(request, response, response_size)
        
        return response
    
    async def _log_large_response(
        self,
        request: Request,
        response: Response,
        response_size: int
    ):
        """Log large response for optimization analysis."""
        context = get_request_context()
        
        log_data = {
            "event": "large_response",
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "status_code": response.status_code,
            "response_size_bytes": response_size,
            "response_size_kb": round(response_size / 1024, 2),
            "response_size_mb": round(response_size / (1024 * 1024), 2),
            "content_type": response.headers.get("content-type"),
            "content_encoding": response.headers.get("content-encoding"),
            **context
        }
        
        # Add optimization suggestions
        suggestions = []
        if not response.headers.get("content-encoding"):
            suggestions.append("Consider enabling compression")
        if response.headers.get("content-type", "").startswith("application/json"):
            suggestions.append("Consider pagination for large JSON responses")
        if response.headers.get("content-type", "").startswith("text/"):
            suggestions.append("Consider minification for text responses")
        
        if suggestions:
            log_data["optimization_suggestions"] = suggestions
        
        logger.warning("Large response detected: %s", log_data)


def get_performance_summary() -> Dict[str, Any]:
    """Get a summary of all performance metrics."""
    # This would typically be implemented with a shared metrics store
    # For now, return a placeholder
    return {
        "note": "Performance summary would aggregate metrics from all middleware instances",
        "recommendation": "Implement shared metrics store (Redis/PostgreSQL) for production"
    }