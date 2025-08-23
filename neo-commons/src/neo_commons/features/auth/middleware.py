"""FastAPI middleware components for authentication."""

import logging
import time
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from ...core.exceptions.auth import AuthenticationError, AuthorizationError
from ...core.value_objects.identifiers import TenantId
from .dependencies import AuthDependencies, AuthDependencyError
from .entities.auth_context import AuthContext
from .entities.protocols import RealmManagerProtocol

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Authentication middleware for FastAPI applications."""
    
    def __init__(
        self,
        auth_dependencies: AuthDependencies,
        realm_manager: RealmManagerProtocol,
        excluded_paths: Optional[list[str]] = None,
        health_check_paths: Optional[list[str]] = None,
    ):
        """Initialize auth middleware."""
        self.auth_dependencies = auth_dependencies
        self.realm_manager = realm_manager
        
        # Default excluded paths (don't require authentication)
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/ping",
            "/metrics",
            "/auth/login",
            "/auth/logout", 
            "/auth/callback",
            "/auth/refresh",
        ]
        
        # Health check paths (minimal processing)
        self.health_check_paths = health_check_paths or [
            "/health",
            "/ping",
            "/ready",
            "/live",
        ]
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request through auth middleware."""
        start_time = time.time()
        
        # Skip processing for excluded paths
        if self._should_exclude_path(request.url.path):
            response = await call_next(request)
            return self._add_timing_header(response, start_time)
        
        # Fast path for health checks
        if request.url.path in self.health_check_paths:
            response = await call_next(request)
            return self._add_timing_header(response, start_time)
        
        try:
            # Extract and validate tenant
            tenant_id = await self._extract_and_validate_tenant(request)
            
            # Add tenant to request state
            request.state.tenant_id = tenant_id
            
            # Extract auth context if present
            auth_context = await self._extract_auth_context(request)
            if auth_context:
                request.state.auth_context = auth_context
                request.state.user_id = auth_context.user_id
                
                # Log authenticated request
                logger.debug(
                    f"Authenticated request: {request.method} {request.url.path} "
                    f"User: {auth_context.user_id.value} Tenant: {tenant_id.value}"
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response = self._add_security_headers(response)
            
            return self._add_timing_header(response, start_time)
        
        except AuthDependencyError as e:
            logger.warning(f"Auth middleware error: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "authentication_failed",
                    "message": e.detail,
                    "timestamp": time.time(),
                }
            )
        
        except Exception as e:
            logger.error(f"Unexpected middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "internal_server_error",
                    "message": "Authentication processing failed",
                    "timestamp": time.time(),
                }
            )
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from auth processing."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    async def _extract_and_validate_tenant(self, request: Request) -> TenantId:
        """Extract and validate tenant from request."""
        try:
            tenant_id = await self.auth_dependencies._extract_tenant_id(request)
            
            # Validate that tenant realm exists
            realm_config = await self.realm_manager.get_realm_config(tenant_id)
            if not realm_config:
                logger.warning(f"No realm found for tenant: {tenant_id.value}")
                raise AuthDependencyError(
                    "Tenant not found or not configured",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            return tenant_id
        
        except AuthDependencyError:
            raise
        
        except Exception as e:
            logger.error(f"Tenant extraction failed: {e}")
            raise AuthDependencyError(
                "Unable to identify tenant",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    async def _extract_auth_context(self, request: Request) -> Optional[AuthContext]:
        """Extract auth context from request if present."""
        try:
            # Check for Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # Extract token
            token = auth_header.split(" ", 1)[1]
            
            # Get tenant from request state
            tenant_id = request.state.tenant_id
            
            # Get realm config
            realm_config = await self.realm_manager.get_realm_config(tenant_id)
            
            # Validate token and get context
            auth_context = await self.auth_dependencies.token_service.validate_and_cache_token(
                token, realm_config.realm_id
            )
            
            # Validate tenant match
            if auth_context.tenant_id != tenant_id:
                logger.warning(
                    f"Token tenant mismatch: {auth_context.tenant_id.value} != {tenant_id.value}"
                )
                return None
            
            return auth_context
        
        except Exception as e:
            # Log but don't raise - auth context is optional at middleware level
            logger.debug(f"Auth context extraction failed: {e}")
            return None
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        # Prevent caching of authenticated responses
        if hasattr(response, 'headers'):
            response.headers["cache-control"] = "no-cache, no-store, must-revalidate"
            response.headers["pragma"] = "no-cache"
            response.headers["expires"] = "0"
            
            # Security headers
            response.headers["x-content-type-options"] = "nosniff"
            response.headers["x-frame-options"] = "DENY"
            response.headers["x-xss-protection"] = "1; mode=block"
        
        return response
    
    def _add_timing_header(self, response: Response, start_time: float) -> Response:
        """Add request timing header."""
        if hasattr(response, 'headers'):
            processing_time = time.time() - start_time
            response.headers["x-processing-time"] = f"{processing_time:.4f}s"
        
        return response


class TenantIsolationMiddleware:
    """Middleware to enforce tenant data isolation."""
    
    def __init__(self, strict_mode: bool = True):
        """Initialize tenant isolation middleware."""
        self.strict_mode = strict_mode
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Enforce tenant isolation."""
        
        # Skip if no tenant in state (not authenticated)
        if not hasattr(request.state, 'tenant_id'):
            return await call_next(request)
        
        try:
            # Add tenant context to database connections
            # This would integrate with your database service to set schema context
            tenant_id = request.state.tenant_id
            
            # Set tenant context for the request
            # Your database service should use this for schema switching
            request.state.database_context = {
                "tenant_id": tenant_id.value,
                "isolation_mode": "strict" if self.strict_mode else "permissive",
            }
            
            logger.debug(f"Set database context for tenant: {tenant_id.value}")
            
            response = await call_next(request)
            
            return response
        
        except Exception as e:
            logger.error(f"Tenant isolation middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "tenant_isolation_error",
                    "message": "Unable to enforce tenant isolation",
                    "timestamp": time.time(),
                }
            )


class RateLimitingMiddleware:
    """Rate limiting middleware for auth operations."""
    
    def __init__(
        self,
        auth_rate_limit: int = 10,  # requests per minute for auth endpoints
        general_rate_limit: int = 100,  # requests per minute for other endpoints
        window_seconds: int = 60,
    ):
        """Initialize rate limiting middleware."""
        self.auth_rate_limit = auth_rate_limit
        self.general_rate_limit = general_rate_limit
        self.window_seconds = window_seconds
        
        # In-memory rate limiting (use Redis for production)
        self.request_counts = {}
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""
        
        # Get client identifier (IP + user ID if available)
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, 'user_id', None)
        client_key = f"{client_ip}:{user_id.value if user_id else 'anonymous'}"
        
        # Determine rate limit based on path
        is_auth_endpoint = any(
            request.url.path.startswith(path) 
            for path in ["/auth/", "/login", "/logout", "/token"]
        )
        
        rate_limit = self.auth_rate_limit if is_auth_endpoint else self.general_rate_limit
        
        # Check rate limit
        if await self._is_rate_limited(client_key, rate_limit):
            logger.warning(f"Rate limit exceeded for {client_key}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {rate_limit} per minute",
                    "retry_after": self.window_seconds,
                },
                headers={"retry-after": str(self.window_seconds)}
            )
        
        return await call_next(request)
    
    async def _is_rate_limited(self, client_key: str, limit: int) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old entries
        if client_key in self.request_counts:
            self.request_counts[client_key] = [
                timestamp for timestamp in self.request_counts[client_key]
                if timestamp > window_start
            ]
        else:
            self.request_counts[client_key] = []
        
        # Check if limit exceeded
        if len(self.request_counts[client_key]) >= limit:
            return True
        
        # Add current request
        self.request_counts[client_key].append(now)
        return False


def configure_auth_middleware(
    app: FastAPI,
    auth_dependencies: AuthDependencies,
    realm_manager: RealmManagerProtocol,
    enable_rate_limiting: bool = True,
    enable_tenant_isolation: bool = True,
    excluded_paths: Optional[list[str]] = None,
) -> None:
    """Configure all auth middleware on FastAPI app."""
    
    # Rate limiting (first layer)
    if enable_rate_limiting:
        app.add_middleware(RateLimitingMiddleware)
        logger.info("Added rate limiting middleware")
    
    # Tenant isolation
    if enable_tenant_isolation:
        app.add_middleware(TenantIsolationMiddleware, strict_mode=True)
        logger.info("Added tenant isolation middleware")
    
    # Main auth middleware (last layer - closest to routes)
    auth_middleware = AuthMiddleware(
        auth_dependencies=auth_dependencies,
        realm_manager=realm_manager,
        excluded_paths=excluded_paths,
    )
    
    app.middleware("http")(auth_middleware)
    logger.info("Added auth middleware")


# Exception handlers for auth errors

def configure_auth_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers for auth errors."""
    
    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError):
        logger.warning(f"Authentication error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "authentication_failed",
                "message": str(exc),
                "timestamp": time.time(),
            }
        )
    
    @app.exception_handler(AuthorizationError)
    async def authz_exception_handler(request: Request, exc: AuthorizationError):
        logger.warning(f"Authorization error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "authorization_failed", 
                "message": str(exc),
                "timestamp": time.time(),
            }
        )
    
    @app.exception_handler(AuthDependencyError)
    async def auth_dependency_exception_handler(request: Request, exc: AuthDependencyError):
        logger.warning(f"Auth dependency error: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "authentication_error",
                "message": exc.detail,
                "timestamp": time.time(),
            }
        )
    
    logger.info("Configured auth exception handlers")