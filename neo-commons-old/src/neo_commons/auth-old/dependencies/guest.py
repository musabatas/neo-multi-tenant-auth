"""
Guest Authentication Dependencies Implementation

Protocol-compliant guest authentication system supporting public endpoint access with:
- Guest session tracking and rate limiting
- Mixed authentication (guest or authenticated users)
- Session-based access controls with IP and user agent tracking
- Rate limiting integration with configurable thresholds
- Protocol-based dependency injection for service independence
"""

from typing import Optional, List, Dict, Any
from fastapi import Depends, Request, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from ..protocols import (
    GuestAuthServiceProtocol,
    PermissionCheckerProtocol,
    TokenValidatorProtocol,
    AuthConfigProtocol
)
from ...exceptions import UnauthorizedError, ForbiddenError, RateLimitError


# Optional security scheme for guest tokens
guest_security = HTTPBearer(
    description="Optional guest session token for tracking",
    auto_error=False
)


class GuestSessionInfo:
    """
    Guest session information extraction dependency.
    
    Provides session metadata and statistics for guest users without
    requiring full authentication.
    """
    
    def __init__(self, guest_service: GuestAuthServiceProtocol):
        """
        Initialize guest session info dependency.
        
        Args:
            guest_service: Guest authentication service implementation
        """
        self.guest_service = guest_service
    
    async def __call__(
        self,
        x_guest_session: Optional[str] = Header(None, description="Guest session token")
    ) -> Optional[Dict[str, Any]]:
        """
        Extract guest session information from headers.
        
        Args:
            x_guest_session: Guest session token from X-Guest-Session header
            
        Returns:
            Guest session statistics if token provided, None otherwise
        """
        if not x_guest_session:
            return None
        
        try:
            return await self.guest_service.get_session_stats(x_guest_session)
        except Exception as e:
            logger.debug(f"Failed to get guest session stats: {e}")
            return None


class GuestOrAuthenticated:
    """
    Mixed authentication dependency supporting both authenticated users and guest access.
    
    This dependency provides flexible access patterns where endpoints can be accessed by:
    1. Authenticated users with permission validation
    2. Guest users with session tracking and rate limiting
    
    Features:
    - Automatic authentication attempt with graceful fallback to guest
    - Guest session creation and tracking with metadata collection
    - Rate limiting for guest access to prevent abuse
    - Protocol-based service injection for independence
    - Configurable permission requirements for authenticated users
    """
    
    def __init__(
        self,
        guest_service: GuestAuthServiceProtocol,
        permission_checker: PermissionCheckerProtocol,
        token_validator: TokenValidatorProtocol,
        auth_config: AuthConfigProtocol,
        required_permissions: Optional[List[str]] = None
    ):
        """
        Initialize mixed authentication dependency.
        
        Args:
            guest_service: Guest authentication service
            permission_checker: Permission validation service
            token_validator: Token validation service
            auth_config: Authentication configuration
            required_permissions: Permissions required for authenticated access
        """
        self.guest_service = guest_service
        self.permission_checker = permission_checker
        self.token_validator = token_validator
        self.auth_config = auth_config
        self.required_permissions = required_permissions or []
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(guest_security),
        x_guest_session: Optional[str] = Header(None, description="Guest session token")
    ) -> Dict[str, Any]:
        """
        Validate either authenticated user or create guest session.
        
        Attempts authentication first, then falls back to guest access with
        session tracking and rate limiting.
        
        Args:
            request: FastAPI request object
            credentials: Optional bearer token credentials
            x_guest_session: Optional guest session token
            
        Returns:
            User data (authenticated) or guest session data
            
        Raises:
            HTTPException: On rate limit exceeded or system errors
        """
        # Extract client information for session tracking (matching source)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        referrer = request.headers.get("referer")
        
        # Try authenticated access first (matching source)
        if credentials and credentials.credentials:
            try:
                # Validate token using protocol-based validator
                token_data = await self.token_validator.validate_token(
                    credentials.credentials,
                    realm=self.auth_config.default_realm,
                    strategy=self.auth_config.default_validation_strategy,
                    critical=False
                )
                
                user_id = token_data.get("sub", "")
                if not user_id:
                    raise UnauthorizedError("Invalid token: missing user ID")
                
                # Check permissions if required (matching source logic)
                if self.required_permissions:
                    # Use check_permission for multiple permissions check (requires ALL by default)
                    has_permission = await self.permission_checker.check_permission(
                        user_id=user_id,
                        permissions=self.required_permissions,
                        scope="platform",
                        tenant_id=None,
                        any_of=False  # Require ALL permissions
                    )
                    
                    if not has_permission:
                        raise ForbiddenError(
                            f"Insufficient permissions. Required: {', '.join(self.required_permissions)}"
                        )
                
                # Return authenticated user data (matching source)
                user_data = {
                    "id": user_id,
                    "username": token_data.get("preferred_username", ""),
                    "email": token_data.get("email", ""),
                    "user_type": "authenticated",
                    "session_type": "keycloak",
                    "permissions": self.required_permissions
                }
                
                logger.debug(f"Authenticated user {user_id} accessing with guest/auth dependency")
                return user_data
                
            except Exception as e:
                logger.debug(f"Authentication failed, falling back to guest: {e}")
                # Fall through to guest access (matching source)
        
        # Handle guest access (matching source)
        try:
            # Get or create guest session
            guest_token = x_guest_session or (credentials.credentials if credentials else None)
            
            session_data = await self.guest_service.get_or_create_guest_session(
                session_token=guest_token,
                ip_address=client_ip,
                user_agent=user_agent,
                referrer=referrer
            )
            
            # Format session token for response (matching source)
            if not guest_token or not guest_token.startswith("guest_"):
                session_data["new_session_token"] = f"{session_data['session_id']}:{session_data['session_token']}"
            
            logger.debug(f"Guest session {session_data['session_id']} accessing via guest/auth dependency")
            return session_data
            
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
                headers={"Retry-After": "3600"}  # 1 hour (matching source)
            )
        except Exception as e:
            logger.error(f"Guest authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create guest session"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request with proxy support.
        
        Handles various proxy headers to get the real client IP address.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address string
        """
        # Check X-Forwarded-For header (load balancer/proxy) (matching source)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header (nginx) (matching source)
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection (matching source)
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


# Factory functions for creating configured dependencies
def create_guest_session_info(guest_service: GuestAuthServiceProtocol) -> GuestSessionInfo:
    """Create configured GuestSessionInfo dependency."""
    return GuestSessionInfo(guest_service)


def create_guest_or_authenticated(
    guest_service: GuestAuthServiceProtocol,
    permission_checker: PermissionCheckerProtocol,
    token_validator: TokenValidatorProtocol,
    auth_config: AuthConfigProtocol,
    required_permissions: Optional[List[str]] = None
) -> GuestOrAuthenticated:
    """Create configured GuestOrAuthenticated dependency."""
    return GuestOrAuthenticated(
        guest_service, permission_checker, token_validator, 
        auth_config, required_permissions
    )


# Placeholder instances - these need to be configured with actual implementations
get_reference_data_access = None  # Will be configured in service
get_guest_session_info = None  # Will be configured in service


def create_reference_data_access(
    guest_service: GuestAuthServiceProtocol,
    permission_checker: PermissionCheckerProtocol,
    token_validator: TokenValidatorProtocol,
    auth_config: AuthConfigProtocol
) -> GuestOrAuthenticated:
    """
    Create reference data access dependency.
    
    Configured for reference data endpoints that require 'reference_data:read'
    permission for authenticated users but allow guest access.
    """
    return GuestOrAuthenticated(
        guest_service, permission_checker, token_validator,
        auth_config, required_permissions=["reference_data:read"]
    )