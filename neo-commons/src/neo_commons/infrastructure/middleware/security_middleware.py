"""Security middleware for FastAPI applications.

Provides CORS handling, rate limiting, security headers, and request validation
for enhanced application security and compliance.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from starlette.responses import Response
from collections import defaultdict, deque
from datetime import datetime, timedelta
import ipaddress
import re

from ...core.exceptions import SecurityError, RateLimitExceededError
from ...features.cache.services import CacheService

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for FastAPI applications."""
    
    def __init__(
        self,
        app,
        enable_security_headers: bool = True,
        enable_request_validation: bool = True,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        blocked_user_agents: Optional[List[str]] = None,
        blocked_ips: Optional[List[str]] = None,
        trusted_proxies: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.enable_security_headers = enable_security_headers
        self.enable_request_validation = enable_request_validation
        self.max_request_size = max_request_size
        self.blocked_user_agents = blocked_user_agents or []
        self.blocked_ips = set(blocked_ips or [])
        self.trusted_proxies = set(trusted_proxies or [])
        
        # Compile user agent patterns
        self.blocked_ua_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.blocked_user_agents
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply security checks and headers."""
        
        try:
            # Validate request
            if self.enable_request_validation:
                await self._validate_request(request)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            if self.enable_security_headers:
                self._add_security_headers(response)
            
            return response
        
        except SecurityError as e:
            logger.warning(f"Security violation: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            raise
    
    async def _validate_request(self, request: Request) -> None:
        """Validate incoming request for security issues."""
        
        # Check request size
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_request_size:
            raise SecurityError(f"Request too large: {content_length} bytes")
        
        # Check client IP
        client_ip = self._get_real_client_ip(request)
        if client_ip in self.blocked_ips:
            raise SecurityError(f"Blocked IP address: {client_ip}")
        
        # Check user agent
        user_agent = request.headers.get("User-Agent", "")
        if any(pattern.search(user_agent) for pattern in self.blocked_ua_patterns):
            raise SecurityError("Blocked user agent")
        
        # Check for suspicious patterns in URL
        if self._has_suspicious_patterns(str(request.url)):
            raise SecurityError("Suspicious URL pattern detected")
        
        # Validate headers
        self._validate_headers(request)
    
    def _get_real_client_ip(self, request: Request) -> str:
        """Get the real client IP, accounting for proxies."""
        # Check X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP (original client)
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            for ip in ips:
                try:
                    # Validate IP format
                    ipaddress.ip_address(ip)
                    # Skip trusted proxies
                    if ip not in self.trusted_proxies:
                        return ip
                except ValueError:
                    continue
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            try:
                ipaddress.ip_address(real_ip)
                return real_ip
            except ValueError:
                pass
        
        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _has_suspicious_patterns(self, url: str) -> bool:
        """Check for suspicious patterns in URL."""
        suspicious_patterns = [
            r"\.\.[\/\\]",  # Directory traversal
            r"<script",       # XSS attempts
            r"javascript:",   # JavaScript injection
            r"data:.*base64", # Data URI attacks
            r"\x00",          # Null byte injection
        ]
        
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in suspicious_patterns)
    
    def _validate_headers(self, request: Request) -> None:
        """Validate request headers for security issues."""
        
        # Check for excessively long headers
        for name, value in request.headers.items():
            if len(name) > 256 or len(value) > 8192:
                raise SecurityError(f"Header too long: {name}")
            
            # Check for null bytes in headers
            if "\x00" in name or "\x00" in value:
                raise SecurityError("Null byte in header")
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "font-src 'self' https:; "
                "frame-ancestors 'none';"
            ),
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=()"
            )
        }
        
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value


class CORSMiddleware(StarletteCORSMiddleware):
    """Enhanced CORS middleware with additional security features."""
    
    def __init__(
        self,
        app,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        allow_origin_regex: str = None,
        expose_headers: List[str] = None,
        max_age: int = 600,
        log_cors_rejections: bool = True
    ):
        self.log_cors_rejections = log_cors_rejections
        
        super().__init__(
            app=app,
            allow_origins=allow_origins or [],
            allow_methods=allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=allow_headers or ["*"],
            allow_credentials=allow_credentials,
            allow_origin_regex=allow_origin_regex,
            expose_headers=expose_headers or [],
            max_age=max_age
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Enhanced CORS handling with logging."""
        origin = request.headers.get("origin")
        
        # Log CORS rejections if enabled
        if self.log_cors_rejections and origin:
            if not self.is_allowed_origin(origin):
                logger.warning(
                    f"CORS request rejected: origin={origin}, path={request.url.path}"
                )
        
        return await super().dispatch(request, call_next)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with multiple strategies."""
    
    def __init__(
        self,
        app,
        cache_service: CacheService,
        default_rate_limit: str = "100/minute",
        burst_rate_limit: str = "20/second",
        rate_limit_by: str = "ip",  # ip, user, tenant
        exempt_paths: Optional[List[str]] = None,
        custom_limits: Optional[Dict[str, str]] = None,
        enable_burst_protection: bool = True
    ):
        super().__init__(app)
        self.cache_service = cache_service
        self.default_rate_limit = self._parse_rate_limit(default_rate_limit)
        self.burst_rate_limit = self._parse_rate_limit(burst_rate_limit) if enable_burst_protection else None
        self.rate_limit_by = rate_limit_by
        self.exempt_paths = exempt_paths or ["/health", "/metrics"]
        self.custom_limits = {k: self._parse_rate_limit(v) for k, v in (custom_limits or {}).items()}
        
        # In-memory backup for high-frequency checks
        self.local_counters = defaultdict(lambda: defaultdict(deque))
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting."""
        
        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        try:
            # Get rate limit key
            limit_key = self._get_rate_limit_key(request)
            
            # Check rate limits
            await self._check_rate_limits(request, limit_key)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            self._add_rate_limit_headers(response, limit_key)
            
            return response
        
        except RateLimitExceededError as e:
            logger.warning(
                f"Rate limit exceeded: key={limit_key}, path={request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.default_rate_limit[0]),
                    "X-RateLimit-Remaining": "0"
                }
            )
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key based on configuration."""
        
        if self.rate_limit_by == "ip":
            client_ip = self._get_client_ip(request)
            return f"rate_limit:ip:{client_ip}"
        
        elif self.rate_limit_by == "user":
            user_context = getattr(request.state, 'user_context', None)
            if user_context and user_context.user_id:
                return f"rate_limit:user:{user_context.user_id}"
            else:
                # Fallback to IP for unauthenticated requests
                client_ip = self._get_client_ip(request)
                return f"rate_limit:ip:{client_ip}"
        
        elif self.rate_limit_by == "tenant":
            tenant_context = getattr(request.state, 'tenant_context', None)
            if tenant_context and tenant_context.get('tenant_id'):
                return f"rate_limit:tenant:{tenant_context['tenant_id']}"
            else:
                # Fallback to IP for non-tenant requests
                client_ip = self._get_client_ip(request)
                return f"rate_limit:ip:{client_ip}"
        
        else:
            # Default to IP
            client_ip = self._get_client_ip(request)
            return f"rate_limit:ip:{client_ip}"
    
    async def _check_rate_limits(self, request: Request, limit_key: str) -> None:
        """Check if request exceeds rate limits."""
        current_time = time.time()
        
        # Check burst rate limit first (if enabled)
        if self.burst_rate_limit:
            burst_key = f"{limit_key}:burst"
            await self._check_single_rate_limit(
                burst_key, self.burst_rate_limit, current_time
            )
        
        # Check default rate limit
        await self._check_single_rate_limit(
            limit_key, self.default_rate_limit, current_time
        )
        
        # Check custom limits for specific paths
        for path_pattern, limit in self.custom_limits.items():
            if request.url.path.startswith(path_pattern):
                custom_key = f"{limit_key}:{path_pattern}"
                await self._check_single_rate_limit(
                    custom_key, limit, current_time
                )
    
    async def _check_single_rate_limit(
        self, 
        key: str, 
        limit: tuple, 
        current_time: float
    ) -> None:
        """Check a single rate limit."""
        limit_count, limit_window = limit
        window_start = current_time - limit_window
        
        # Use local counter for high-frequency checks
        local_key = f"{key}:{int(current_time // limit_window)}"
        request_times = self.local_counters[local_key]['times']
        
        # Clean old entries
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # Check if limit exceeded
        if len(request_times) >= limit_count:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {limit_count} requests per {limit_window} seconds"
            )
        
        # Record this request
        request_times.append(current_time)
        
        # Also update cache for persistence (async)
        try:
            await self.cache_service.increment(
                key, 
                ttl=int(limit_window)
            )
        except Exception as e:
            logger.warning(f"Failed to update rate limit cache: {e}")
    
    def _parse_rate_limit(self, rate_limit_str: str) -> tuple:
        """Parse rate limit string (e.g., '100/minute') to (count, seconds)."""
        parts = rate_limit_str.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid rate limit format: {rate_limit_str}")
        
        count = int(parts[0])
        period = parts[1].lower()
        
        period_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        if period not in period_map:
            raise ValueError(f"Invalid period: {period}")
        
        return count, period_map[period]
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _add_rate_limit_headers(self, response: Response, limit_key: str) -> None:
        """Add rate limit headers to response."""
        limit_count, limit_window = self.default_rate_limit
        
        # Calculate remaining requests (simplified)
        remaining = max(0, limit_count - 1)  # Approximate
        
        response.headers.update({
            "X-RateLimit-Limit": str(limit_count),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time() + limit_window))
        })