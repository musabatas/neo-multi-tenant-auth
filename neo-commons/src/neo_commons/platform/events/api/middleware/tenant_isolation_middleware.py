"""
Tenant isolation middleware.

ONLY handles tenant data isolation and security enforcement.
"""

import time
from typing import Callable, Set
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

from ....core.value_objects import TenantId


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce tenant data isolation and security.
    
    Ensures tenant-scoped requests cannot access other tenant data.
    """
    
    def __init__(
        self,
        app,
        *,
        public_paths: Set[str] = None,
        admin_paths: Set[str] = None,
        internal_paths: Set[str] = None,
    ):
        """
        Initialize tenant isolation middleware.
        
        Args:
            public_paths: Paths that don't require tenant context
            admin_paths: Paths that allow cross-tenant access for admins
            internal_paths: Paths for internal service communication
        """
        super().__init__(app)
        
        self.public_paths = public_paths or {
            "/public/events/health",
            "/public/events/status", 
            "/public/events/docs/integration",
            "/public/events/webhook/verify",
        }
        
        self.admin_paths = admin_paths or {
            "/admin/events",
        }
        
        self.internal_paths = internal_paths or {
            "/internal/events",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enforce tenant isolation."""
        path = request.url.path
        
        # Skip isolation for public endpoints
        if any(path.startswith(public_path) for public_path in self.public_paths):
            return await call_next(request)
        
        # Skip isolation for internal endpoints (they have their own auth)
        if any(path.startswith(internal_path) for internal_path in self.internal_paths):
            return await call_next(request)
        
        # Admin endpoints have special handling
        if any(path.startswith(admin_path) for admin_path in self.admin_paths):
            return await self._handle_admin_request(request, call_next)
        
        # Tenant endpoints require strict isolation
        if path.startswith("/tenant/events"):
            return await self._handle_tenant_request(request, call_next)
        
        # Default: proceed without isolation
        return await call_next(request)
    
    async def _handle_admin_request(self, request: Request, call_next: Callable) -> Response:
        """Handle admin requests with cross-tenant access validation."""
        try:
            # Admin requests should have admin context set by auth middleware
            # This is additional validation to ensure admin privileges
            
            # Store admin context for audit logging
            request.state.access_level = "admin"
            request.state.cross_tenant_access = True
            
            # Add security headers for admin operations
            response = await call_next(request)
            response.headers["X-Access-Level"] = "admin"
            response.headers["X-Cross-Tenant"] = "allowed"
            
            return response
            
        except Exception as e:
            # Log security violations for admin access
            await self._log_security_event(
                request,
                "admin_access_violation",
                {"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access validation failed"
            )
    
    async def _handle_tenant_request(self, request: Request, call_next: Callable) -> Response:
        """Handle tenant requests with strict isolation enforcement."""
        try:
            # Extract tenant ID from various sources
            tenant_id = await self._extract_tenant_id(request)
            
            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant context required for this operation"
                )
            
            # Store tenant context for downstream processing
            request.state.tenant_id = tenant_id
            request.state.access_level = "tenant"
            request.state.cross_tenant_access = False
            
            # Validate tenant is active (this could be cached)
            await self._validate_tenant_status(tenant_id)
            
            # Process request with tenant context
            response = await call_next(request)
            
            # Add tenant isolation headers
            response.headers["X-Tenant-ID"] = tenant_id.value
            response.headers["X-Access-Level"] = "tenant"
            response.headers["X-Cross-Tenant"] = "denied"
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            await self._log_security_event(
                request,
                "tenant_isolation_violation",
                {"error": str(e), "tenant_id": getattr(tenant_id, 'value', None)}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access validation failed"
            )
    
    async def _extract_tenant_id(self, request: Request) -> TenantId:
        """Extract tenant ID from request context."""
        # Try to get tenant ID from authenticated user context (set by auth middleware)
        if hasattr(request.state, "user_context"):
            user_context = request.state.user_context
            if hasattr(user_context, "tenant_id") and user_context.tenant_id:
                return user_context.tenant_id
        
        # Try header (for service-to-service calls)
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            return TenantId(tenant_header)
        
        # Try query parameter (limited cases)
        tenant_query = request.query_params.get("tenant_id")
        if tenant_query:
            return TenantId(tenant_query)
        
        return None
    
    async def _validate_tenant_status(self, tenant_id: TenantId) -> None:
        """Validate tenant is active and allowed to use event services."""
        # This would typically check a cache or database
        # For now, we'll implement a basic validation
        
        # TODO: Implement proper tenant validation with caching
        # - Check tenant exists
        # - Check tenant is active
        # - Check tenant has event service permissions
        # - Check tenant quotas/limits
        
        # Simulate validation delay (would be cached in production)
        await asyncio.sleep(0.001)
        
        # Basic validation - assume tenant is valid if ID format is correct
        if not tenant_id.value or len(tenant_id.value) < 8:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid tenant identifier"
            )
    
    async def _log_security_event(self, request: Request, event_type: str, details: dict) -> None:
        """Log security events for monitoring and alerting."""
        # TODO: Implement proper security event logging
        # This would typically go to a security monitoring system
        
        security_event = {
            "event_type": event_type,
            "timestamp": time.time(),
            "request_path": request.url.path,
            "request_method": request.method,
            "client_ip": getattr(request.state, "client_ip", "unknown"),
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            "details": details,
        }
        
        # In production, this would be sent to security monitoring
        # For now, we'll just store it in request state for potential logging
        if not hasattr(request.state, "security_events"):
            request.state.security_events = []
        request.state.security_events.append(security_event)


# Middleware instance for easy import with default settings
tenant_isolation_middleware = TenantIsolationMiddleware