"""
Authentication dependencies.

ONLY handles authentication and authorization dependency injection.
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ....core.value_objects import UserId, TenantId
from ....core.shared import RequestContext

# Import authentication services (these would be implemented in platform/auth)
# For now, we'll define the interfaces they should implement
from typing import Protocol


class AuthService(Protocol):
    """Authentication service protocol."""
    
    async def validate_user_token(self, token: str) -> dict:
        """Validate user JWT token."""
        ...
    
    async def validate_admin_token(self, token: str) -> dict:
        """Validate admin JWT token."""
        ...
    
    async def validate_service_token(self, token: str) -> dict:
        """Validate internal service token."""
        ...
    
    async def validate_api_key(self, api_key: str) -> dict:
        """Validate public API key."""
        ...


class TenantService(Protocol):
    """Tenant service protocol."""
    
    async def get_tenant_context(self, tenant_id: str) -> dict:
        """Get tenant context information."""
        ...


# Security schemes
bearer_scheme = HTTPBearer()


async def get_auth_service() -> AuthService:
    """Get authentication service instance."""
    # This would be injected from neo_commons.platform container
    # For now, we'll implement a mock service
    from neo_commons.platform.container import get_container
    container = get_container()
    
    # TODO: Replace with actual auth service implementation
    class MockAuthService:
        async def validate_user_token(self, token: str) -> dict:
            # Mock implementation - replace with real JWT validation
            return {
                "user_id": "usr_123456789",
                "tenant_id": "tenant_123",
                "roles": ["user"],
                "permissions": []
            }
        
        async def validate_admin_token(self, token: str) -> dict:
            # Mock implementation - replace with real admin validation
            return {
                "user_id": "adm_123456789",
                "tenant_id": None,  # Admins can access all tenants
                "roles": ["admin"],
                "permissions": ["*"]
            }
        
        async def validate_service_token(self, token: str) -> dict:
            # Mock implementation - replace with service token validation
            return {
                "service_id": "svc_events",
                "permissions": ["internal_api"]
            }
        
        async def validate_api_key(self, api_key: str) -> dict:
            # Mock implementation - replace with API key validation
            return {
                "api_key_id": "key_123",
                "permissions": ["public_read"]
            }
    
    return MockAuthService()


async def get_tenant_service() -> TenantService:
    """Get tenant service instance."""
    from neo_commons.platform.container import get_container
    container = get_container()
    
    # TODO: Replace with actual tenant service implementation
    class MockTenantService:
        async def get_tenant_context(self, tenant_id: str) -> dict:
            return {
                "tenant_id": tenant_id,
                "name": "Example Tenant",
                "status": "active"
            }
    
    return MockTenantService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> RequestContext:
    """
    Get current authenticated user context.
    
    Validates JWT token and returns user context.
    """
    try:
        user_data = await auth_service.validate_user_token(credentials.credentials)
        
        return RequestContext(
            user_id=UserId(user_data["user_id"]),
            tenant_id=TenantId(user_data["tenant_id"]),
            request_id="req_" + "123456789",  # Generate unique request ID
            correlation_id=None,
            roles=user_data.get("roles", []),
            permissions=user_data.get("permissions", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> RequestContext:
    """
    Get current authenticated admin user context.
    
    Validates admin JWT token and returns admin context.
    """
    try:
        admin_data = await auth_service.validate_admin_token(credentials.credentials)
        
        # Verify admin role
        if "admin" not in admin_data.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return RequestContext(
            user_id=UserId(admin_data["user_id"]),
            tenant_id=None,  # Admins have cross-tenant access
            request_id="req_admin_" + "123456789",
            correlation_id=None,
            roles=admin_data.get("roles", []),
            permissions=admin_data.get("permissions", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_tenant_context(
    user_context: RequestContext = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
) -> RequestContext:
    """
    Get tenant context for the current user.
    
    Enriches user context with tenant information.
    """
    try:
        if not user_context.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tenant context available"
            )
        
        tenant_data = await tenant_service.get_tenant_context(
            user_context.tenant_id.value
        )
        
        # Verify tenant is active
        if tenant_data.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is not active"
            )
        
        # Return enriched context
        user_context.metadata = user_context.metadata or {}
        user_context.metadata.update({
            "tenant_name": tenant_data.get("name"),
            "tenant_status": tenant_data.get("status")
        })
        
        return user_context
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant context: {str(e)}"
        )


async def verify_internal_service_token(
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """
    Verify internal service token.
    
    Used for service-to-service communication.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Internal service token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    
    try:
        service_data = await auth_service.validate_service_token(token)
        
        if "internal_api" not in service_data.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Internal API access required"
            )
        
        return service_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token"
        )


async def verify_public_api_key(
    api_key: Optional[str] = Query(None, alias="api_key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """
    Verify public API key.
    
    Accepts API key from query parameter or header.
    """
    # Get API key from query param or header
    key = api_key or x_api_key
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    try:
        key_data = await auth_service.validate_api_key(key)
        
        if "public_read" not in key_data.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public API access required"
            )
        
        return key_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )


# Type aliases for dependency injection
CurrentUserDep = Annotated[RequestContext, Depends(get_current_user)]
AdminUserDep = Annotated[RequestContext, Depends(get_current_admin_user)]
TenantContextDep = Annotated[RequestContext, Depends(get_tenant_context)]
ServiceTokenDep = Annotated[dict, Depends(verify_internal_service_token)]
PublicKeyDep = Annotated[dict, Depends(verify_public_api_key)]