"""Authentication API router."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ....core.exceptions.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ....core.value_objects.identifiers import TenantId, UserId
from ..dependencies import AuthDependencies
from ..entities.auth_context import AuthContext
from ..entities.keycloak_config import KeycloakConfig
from ..models.requests import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from ..models.responses import (
    ErrorResponse,
    LoginResponse,
    MessageResponse,
    PasswordResetResponse,
    RegisterResponse,
    SessionInfoResponse,
    TokenResponse,
    UserProfileResponse,
    UserValidationResponse,
)
from ...database.services.database_service import DatabaseManager
from ..services.password_reset_service import PasswordResetService
from ..services.user_registration_service import UserRegistrationService

logger = logging.getLogger(__name__)

# FastAPI router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# Dependency function for database service
async def get_database_service():
    """Get database service instance."""
    return await DatabaseManager.get_instance()

# Security scheme
security = HTTPBearer(auto_error=False)


# Dependency injection helpers
def get_auth_dependencies() -> AuthDependencies:
    """Get auth dependencies - to be overridden by application."""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Auth dependencies not configured"
    )


def get_user_registration_service() -> UserRegistrationService:
    """Get user registration service - to be overridden by application."""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="User registration service not configured"
    )


def get_password_reset_service() -> PasswordResetService:
    """Get password reset service - to be overridden by application."""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Password reset service not configured"
    )


async def extract_tenant_id(request: Request) -> TenantId:
    """Extract tenant ID from request - to be overridden by application."""
    # This is a placeholder - applications should override this
    # based on their tenant identification strategy
    tenant_header = request.headers.get("x-tenant-id")
    if tenant_header:
        return TenantId(tenant_header)
    
    # Check subdomain
    host = request.headers.get("host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        if subdomain and subdomain not in ["api", "www"]:
            return TenantId(subdomain)
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tenant identification required"
    )


async def get_realm_name(tenant_id: TenantId) -> str:
    """Get realm name for tenant - to be overridden by application."""
    # This is a placeholder - applications should override this
    # based on their realm naming strategy
    return f"tenant-{tenant_id.value}"


# Authentication endpoints

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    auth_deps: AuthDependencies = Depends(get_auth_dependencies),
    db_service = Depends(get_database_service),
) -> LoginResponse:
    """User login endpoint."""
    try:
        # Extract tenant ID from headers only
        tenant_id = await extract_tenant_id(request)
        
        realm_name = await get_realm_name(tenant_id)
        
        # Get realm configuration
        realm_config = await auth_deps.realm_manager.get_realm_config(tenant_id)
        if not realm_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant configuration not found"
            )
        
        # Create Keycloak config for this tenant
        keycloak_config = KeycloakConfig(
            server_url=realm_config.keycloak_server_url,
            realm_name=realm_config.realm_id.value,
            client_id=realm_config.client_id,
            client_secret=realm_config.client_secret,
        )
        
        # Authenticate user
        from ..adapters.keycloak_openid import KeycloakOpenIDAdapter
        async with KeycloakOpenIDAdapter(keycloak_config) as openid_client:
            jwt_token = await openid_client.authenticate(
                login_data.username, login_data.password
            )
            
            # Validate token and get auth context
            auth_context = await auth_deps.token_service.validate_and_cache_token(
                jwt_token.access_token, realm_config.realm_id
            )
            
            # Create token response
            token_response = TokenResponse(
                access_token=jwt_token.access_token,
                refresh_token=jwt_token.refresh_token,
                token_type=jwt_token.token_type,
                expires_in=jwt_token.expires_in,
                refresh_expires_in=jwt_token.refresh_expires_in,
                scope=jwt_token.scope,
            )
            
            # Create complete user profile response
            schema_name = getattr(request.state, 'database_schema', 'admin')  # Default to admin, can be overridden
            user_profile = await UserProfileResponse.from_auth_context(auth_context, schema_name, db_service)
            
            logger.info(f"User {login_data.username} logged in successfully")
            
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


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: Request,
    registration_data: RegisterRequest,
    registration_service: UserRegistrationService = Depends(get_user_registration_service),
) -> RegisterResponse:
    """User registration endpoint."""
    try:
        # Extract tenant ID from headers only
        tenant_id = await extract_tenant_id(request)
        
        realm_name = await get_realm_name(tenant_id)
        
        # Register user
        response = await registration_service.register_user(
            registration_data, tenant_id, realm_name
        )
        
        logger.info(f"User {registration_data.username} registered successfully")
        return response
    
    except UserAlreadyExistsError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service temporarily unavailable"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    auth_deps: AuthDependencies = Depends(get_auth_dependencies),
) -> TokenResponse:
    """Refresh access token."""
    try:
        # Extract tenant ID
        tenant_id = await extract_tenant_id(request)
        
        # Get realm configuration
        realm_config = await auth_deps.realm_manager.get_realm_config(tenant_id)
        if not realm_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant configuration not found"
            )
        
        # Create Keycloak config
        keycloak_config = KeycloakConfig(
            server_url=realm_config.keycloak_server_url,
            realm_name=realm_config.realm_id.value,
            client_id=realm_config.client_id,
            client_secret=realm_config.client_secret,
        )
        
        # Refresh token
        from ..adapters.keycloak_openid import KeycloakOpenIDAdapter
        async with KeycloakOpenIDAdapter(keycloak_config) as openid_client:
            jwt_token = await openid_client.refresh_token(refresh_data.refresh_token)
            
            return TokenResponse(
                access_token=jwt_token.access_token,
                refresh_token=jwt_token.refresh_token,
                token_type=jwt_token.token_type,
                expires_in=jwt_token.expires_in,
                refresh_expires_in=jwt_token.refresh_expires_in,
                scope=jwt_token.scope,
            )
    
    except (InvalidTokenError, TokenExpiredError) as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service temporarily unavailable"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    auth_deps: AuthDependencies = Depends(get_auth_dependencies),
    current_user: AuthContext = Depends(lambda: get_auth_dependencies().get_current_user),
) -> MessageResponse:
    """User logout endpoint."""
    try:
        # Extract tenant ID
        tenant_id = await extract_tenant_id(request)
        
        # Get realm configuration
        realm_config = await auth_deps.realm_manager.get_realm_config(tenant_id)
        if not realm_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant configuration not found"
            )
        
        # Create Keycloak config
        keycloak_config = KeycloakConfig(
            server_url=realm_config.keycloak_server_url,
            realm_name=realm_config.realm_id.value,
            client_id=realm_config.client_id,
            client_secret=realm_config.client_secret,
        )
        
        # Logout from Keycloak
        if logout_data.refresh_token:
            from ..adapters.keycloak_openid import KeycloakOpenIDAdapter
            async with KeycloakOpenIDAdapter(keycloak_config) as openid_client:
                await openid_client.logout(logout_data.refresh_token)
        
        # Invalidate cached tokens
        await auth_deps.token_service.invalidate_user_tokens(current_user.user_id)
        
        logger.info(f"User {current_user.user_id.value} logged out successfully")
        
        return MessageResponse(
            message="Logout successful",
            success=True,
        )
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Don't fail logout on errors
        return MessageResponse(
            message="Logout completed",
            success=True,
        )


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetResponse:
    """Forgot password endpoint."""
    try:
        # Extract tenant ID from headers only
        tenant_id = await extract_tenant_id(request)
        
        realm_name = await get_realm_name(tenant_id)
        
        # Initiate password reset
        response = await password_reset_service.initiate_password_reset(
            forgot_data, tenant_id, realm_name
        )
        
        logger.info(f"Password reset initiated for email {forgot_data.email}")
        return response
    
    except Exception as e:
        logger.error(f"Password reset initiation failed: {e}")
        # Return generic response for security
        return PasswordResetResponse(
            message="If an account with this email exists, you will receive a password reset link.",
            reset_token_sent=False,
        )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    request: Request,
    current_user: AuthContext = Depends(lambda: get_auth_dependencies().get_current_user),
    db_service = Depends(get_database_service),
) -> UserProfileResponse:
    """Get current user profile with complete database data."""
    schema_name = getattr(request.state, 'database_schema', 'admin')  # Default to admin, can be overridden
    return await UserProfileResponse.from_auth_context(current_user, schema_name, db_service)


@router.get("/session", response_model=SessionInfoResponse)
async def get_session_info(
    request: Request,
    current_user: AuthContext = Depends(lambda: get_auth_dependencies().get_current_user),
) -> SessionInfoResponse:
    """Get current session information."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    return SessionInfoResponse(
        session_id=current_user.session_id or "unknown",
        user_id=current_user.user_id.value,
        authenticated_at=current_user.authenticated_at,
        expires_at=current_user.expires_at,
        ip_address=client_ip,
        user_agent=user_agent,
    )


# Validation endpoints

@router.get("/validate/username/{username}", response_model=UserValidationResponse)
async def validate_username(
    username: str,
    request: Request,
    registration_service: UserRegistrationService = Depends(get_user_registration_service),
) -> UserValidationResponse:
    """Validate username availability."""
    try:
        tenant_id = await extract_tenant_id(request)
        realm_name = await get_realm_name(tenant_id)
        
        is_available = await registration_service.validate_username_availability(
            username, realm_name
        )
        
        return UserValidationResponse(
            valid=is_available,
            username_available=is_available,
            details={"username": username, "available": is_available}
        )
    
    except Exception as e:
        logger.error(f"Username validation failed: {e}")
        return UserValidationResponse(
            valid=False,
            username_available=False,
            details={"error": "Validation service unavailable"}
        )


@router.get("/validate/email/{email}", response_model=UserValidationResponse)
async def validate_email(
    email: str,
    request: Request,
    registration_service: UserRegistrationService = Depends(get_user_registration_service),
) -> UserValidationResponse:
    """Validate email availability."""
    try:
        tenant_id = await extract_tenant_id(request)
        realm_name = await get_realm_name(tenant_id)
        
        is_available = await registration_service.validate_email_availability(
            email, realm_name
        )
        
        return UserValidationResponse(
            valid=is_available,
            email_available=is_available,
            details={"email": email, "available": is_available}
        )
    
    except Exception as e:
        logger.error(f"Email validation failed: {e}")
        return UserValidationResponse(
            valid=False,
            email_available=False,
            details={"error": "Validation service unavailable"}
        )