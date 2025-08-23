"""Performance monitoring middleware for FastAPI applications.

Provides request timing, metrics collection, performance monitoring,
and optimization insights for production observability.
"""

import logging
import time
import psutil
from typing import Optional, Dict, Any, Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from datetime import datetime
from collections import defaultdict, deque
import asyncio

from ...features.cache.services import CacheService

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Comprehensive performance monitoring middleware."""
    
    def __init__(
        self,
        app,
        cache_service: Optional[CacheService] = None,
        enable_metrics: bool = True,
        enable_profiling: bool = False,
        slow_request_threshold: float = 1.0,  # seconds
        metrics_retention: int = 3600,  # 1 hour
        exempt_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.cache_service = cache_service
        self.enable_metrics = enable_metrics
        self.enable_profiling = enable_profiling
        self.slow_request_threshold = slow_request_threshold
        self.metrics_retention = metrics_retention
        self.exempt_paths = exempt_paths or [
            "/health", "/metrics", "/docs", "/openapi.json"
        ]
        
        # In-memory metrics storage
        self.request_metrics = defaultdict(list)
        self.performance_stats = {
            "total_requests": 0,
            "total_response_time": 0.0,
            "slow_requests": 0,
            "error_requests": 0,
            "peak_memory_mb": 0.0,
            "peak_cpu_percent": 0.0
        }
        
        # System monitoring
        self.process = psutil.Process()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Monitor request performance and collect metrics."""
        
        # Skip monitoring for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Start performance monitoring
        start_time = time.time()
        start_cpu_time = time.process_time()
        
        # Get initial system metrics
        initial_memory = self._get_memory_usage()
        initial_cpu = self._get_cpu_usage()
        
        # Add timing header to request
        request.state.performance_start = start_time
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate timing metrics
            end_time = time.time()
            total_time = end_time - start_time
            cpu_time = time.process_time() - start_cpu_time
            
            # Get final system metrics
            final_memory = self._get_memory_usage()
            final_cpu = self._get_cpu_usage()
            
            # Calculate performance metrics
            metrics = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": round(total_time * 1000, 2),
                "cpu_time_ms": round(cpu_time * 1000, 2),
                "memory_delta_mb": round(final_memory - initial_memory, 2),
                "peak_memory_mb": round(max(initial_memory, final_memory), 2),
                "cpu_usage_percent": round(max(initial_cpu, final_cpu), 2),
                "timestamp": datetime.utcnow().isoformat(),
                "is_slow": total_time > self.slow_request_threshold,
                "is_error": response.status_code >= 400
            }
            
            # Add context information if available
            if hasattr(request.state, 'user_context') and request.state.user_context:
                metrics["user_id"] = str(request.state.user_context.user_id)
                metrics["tenant_id"] = str(request.state.user_context.tenant_id)
            
            # Record metrics
            await self._record_metrics(metrics)
            
            # Add performance headers to response
            self._add_performance_headers(response, metrics)
            
            # Log slow requests
            if metrics["is_slow"]:
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path} "
                    f"took {metrics['response_time_ms']}ms",
                    extra={"performance_metrics": metrics}
                )
            
            return response
        
        except Exception as e:
            # Record error metrics
            end_time = time.time()
            total_time = end_time - start_time
            
            error_metrics = {
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "response_time_ms": round(total_time * 1000, 2),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "is_error": True
            }
            
            await self._record_metrics(error_metrics)
            
            logger.error(
                f"Request error: {request.method} {request.url.path}",
                extra={"performance_metrics": error_metrics},
                exc_info=True
            )
            
            # Re-raise the exception
            raise
    
    async def _record_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record performance metrics."""
        if not self.enable_metrics:
            return
        
        try:
            # Update in-memory stats
            self.performance_stats["total_requests"] += 1
            self.performance_stats["total_response_time"] += metrics["response_time_ms"]
            
            if metrics.get("is_slow"):
                self.performance_stats["slow_requests"] += 1
            
            if metrics.get("is_error"):
                self.performance_stats["error_requests"] += 1
            
            if "peak_memory_mb" in metrics:
                self.performance_stats["peak_memory_mb"] = max(
                    self.performance_stats["peak_memory_mb"],
                    metrics["peak_memory_mb"]
                )
            
            if "cpu_usage_percent" in metrics:
                self.performance_stats["peak_cpu_percent"] = max(
                    self.performance_stats["peak_cpu_percent"],
                    metrics["cpu_usage_percent"]
                )
            
            # Store detailed metrics per endpoint
            endpoint_key = f"{metrics['method']}:{metrics['path']}"
            self.request_metrics[endpoint_key].append(metrics)
            
            # Limit metrics history
            if len(self.request_metrics[endpoint_key]) > 1000:
                self.request_metrics[endpoint_key] = self.request_metrics[endpoint_key][-500:]
            
            # Store in cache if available
            if self.cache_service:
                await self._store_metrics_in_cache(metrics)
        
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    async def _store_metrics_in_cache(self, metrics: Dict[str, Any]) -> None:
        """Store metrics in cache for persistence."""
        try:
            # Store current metrics
            cache_key = f"performance_metrics:{int(time.time())}"
            await self.cache_service.set(
                cache_key,
                metrics,
                ttl=self.metrics_retention
            )
            
            # Update aggregated stats
            stats_key = "performance_stats:current"
            await self.cache_service.set(
                stats_key,
                self.performance_stats,
                ttl=self.metrics_retention
            )
        
        except Exception as e:
            logger.warning(f"Failed to store metrics in cache: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return self.process.cpu_percent()
        except Exception:
            return 0.0
    
    def _add_performance_headers(self, response: Response, metrics: Dict[str, Any]) -> None:
        """Add performance headers to response."""
        response.headers.update({
            "X-Response-Time": f"{metrics['response_time_ms']}ms",
            "X-CPU-Time": f"{metrics.get('cpu_time_ms', 0)}ms",
            "X-Memory-Delta": f"{metrics.get('memory_delta_mb', 0)}MB",
        })
        
        # Add warning header for slow requests
        if metrics.get("is_slow"):
            response.headers["X-Performance-Warning"] = "slow-request"
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        total_requests = self.performance_stats["total_requests"]
        
        if total_requests == 0:
            return {"message": "No requests processed yet"}
        
        avg_response_time = self.performance_stats["total_response_time"] / total_requests
        error_rate = (self.performance_stats["error_requests"] / total_requests) * 100
        slow_request_rate = (self.performance_stats["slow_requests"] / total_requests) * 100
        
        return {
            "total_requests": total_requests,
            "average_response_time_ms": round(avg_response_time, 2),
            "error_rate_percent": round(error_rate, 2),
            "slow_request_rate_percent": round(slow_request_rate, 2),
            "peak_memory_mb": round(self.performance_stats["peak_memory_mb"], 2),
            "peak_cpu_percent": round(self.performance_stats["peak_cpu_percent"], 2),
            "current_memory_mb": round(self._get_memory_usage(), 2),
            "current_cpu_percent": round(self._get_cpu_usage(), 2)
        }
    
    def get_endpoint_metrics(self, endpoint: str = None) -> Dict[str, Any]:
        """Get metrics for specific endpoint or all endpoints."""
        if endpoint:
            metrics_list = self.request_metrics.get(endpoint, [])
            if not metrics_list:
                return {"message": f"No metrics found for endpoint: {endpoint}"}
            
            response_times = [m["response_time_ms"] for m in metrics_list]
            
            return {
                "endpoint": endpoint,
                "total_requests": len(metrics_list),
                "average_response_time_ms": round(sum(response_times) / len(response_times), 2),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "p95_response_time_ms": round(self._calculate_percentile(response_times, 95), 2),
                "p99_response_time_ms": round(self._calculate_percentile(response_times, 99), 2),
                "error_count": sum(1 for m in metrics_list if m.get("is_error")),
                "slow_request_count": sum(1 for m in metrics_list if m.get("is_slow"))
            }
        else:
            # Return summary for all endpoints
            endpoint_summaries = {}
            for endpoint_key in self.request_metrics:
                endpoint_summaries[endpoint_key] = self.get_endpoint_metrics(endpoint_key)
            
            return endpoint_summaries
    
    def _calculate_percentile(self, values: list, percentile: float) -> float:
        """Calculate percentile value from a list of numbers."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


class TimingMiddleware(BaseHTTPMiddleware):
    """Lightweight timing middleware for basic request timing."""
    
    def __init__(self, app, add_headers: bool = True):
        super().__init__(app)
        self.add_headers = add_headers
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add basic timing to requests."""
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        if self.add_headers:
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        return response


class DatabasePerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking database performance metrics."""
    
    def __init__(
        self,
        app,
        slow_query_threshold: float = 0.5,  # seconds
        enable_query_logging: bool = False
    ):
        super().__init__(app)
        self.slow_query_threshold = slow_query_threshold
        self.enable_query_logging = enable_query_logging
        
        # Track database metrics
        self.db_stats = {
            "total_queries": 0,
            "slow_queries": 0,
            "total_query_time": 0.0,
            "connections_opened": 0,
            "connections_closed": 0
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Monitor database performance during request."""
        
        # Initialize request-level DB tracking
        request.state.db_queries = []
        request.state.db_query_count = 0
        request.state.db_total_time = 0.0
        
        response = await call_next(request)
        
        # Add database performance headers
        if hasattr(request.state, 'db_query_count'):
            response.headers["X-DB-Query-Count"] = str(request.state.db_query_count)
            response.headers["X-DB-Total-Time"] = f"{request.state.db_total_time:.4f}s"
            
            # Warn about excessive queries
            if request.state.db_query_count > 10:
                response.headers["X-DB-Warning"] = "high-query-count"
        
        return response
    
    def record_query(self, query: str, execution_time: float, request: Request = None) -> None:
        """Record database query metrics."""
        self.db_stats["total_queries"] += 1
        self.db_stats["total_query_time"] += execution_time
        
        if execution_time > self.slow_query_threshold:
            self.db_stats["slow_queries"] += 1
            
            if self.enable_query_logging:
                logger.warning(
                    f"Slow query detected: {execution_time:.4f}s - {query[:200]}"
                )
        
        # Track per-request metrics
        if request and hasattr(request.state, 'db_queries'):
            request.state.db_queries.append({
                "query": query[:200],  # Truncate for logging
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            })
            request.state.db_query_count += 1
            request.state.db_total_time += execution_time
    
    def get_db_stats(self) -> Dict[str, Any]:
        """Get database performance statistics."""
        total_queries = self.db_stats["total_queries"]
        
        if total_queries == 0:
            return {"message": "No database queries recorded"}
        
        avg_query_time = self.db_stats["total_query_time"] / total_queries
        slow_query_rate = (self.db_stats["slow_queries"] / total_queries) * 100
        
        return {
            "total_queries": total_queries,
            "slow_queries": self.db_stats["slow_queries"],
            "average_query_time_ms": round(avg_query_time * 1000, 2),
            "slow_query_rate_percent": round(slow_query_rate, 2),
            "total_query_time_seconds": round(self.db_stats["total_query_time"], 2),
            "connections_opened": self.db_stats["connections_opened"],
            "connections_closed": self.db_stats["connections_closed"]
        }