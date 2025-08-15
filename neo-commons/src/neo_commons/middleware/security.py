"""
Security headers middleware for enhanced application security.
"""
import time
import os
from typing import Callable, Dict, Optional, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    
    Features:
    - Content Security Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Strict-Transport-Security (HSTS)
    - Referrer-Policy
    - Permissions-Policy
    - Cross-Origin-Embedder-Policy
    - Cross-Origin-Opener-Policy
    """
    
    def __init__(
        self,
        app,
        *,
        force_https: bool = None,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        content_security_policy: Optional[str] = None,
        frame_options: str = "DENY",
        content_type_options: bool = True,
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[Dict[str, List[str]]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        exclude_paths: Optional[List[str]] = None,
        is_production: bool = None
    ):
        super().__init__(app)
        
        # Auto-detect production if not specified
        if is_production is None:
            is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        self.is_production = is_production
        self.force_https = force_https if force_https is not None else is_production
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.frame_options = frame_options
        self.content_type_options = content_type_options
        self.xss_protection = xss_protection
        self.referrer_policy = referrer_policy
        self.custom_headers = custom_headers or {}
        self.exclude_paths = exclude_paths or []
        
        # Build CSP and Permissions Policy
        self.content_security_policy = content_security_policy or self._build_default_csp()
        self.permissions_policy = permissions_policy or self._build_default_permissions_policy()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Skip security headers for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return response
        
        # Add security headers
        self._add_security_headers(request, response)
        
        return response
    
    def _add_security_headers(self, request: Request, response: Response):
        """Add all security headers to the response."""
        # X-Content-Type-Options
        if self.content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        if self.frame_options:
            response.headers["X-Frame-Options"] = self.frame_options
        
        # X-XSS-Protection (deprecated but still useful for older browsers)
        if self.xss_protection:
            response.headers["X-XSS-Protection"] = self.xss_protection
        
        # Referrer-Policy
        if self.referrer_policy:
            response.headers["Referrer-Policy"] = self.referrer_policy
        
        # Content-Security-Policy
        if self.content_security_policy:
            response.headers["Content-Security-Policy"] = self.content_security_policy
        
        # Permissions-Policy
        if self.permissions_policy:
            policy_string = self._format_permissions_policy(self.permissions_policy)
            response.headers["Permissions-Policy"] = policy_string
        
        # HSTS (only for HTTPS)
        if self._should_add_hsts(request):
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # Cross-Origin policies
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        
        # Custom headers
        for header_name, header_value in self.custom_headers.items():
            response.headers[header_name] = header_value
        
        # Server header removal (don't advertise server software)
        app_name = os.getenv("APP_NAME", "NeoMultiTenant")
        response.headers["Server"] = app_name
    
    def _build_default_csp(self) -> str:
        """Build default Content Security Policy."""
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Relaxed for dev
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ]
        
        # Adjust for development
        if not self.is_production:
            # Allow local development servers
            csp_directives = [directive.replace("'self'", "'self' localhost:* 127.0.0.1:*") 
                            for directive in csp_directives]
            # Remove upgrade-insecure-requests in development
            csp_directives = [d for d in csp_directives if not d.startswith("upgrade-insecure-requests")]
        
        return "; ".join(csp_directives)
    
    def _build_default_permissions_policy(self) -> Dict[str, List[str]]:
        """Build default Permissions Policy."""
        return {
            "accelerometer": [],
            "ambient-light-sensor": [],
            "autoplay": ["self"],
            "battery": [],
            "camera": [],
            "clipboard-read": [],
            "clipboard-write": ["self"],
            "cross-origin-isolated": [],
            "display-capture": [],
            "document-domain": [],
            "encrypted-media": [],
            "execution-while-not-rendered": [],
            "execution-while-out-of-viewport": [],
            "fullscreen": ["self"],
            "gamepad": [],
            "geolocation": [],
            "gyroscope": [],
            "keyboard-map": [],
            "magnetometer": [],
            "microphone": [],
            "midi": [],
            "navigation-override": [],
            "payment": ["self"],
            "picture-in-picture": [],
            "publickey-credentials-get": [],
            "screen-wake-lock": [],
            "sync-xhr": [],
            "usb": [],
            "web-share": [],
            "xr-spatial-tracking": []
        }
    
    def _format_permissions_policy(self, policy: Dict[str, List[str]]) -> str:
        """Format permissions policy dictionary into header string."""
        formatted_policies = []
        
        for feature, allowlist in policy.items():
            if not allowlist:
                # Feature is denied for all origins
                formatted_policies.append(f"{feature}=()")
            else:
                # Feature is allowed for specific origins
                origins = " ".join(f'"{origin}"' if origin != "self" else origin for origin in allowlist)
                formatted_policies.append(f"{feature}=({origins})")
        
        return ", ".join(formatted_policies)
    
    def _should_add_hsts(self, request: Request) -> bool:
        """Determine if HSTS header should be added."""
        if not self.force_https:
            return False
        
        # Check if request is over HTTPS
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https" or
            request.headers.get("x-forwarded-ssl") == "on"
        )
        
        return is_https


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with security considerations.
    
    This extends the basic CORS functionality with additional security checks.
    """
    
    def __init__(
        self,
        app,
        *,
        allowed_origins: List[str],
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        exposed_headers: List[str] = None,
        allow_credentials: bool = False,
        max_age: int = 600,
        strict_origin_check: bool = True
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["*"]
        self.exposed_headers = exposed_headers or []
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        self.strict_origin_check = strict_origin_check
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS with security checks."""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._handle_preflight(request, origin)
        
        # Process normal request
        response = await call_next(request)
        
        # Add CORS headers
        self._add_cors_headers(response, origin)
        
        return response
    
    def _handle_preflight(self, request: Request, origin: Optional[str]) -> Response:
        """Handle preflight OPTIONS request."""
        response = Response(status_code=200)
        
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            
            # Allow methods
            requested_method = request.headers.get("access-control-request-method")
            if requested_method and requested_method in self.allowed_methods:
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            
            # Allow headers
            requested_headers = request.headers.get("access-control-request-headers")
            if requested_headers:
                if "*" in self.allowed_headers:
                    response.headers["Access-Control-Allow-Headers"] = requested_headers
                else:
                    allowed = [h for h in requested_headers.split(", ") if h in self.allowed_headers]
                    if allowed:
                        response.headers["Access-Control-Allow-Headers"] = ", ".join(allowed)
            
            # Max age
            response.headers["Access-Control-Max-Age"] = str(self.max_age)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: Optional[str]):
        """Add CORS headers to response."""
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            
            if self.exposed_headers:
                response.headers["Access-Control-Expose-Headers"] = ", ".join(self.exposed_headers)
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed."""
        if not origin:
            return not self.strict_origin_check
        
        if "*" in self.allowed_origins:
            return True
        
        return origin in self.allowed_origins


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.
    
    Note: This is a basic implementation. For production, consider using
    Redis-based rate limiting for distributed scenarios.
    """
    
    def __init__(
        self,
        app,
        *,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        exclude_paths: List[str] = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        
        # Simple in-memory storage (use Redis in production)
        self._request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        # Check rate limits
        if self._is_rate_limited(client_ip):
            return Response(
                content='{"error": "Rate limit exceeded"}',
                status_code=429,
                headers={"content-type": "application/json"}
            )
        
        # Record request
        self._record_request(client_ip)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client IP is rate limited."""
        current_time = int(time.time())
        
        if client_ip not in self._request_counts:
            return False
        
        # Clean old entries and check limits
        counts = self._request_counts[client_ip]
        recent_requests = [t for t in counts if current_time - t < 3600]
        self._request_counts[client_ip] = recent_requests
        
        minute_requests = len([t for t in recent_requests if current_time - t < 60])
        hour_requests = len(recent_requests)
        
        return minute_requests >= self.requests_per_minute or hour_requests >= self.requests_per_hour
    
    def _record_request(self, client_ip: str):
        """Record request timestamp."""
        current_time = int(time.time())
        if client_ip not in self._request_counts:
            self._request_counts[client_ip] = []
        self._request_counts[client_ip].append(current_time)