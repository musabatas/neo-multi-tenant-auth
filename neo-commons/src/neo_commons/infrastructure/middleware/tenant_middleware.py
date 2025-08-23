"""Tenant context middleware for multi-tenant FastAPI applications.

Provides tenant isolation and context management with automatic schema resolution
and request routing based on tenant identification.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ...core.value_objects import TenantId
from ...core.shared.context import RequestContext
from ...core.exceptions import TenantNotFoundError, AuthorizationError
from ...features.tenants.services import TenantService
from ...features.cache.services import CacheService
from ...features.database.services import DatabaseService

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for tenant context management and isolation."""
    
    def __init__(
        self,
        app,
        tenant_service: TenantService,
        cache_service: CacheService,
        database_service: DatabaseService,
        tenant_header: str = "X-Tenant-ID",
        subdomain_extraction: bool = False,
        exempt_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.tenant_service = tenant_service
        self.cache_service = cache_service
        self.database_service = database_service
        self.tenant_header = tenant_header
        self.subdomain_extraction = subdomain_extraction
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/metrics",
            "/admin"  # Platform admin endpoints
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process tenant context for incoming requests."""
        
        # Skip tenant resolution for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        try:
            # Extract tenant identifier from request
            tenant_id = await self._extract_tenant_id(request)
            
            if tenant_id:
                # Validate and load tenant context
                tenant_context = await self._load_tenant_context(tenant_id)
                
                # Set tenant context in request state
                request.state.tenant_id = tenant_id
                request.state.tenant_context = tenant_context
                
                # Configure database schema for tenant
                await self._configure_tenant_schema(tenant_id, tenant_context)
                
                # Update request context if it exists
                if hasattr(request.state, 'user_context'):
                    request.state.user_context.tenant_id = tenant_id
                
                logger.debug(
                    f"Tenant context configured: tenant_id={tenant_id}, "
                    f"schema={tenant_context.get('schema_name')}, "
                    f"path={request.url.path}"
                )
            else:
                # Handle requests without tenant context
                if self._requires_tenant(request):
                    raise TenantNotFoundError("Tenant identification required")
                
                request.state.tenant_id = None
                request.state.tenant_context = None
        
        except TenantNotFoundError as e:
            logger.warning(f"Tenant resolution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except AuthorizationError as e:
            logger.warning(f"Tenant access denied: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal tenant resolution error"
            )
        
        return await call_next(request)
    
    async def _extract_tenant_id(self, request: Request) -> Optional[TenantId]:
        """Extract tenant ID from request headers, subdomain, or path."""
        
        # Method 1: Extract from header
        tenant_header_value = request.headers.get(self.tenant_header)
        if tenant_header_value:
            return TenantId(tenant_header_value)
        
        # Method 2: Extract from subdomain (if enabled)
        if self.subdomain_extraction:
            host = request.headers.get("Host", "")
            if host:
                subdomain = self._extract_subdomain(host)
                if subdomain and subdomain != "www":
                    return TenantId(subdomain)
        
        # Method 3: Extract from path parameter
        path_segments = request.url.path.strip("/").split("/")
        if len(path_segments) >= 3 and path_segments[0] == "api" and path_segments[1] == "tenant":
            return TenantId(path_segments[2])
        
        # Method 4: Extract from user context (if authenticated)
        if hasattr(request.state, 'user_context') and request.state.user_context:
            return request.state.user_context.tenant_id
        
        return None
    
    async def _load_tenant_context(self, tenant_id: TenantId) -> Dict[str, Any]:
        """Load and validate tenant context with caching."""
        
        # Check cache first
        cache_key = f"tenant_context:{tenant_id}"
        cached_context = await self.cache_service.get(cache_key)
        
        if cached_context:
            return cached_context
        
        # Load tenant from service
        tenant = await self.tenant_service.get_tenant(tenant_id)
        
        if not tenant:
            raise TenantNotFoundError(f"Tenant not found: {tenant_id}")
        
        if not tenant.is_active:
            raise AuthorizationError(f"Tenant is not active: {tenant_id}")
        
        # Build tenant context
        tenant_context = {
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "organization_id": str(tenant.organization_id),
            "schema_name": f"tenant_{tenant.slug}",
            "region": tenant.region,
            "subscription_plan": tenant.subscription_plan,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None
        }
        
        # Cache tenant context
        await self.cache_service.set(
            cache_key,
            tenant_context,
            ttl=1800  # 30 minutes
        )
        
        return tenant_context
    
    async def _configure_tenant_schema(self, tenant_id: TenantId, tenant_context: Dict[str, Any]) -> None:
        """Configure database schema for tenant-specific operations."""
        schema_name = tenant_context.get("schema_name")
        
        if schema_name:
            # Set schema context in database service
            await self.database_service.set_schema_context(schema_name)
            
            logger.debug(f"Database schema configured: {schema_name} for tenant {tenant_id}")
    
    def _extract_subdomain(self, host: str) -> Optional[str]:
        """Extract subdomain from host header."""
        # Remove port if present
        host = host.split(":")[0]
        
        # Split by dots and get first part as subdomain
        parts = host.split(".")
        
        if len(parts) > 2:  # e.g., tenant.example.com
            return parts[0]
        
        return None
    
    def _requires_tenant(self, request: Request) -> bool:
        """Check if the request path requires tenant context."""
        # Tenant API endpoints require tenant context
        if request.url.path.startswith("/api/tenant/"):
            return True
        
        # Check for tenant-specific endpoints
        tenant_paths = ["/api/v1/", "/tenant/", "/app/"]
        return any(request.url.path.startswith(path) for path in tenant_paths)


class MultiTenantDatabaseMiddleware(BaseHTTPMiddleware):
    """Specialized middleware for tenant database schema management."""
    
    def __init__(self, app, database_service: DatabaseService):
        super().__init__(app)
        self.database_service = database_service
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Ensure proper database schema context throughout request."""
        
        # Get tenant context from previous middleware
        tenant_context = getattr(request.state, 'tenant_context', None)
        
        if tenant_context:
            schema_name = tenant_context.get("schema_name")
            
            # Set schema for the entire request lifecycle
            async with self.database_service.schema_context(schema_name):
                return await call_next(request)
        
        return await call_next(request)