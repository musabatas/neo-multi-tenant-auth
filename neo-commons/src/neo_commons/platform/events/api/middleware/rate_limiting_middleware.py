"""
Rate limiting middleware.

ONLY handles API rate limiting and throttling for event endpoints.
"""

import time
from typing import Callable, Dict, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass

from ....core.value_objects import TenantId, UserId


@dataclass
class RateLimitRule:
    """Rate limit rule configuration."""
    
    requests_per_minute: int
    burst_limit: int
    window_minutes: int = 1
    
    
@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    
    tokens: int
    last_refill: float
    request_history: deque
    
    def __post_init__(self):
        if not hasattr(self, 'request_history') or self.request_history is None:
            self.request_history = deque(maxlen=1000)  # Keep last 1000 requests


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limiting on event API endpoints.
    
    Implements token bucket algorithm with per-tenant and per-user limits.
    """
    
    def __init__(
        self,
        app,
        *,
        default_rules: Dict[str, RateLimitRule] = None,
        tenant_rules: Dict[str, RateLimitRule] = None,
        public_rules: Dict[str, RateLimitRule] = None,
        cleanup_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            default_rules: Default rate limits by endpoint pattern
            tenant_rules: Tenant-specific rate limits  
            public_rules: Public endpoint rate limits
            cleanup_interval: Cleanup interval for expired buckets
        """
        super().__init__(app)
        
        # Default rate limits per endpoint type
        self.default_rules = default_rules or {
            "tenant_dispatch": RateLimitRule(requests_per_minute=100, burst_limit=10),
            "tenant_query": RateLimitRule(requests_per_minute=200, burst_limit=20),
            "admin_operations": RateLimitRule(requests_per_minute=500, burst_limit=50),
            "internal_api": RateLimitRule(requests_per_minute=1000, burst_limit=100),
            "public_api": RateLimitRule(requests_per_minute=60, burst_limit=10),
        }
        
        # Tenant-specific overrides
        self.tenant_rules = tenant_rules or {}
        
        # Public API limits
        self.public_rules = public_rules or {}
        
        # In-memory buckets (in production, use Redis)
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enforce rate limits."""
        # Clean up expired buckets periodically
        await self._cleanup_expired_buckets()
        
        # Determine rate limit rule
        rule = self._get_rate_limit_rule(request)
        if not rule:
            # No rate limiting for this endpoint
            return await call_next(request)
        
        # Get rate limit key (tenant, user, or IP based)
        limit_key = self._get_rate_limit_key(request)
        
        # Check rate limit
        allowed, retry_after = await self._check_rate_limit(limit_key, rule)
        
        if not allowed:
            # Rate limit exceeded
            response = self._create_rate_limit_response(retry_after)
            await self._log_rate_limit_violation(request, limit_key, rule)
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, limit_key, rule)
        
        return response
    
    def _get_rate_limit_rule(self, request: Request) -> Optional[RateLimitRule]:
        """Determine appropriate rate limit rule for request."""
        path = request.url.path
        method = request.method
        
        # Public API endpoints
        if path.startswith("/public/events"):
            if path in ["/public/events/health", "/public/events/status"]:
                return self.default_rules.get("public_api")
            return self.default_rules.get("public_api")
        
        # Internal API endpoints (higher limits)
        if path.startswith("/internal/events"):
            return self.default_rules.get("internal_api")
        
        # Admin endpoints (higher limits)
        if path.startswith("/admin/events"):
            return self.default_rules.get("admin_operations")
        
        # Tenant endpoints (differentiate by operation type)
        if path.startswith("/tenant/events"):
            if method == "POST" and "dispatch" in path:
                return self.default_rules.get("tenant_dispatch")
            else:
                return self.default_rules.get("tenant_query")
        
        # Default: no rate limiting
        return None
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key for request."""
        path = request.url.path
        
        # For tenant endpoints, use tenant + user
        if path.startswith("/tenant/events"):
            tenant_id = getattr(request.state, "tenant_id", None)
            user_context = getattr(request.state, "user_context", None)
            
            if tenant_id and user_context and user_context.user_id:
                return f"tenant:{tenant_id.value}:user:{user_context.user_id.value}"
            elif tenant_id:
                return f"tenant:{tenant_id.value}"
        
        # For admin endpoints, use admin user
        if path.startswith("/admin/events"):
            user_context = getattr(request.state, "user_context", None)
            if user_context and user_context.user_id:
                return f"admin:{user_context.user_id.value}"
        
        # For internal endpoints, use service identifier
        if path.startswith("/internal/events"):
            service_token = getattr(request.state, "service_token", None)
            if service_token and service_token.get("service_id"):
                return f"service:{service_token['service_id']}"
        
        # For public endpoints, use IP address
        client_ip = getattr(request.state, "client_ip", "unknown")
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        
        if api_key:
            return f"public:key:{api_key[:10]}"  # Truncate for security
        else:
            return f"public:ip:{client_ip}"
    
    async def _check_rate_limit(self, key: str, rule: RateLimitRule) -> tuple[bool, int]:
        """
        Check if request is within rate limits.
        
        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.time()
        
        # Get or create bucket
        if key not in self.buckets:
            self.buckets[key] = RateLimitBucket(
                tokens=rule.burst_limit,
                last_refill=now,
                request_history=deque(maxlen=1000)
            )
        
        bucket = self.buckets[key]
        
        # Refill tokens based on time passed
        time_passed = now - bucket.last_refill
        tokens_to_add = int(time_passed * (rule.requests_per_minute / 60.0))
        
        if tokens_to_add > 0:
            bucket.tokens = min(rule.burst_limit, bucket.tokens + tokens_to_add)
            bucket.last_refill = now
        
        # Check if request is allowed
        if bucket.tokens > 0:
            bucket.tokens -= 1
            bucket.request_history.append(now)
            return True, 0
        
        # Calculate retry after (when next token will be available)
        retry_after = int(60 / rule.requests_per_minute) + 1
        return False, retry_after
    
    def _create_rate_limit_response(self, retry_after: int) -> Response:
        """Create rate limit exceeded response."""
        return Response(
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests, please try again later",
                "retry_after": retry_after
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={
                "Retry-After": str(retry_after),
                "Content-Type": "application/json"
            }
        )
    
    def _add_rate_limit_headers(self, response: Response, key: str, rule: RateLimitRule) -> None:
        """Add rate limit headers to response."""
        if key in self.buckets:
            bucket = self.buckets[key]
            
            # Calculate remaining requests in current window
            now = time.time()
            window_start = now - (rule.window_minutes * 60)
            recent_requests = sum(1 for req_time in bucket.request_history if req_time > window_start)
            remaining = max(0, rule.requests_per_minute - recent_requests)
            
            response.headers["X-RateLimit-Limit"] = str(rule.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining) 
            response.headers["X-RateLimit-Reset"] = str(int(now + 60))
            response.headers["X-RateLimit-Window"] = str(rule.window_minutes * 60)
    
    async def _log_rate_limit_violation(self, request: Request, key: str, rule: RateLimitRule) -> None:
        """Log rate limit violations for monitoring."""
        violation_event = {
            "event_type": "rate_limit_exceeded",
            "timestamp": time.time(),
            "rate_limit_key": key,
            "rule": {
                "requests_per_minute": rule.requests_per_minute,
                "burst_limit": rule.burst_limit,
            },
            "request_path": request.url.path,
            "request_method": request.method,
            "client_ip": getattr(request.state, "client_ip", "unknown"),
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
        }
        
        # Store in request state for potential logging
        if not hasattr(request.state, "rate_limit_violations"):
            request.state.rate_limit_violations = []
        request.state.rate_limit_violations.append(violation_event)
    
    async def _cleanup_expired_buckets(self) -> None:
        """Clean up expired rate limit buckets."""
        now = time.time()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove buckets that haven't been used recently
        expired_keys = []
        cutoff_time = now - (self.cleanup_interval * 2)  # 2x cleanup interval
        
        for key, bucket in self.buckets.items():
            if bucket.last_refill < cutoff_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.buckets[key]
        
        self.last_cleanup = now


# Middleware instance for easy import with default settings
rate_limiting_middleware = RateLimitingMiddleware