"""Complete authentication integration example.

This example demonstrates how to integrate the complete neo-commons auth system
with login, register, password reset, and all authentication features.
"""

from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

from neo_commons.features.auth import (
    # Core factory
    create_auth_service_factory,
    AuthServiceFactory,
    
    # Services
    UserRegistrationService,
    PasswordResetService,
    
    # API Router and models
    auth_router,
    LoginRequest,
    RegisterRequest,
    LoginResponse,
    
    # Middleware and dependencies
    configure_auth_middleware,
    configure_auth_exception_handlers,
    AuthDependencies,
    require_permission,
    get_current_user,
)


# Global auth factory (in real apps, use dependency injection)
auth_factory: AuthServiceFactory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global auth_factory
    
    # Initialize auth factory
    auth_factory = create_auth_service_factory(
        keycloak_server_url="http://localhost:8080",
        keycloak_admin_username="admin", 
        keycloak_admin_password="admin",
        redis_url="redis://localhost:6379",
        redis_password="redis",
    )
    
    # Initialize all services
    await auth_factory.initialize_all_services()
    
    yield
    
    # Cleanup
    if auth_factory:
        await auth_factory.cleanup()


# Create FastAPI app with auth integration
app = FastAPI(
    title="Complete Auth Integration Example",
    version="1.0.0",
    lifespan=lifespan,
)


# Override auth router dependencies
def get_auth_dependencies_override() -> AuthDependencies:
    """Get configured auth dependencies."""
    if not auth_factory:
        raise RuntimeError("Auth factory not initialized")
    return auth_factory._auth_dependencies


def get_user_registration_service_override() -> UserRegistrationService:
    """Get user registration service."""
    if not auth_factory:
        raise RuntimeError("Auth factory not initialized")
    
    keycloak_admin = auth_factory.get_keycloak_service()
    user_mapper = auth_factory.get_user_mapper()
    
    return UserRegistrationService(
        keycloak_admin=keycloak_admin,
        user_mapper=user_mapper,
    )


def get_password_reset_service_override() -> PasswordResetService:
    """Get password reset service.""" 
    if not auth_factory:
        raise RuntimeError("Auth factory not initialized")
    
    keycloak_admin = auth_factory.get_keycloak_service()
    return PasswordResetService(keycloak_admin=keycloak_admin)


# Override auth router dependencies
auth_router.dependency_overrides = {
    "get_auth_dependencies": get_auth_dependencies_override,
    "get_user_registration_service": get_user_registration_service_override,
    "get_password_reset_service": get_password_reset_service_override,
}

# Include auth router
app.include_router(auth_router)

# Configure auth middleware
@app.on_event("startup") 
async def configure_auth():
    """Configure authentication middleware and exception handlers."""
    if auth_factory:
        auth_deps = await auth_factory.get_auth_dependencies()
        realm_manager = await auth_factory.get_realm_manager()
        
        # Configure middleware
        configure_auth_middleware(
            app=app,
            auth_dependencies=auth_deps,
            realm_manager=realm_manager,
            enable_rate_limiting=True,
            enable_tenant_isolation=True,
        )
        
        # Configure exception handlers
        configure_auth_exception_handlers(app)


# Protected route examples
@app.get("/protected")
async def protected_route(
    current_user = Depends(get_current_user)
):
    """Example protected route."""
    return {
        "message": "This is a protected route",
        "user_id": current_user.user_id.value,
        "tenant_id": current_user.tenant_id.value,
    }


@app.get("/admin-only") 
async def admin_only_route(
    current_user = Depends(require_permission("admin:access"))
):
    """Admin-only route."""
    return {
        "message": "This is an admin-only route",
        "user_id": current_user.user_id.value,
    }


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# API Usage Examples
"""
Complete Auth API Usage Examples:

# 1. User Registration
POST /auth/register
{
    "email": "user@example.com",
    "username": "testuser",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
}

# 2. User Login  
POST /auth/login
{
    "username": "testuser",
    "password": "SecurePass123!"
}

# 3. Token Refresh
POST /auth/refresh
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUz..."
}

# 4. Get User Profile
GET /auth/me
Headers: Authorization: Bearer <access_token>

# 5. Logout
POST /auth/logout
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUz..."
}
Headers: Authorization: Bearer <access_token>

# 6. Forgot Password
POST /auth/forgot-password
{
    "email": "user@example.com"
}

# 7. Username Validation
GET /auth/validate/username/testuser

# 8. Email Validation
GET /auth/validate/email/user@example.com

# 9. Session Info
GET /auth/session
Headers: Authorization: Bearer <access_token>

# 10. Protected Route Access
GET /protected
Headers: Authorization: Bearer <access_token>

# 11. Permission-based Route
GET /admin-only
Headers: Authorization: Bearer <access_token>
"""


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "complete_auth_integration:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )