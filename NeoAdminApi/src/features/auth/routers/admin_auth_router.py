"""Admin-specific auth router using neo-commons with only parameter passing."""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Depends
from neo_commons.core.value_objects.identifiers import TenantId
from neo_commons.features.auth.dependencies import AuthDependencies, get_current_platform_admin
from neo_commons.features.auth.entities.auth_context import AuthContext
from ....common.dependencies import get_database_service
from ....common.config import get_config_provider

logger = logging.getLogger(__name__)

# Create admin auth router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# Admin-specific dependency implementations
def get_auth_dependencies() -> AuthDependencies:
    """Get auth dependencies from global neo-commons configuration."""
    from neo_commons.features.auth.dependencies import get_auth_dependencies as get_global_auth_deps
    return get_global_auth_deps()


async def extract_tenant_id(request: Request) -> Optional[TenantId]:
    """Extract tenant ID from request headers for admin context (optional)."""
    tenant_header = request.headers.get("x-tenant-id")
    if tenant_header:
        return TenantId(tenant_header)
    return None  # Admin API allows platform-level access without tenant



# Configure platform admin realm for neo-commons
async def configure_platform_admin_realm():
    """Configure platform admin realm in neo-commons at startup."""
    from neo_commons.core.value_objects.identifiers import RealmId
    from neo_commons.features.auth.entities.keycloak_config import KeycloakConfig
    from neo_commons.features.auth.dependencies import get_auth_dependencies as get_global_auth_deps
    
    # Use centralized configuration
    config_provider = get_config_provider()
    env_config = config_provider.config
    auth_deps = get_global_auth_deps()
    
    # Register platform admin realm configuration
    platform_realm_id = RealmId(env_config.keycloak_realm)
    platform_config = KeycloakConfig(
        server_url=env_config.keycloak_server_url,
        realm_name=env_config.keycloak_realm,
        client_id=env_config.keycloak_client_id,
        client_secret=env_config.keycloak_client_secret,
        audience=env_config.keycloak_client_id,
        verify_audience=False,  # Disable for platform admin
        require_https=False,  # Allow HTTP in development
    )
    
    auth_deps.realm_manager.register_custom_realm_config(
        platform_realm_id, platform_config, tenant_id=None
    )


# Authentication endpoints - all forward to neo-commons with admin-specific config
from neo_commons.features.auth.models.requests import (
    LoginRequest, RefreshTokenRequest, LogoutRequest, 
    RegisterRequest, ForgotPasswordRequest
)
from neo_commons.features.auth.models.responses import (
    LoginResponse, TokenResponse, MessageResponse, UserProfileResponse,
    RegisterResponse, PasswordResetResponse, SessionInfoResponse, 
    UserValidationResponse
)

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    auth_deps: AuthDependencies = Depends(get_auth_dependencies),
    user_service = Depends(lambda: None),  # Will inject manually
    db_service = Depends(get_database_service),
) -> LoginResponse:
    """Login with admin-specific tenant extraction (optional tenant ID)."""
    from fastapi import HTTPException, status
    from neo_commons.core.exceptions.auth import (
        InvalidCredentialsError, AuthenticationError
    )
    from neo_commons.core.value_objects.identifiers import RealmId
    from neo_commons.features.auth.entities.keycloak_config import KeycloakConfig
    
    try:
        # Extract tenant ID (optional for admin)
        tenant_id = await extract_tenant_id(request)
        
        # For admin API: if no tenant_id, use platform admin realm
        if tenant_id is None:
            # Use registered platform admin realm with centralized configuration
            config_provider = get_config_provider()
            env_config = config_provider.config
            realm_id = RealmId(env_config.keycloak_realm)
            
            # Get realm configuration from registered platform admin realm  
            realm_config = await auth_deps.realm_manager.get_realm_config_by_id(realm_id)
        else:
            # Regular tenant-specific realm
            realm_config = await auth_deps.realm_manager.get_realm_config(tenant_id)
            realm_id = realm_config.realm_id
        
        if not realm_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authentication configuration not found"
            )
        
        # realm_config is already a KeycloakConfig, use it directly
        keycloak_config = realm_config
        
        # Authenticate user
        from neo_commons.features.auth.adapters.keycloak_openid import KeycloakOpenIDAdapter
        async with KeycloakOpenIDAdapter(keycloak_config) as openid_client:
            jwt_token = await openid_client.authenticate(
                login_data.username, login_data.password
            )
            
            # Validate token and get auth context
            auth_context = await auth_deps.token_service.validate_and_cache_token(
                jwt_token.access_token, keycloak_config.realm_id or realm_id
            )
            
            # Create token response
            from neo_commons.features.auth.models.responses import TokenResponse
            token_response = TokenResponse(
                access_token=jwt_token.access_token,
                refresh_token=jwt_token.refresh_token,
                token_type=jwt_token.token_type,
                expires_in=jwt_token.expires_in,
                refresh_expires_in=jwt_token.refresh_expires_in,
                scope=jwt_token.scope,
            )
            
            # Create complete user profile response using neo-commons
            # Set schema name for admin API
            request.state.database_schema = "admin"
            user_profile = await UserProfileResponse.from_auth_context(auth_context, "admin", db_service)
            
            logger.info(f"Admin user {login_data.username} logged in successfully")
            
            return LoginResponse(
                tokens=token_response,
                user=user_profile,
                session_id=auth_context.session_id,
                message="Login successful",
            )
    
    except InvalidCredentialsError as e:
        logger.warning(f"Login failed for user {login_data.username}: Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    except AuthenticationError as e:
        logger.error(f"Login failed for user {login_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service temporarily unavailable"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    auth_deps: AuthDependencies = Depends(get_auth_dependencies),
) -> TokenResponse:
    """Refresh token with admin-specific configuration."""
    from neo_commons.features.auth.routers.auth_router import refresh_token as neo_refresh
    return await neo_refresh(request, refresh_data, auth_deps)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    auth_deps: AuthDependencies = Depends(get_auth_dependencies),
    current_user = Depends(get_current_platform_admin),
) -> MessageResponse:
    """Logout with admin-specific configuration."""
    from neo_commons.features.auth.routers.auth_router import logout as neo_logout
    return await neo_logout(request, logout_data, auth_deps, current_user)


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    request: Request,
    current_user: AuthContext = Depends(get_current_platform_admin),
    db_service = Depends(get_database_service),
) -> UserProfileResponse:
    """Get current user profile with rich permissions."""
    from neo_commons.features.auth.routers.auth_router import get_current_user_profile as neo_profile
    return await neo_profile(request, current_user, db_service)


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: Request,
    registration_data: RegisterRequest,
    registration_service = Depends(lambda: None),  # Admin API may not need registration
) -> RegisterResponse:
    """User registration with admin-specific configuration."""
    from neo_commons.features.auth.routers.auth_router import register as neo_register
    return await neo_register(request, registration_data, registration_service)


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    password_reset_service = Depends(lambda: None),  # Admin API may not need password reset
) -> PasswordResetResponse:
    """Forgot password with admin-specific configuration."""
    from neo_commons.features.auth.routers.auth_router import forgot_password as neo_forgot
    return await neo_forgot(request, forgot_data, password_reset_service)


@router.get("/session", response_model=SessionInfoResponse)
async def get_session_info(
    request: Request,
    current_user = Depends(get_current_platform_admin),
) -> SessionInfoResponse:
    """Get current session information."""
    from neo_commons.features.auth.routers.auth_router import get_session_info as neo_session
    return await neo_session(request, current_user)


@router.get("/validate/username/{username}", response_model=UserValidationResponse)
async def validate_username(
    username: str,
    request: Request,
    registration_service = Depends(lambda: None),
) -> UserValidationResponse:
    """Validate username availability."""
    from neo_commons.features.auth.routers.auth_router import validate_username as neo_validate_username
    return await neo_validate_username(username, request, registration_service)


@router.get("/validate/email/{email}", response_model=UserValidationResponse)
async def validate_email(
    email: str,
    request: Request,
    registration_service = Depends(lambda: None),
) -> UserValidationResponse:
    """Validate email availability."""
    from neo_commons.features.auth.routers.auth_router import validate_email as neo_validate_email
    return await neo_validate_email(email, request, registration_service)