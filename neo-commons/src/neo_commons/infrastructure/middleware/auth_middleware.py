"""Authentication middleware for FastAPI with Keycloak integration.

Provides JWT token validation, user ID mapping, and request context setup
with automatic fallback between Keycloak and platform user IDs.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt
from datetime import datetime

from ...core.value_objects import UserId, TenantId
from ...core.shared.context import RequestContext
from ...core.exceptions import AuthenticationError, AuthorizationError
from ...features.users.services import UserService
from ...features.cache.services import CacheService

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for JWT authentication with user ID mapping."""
    
    def __init__(
        self,
        app,
        user_service: UserService,
        cache_service: CacheService,
        jwt_secret: str,
        jwt_algorithm: str = "RS256",
        exempt_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.user_service = user_service
        self.cache_service = cache_service
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/metrics"
        ]
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process authentication for incoming requests."""
        
        # Skip authentication for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        try:
            # Extract and validate JWT token
            token = await self._extract_token(request)
            
            if token:
                # Validate token and extract user information
                user_info = await self._validate_token(token)
                
                # Map Keycloak user to platform user
                platform_user_id = await self._map_user_id(user_info)
                
                # Create request context
                request_context = RequestContext(
                    user_id=platform_user_id,
                    tenant_id=user_info.get("tenant_id"),
                    request_id=request.headers.get("X-Request-ID"),
                    keycloak_user_id=user_info.get("sub"),
                    user_email=user_info.get("email"),
                    user_roles=user_info.get("roles", []),
                    timestamp=datetime.utcnow()
                )
                
                # Store context in request state
                request.state.user_context = request_context
                request.state.authenticated = True
                
                logger.info(
                    f"User authenticated: user_id={platform_user_id}, "
                    f"tenant_id={user_info.get('tenant_id')}, "
                    f"path={request.url.path}"
                )
            else:
                # Handle unauthenticated requests
                request.state.authenticated = False
                
                # Check if authentication is required for this path
                if self._requires_authentication(request):
                    raise AuthenticationError("Authentication required")
        
        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authentication error"
            )
        
        return await call_next(request)
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return None
        
        if not authorization.startswith("Bearer "):
            raise AuthenticationError("Invalid authorization header format")
        
        return authorization[7:]  # Remove "Bearer " prefix
    
    async def _validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and extract user information."""
        try:
            # Check cache first for token validation
            cache_key = f"jwt_validation:{token[:32]}"
            cached_info = await self.cache_service.get(cache_key)
            
            if cached_info:
                return cached_info
            
            # Validate JWT token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": True}
            )
            
            # Extract user information
            user_info = {
                "sub": payload.get("sub"),  # Keycloak user ID
                "email": payload.get("email"),
                "preferred_username": payload.get("preferred_username"),
                "realm": payload.get("iss", "").split("/")[-1] if payload.get("iss") else None,
                "roles": payload.get("realm_access", {}).get("roles", []),
                "tenant_id": self._extract_tenant_from_realm(payload.get("iss", "")),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
            # Cache validation result (short TTL)
            await self.cache_service.set(
                cache_key,
                user_info,
                ttl=300  # 5 minutes
            )
            
            return user_info
        
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError("Token validation failed")
    
    async def _map_user_id(self, user_info: Dict[str, Any]) -> UserId:
        """Map Keycloak user ID to platform user ID with caching."""
        keycloak_user_id = user_info.get("sub")
        
        if not keycloak_user_id:
            raise AuthenticationError("Missing user ID in token")
        
        try:
            # Check cache first
            cache_key = f"user_mapping:{keycloak_user_id}"
            cached_user_id = await self.cache_service.get(cache_key)
            
            if cached_user_id:
                return UserId(cached_user_id)
            
            # Map user through user service
            platform_user_id = await self.user_service.map_keycloak_user(
                keycloak_user_id=keycloak_user_id,
                email=user_info.get("email"),
                username=user_info.get("preferred_username")
            )
            
            # Cache the mapping
            await self.cache_service.set(
                cache_key,
                str(platform_user_id),
                ttl=3600  # 1 hour
            )
            
            return platform_user_id
        
        except Exception as e:
            logger.error(f"User mapping error: {e}")
            raise AuthenticationError("Failed to map user ID")
    
    def _extract_tenant_from_realm(self, issuer: str) -> Optional[TenantId]:
        """Extract tenant ID from Keycloak realm in issuer."""
        if not issuer:
            return None
        
        # Expected format: http://localhost:8080/realms/tenant-{slug}
        parts = issuer.split("/")
        if len(parts) > 0:
            realm = parts[-1]
            if realm.startswith("tenant-"):
                tenant_slug = realm[7:]  # Remove "tenant-" prefix
                return TenantId(tenant_slug)
        
        return None
    
    def _requires_authentication(self, request: Request) -> bool:
        """Check if the request path requires authentication."""
        # Most API endpoints require authentication
        # Override this method for custom logic
        return request.url.path.startswith("/api/")


class OptionalAuthenticationMiddleware(AuthenticationMiddleware):
    """Authentication middleware that doesn't enforce authentication."""
    
    def _requires_authentication(self, request: Request) -> bool:
        """Optional authentication - never requires auth."""
        return False