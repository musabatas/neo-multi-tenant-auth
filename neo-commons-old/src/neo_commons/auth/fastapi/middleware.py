"""
Authentication Middleware for Neo-Commons

Enterprise-grade authentication middleware providing:
- JWT token validation with configurable strategies
- User context injection for request processing
- Performance monitoring and security auditing
- Tenant-aware authentication support
- Graceful error handling with proper HTTP status codes
"""

from typing import Optional, Dict, Any, Callable, List
from fastapi import Request, Response, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
import time
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    ValidationStrategy
)
from ..keycloak.protocols import TokenValidatorProtocol


class AuthenticationMiddleware:
    """
    FastAPI middleware for JWT token validation and user context injection.
    
    Features:
    - Automatic token extraction from Authorization header
    - Configurable validation strategies (local/introspection/dual)
    - User context injection into request state
    - Performance metrics collection
    - Security audit logging
    - Tenant-aware authentication
    - Graceful error handling with proper HTTP status codes
    """
    
    def __init__(
        self,
        token_validator: TokenValidatorProtocol,
        auth_config: AuthConfigProtocol,
        skip_paths: Optional[List[str]] = None,
        require_auth: bool = True,
        validation_strategy: ValidationStrategy = ValidationStrategy.LOCAL
    ):
        """
        Initialize authentication middleware.
        
        Args:
            token_validator: Token validation service
            auth_config: Authentication configuration
            skip_paths: List of paths to skip authentication
            require_auth: Whether authentication is required by default
            validation_strategy: Token validation strategy
        """
        self.token_validator = token_validator
        self.auth_config = auth_config
        self.skip_paths = skip_paths or [
            "/health",
            "/docs", 
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]
        self.require_auth = require_auth
        self.validation_strategy = validation_strategy
        
        # Performance metrics
        self.metrics = {
            'total_requests': 0,
            'authenticated_requests': 0,
            'failed_authentications': 0,
            'avg_validation_time': 0.0
        }
        
        logger.info(f"Initialized AuthenticationMiddleware with strategy: {validation_strategy}")
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through authentication middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from downstream handler
        """
        start_time = time.time()
        self.metrics['total_requests'] += 1
        
        # Skip authentication for specified paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Extract authorization token
        token = self._extract_token(request)
        
        # Handle missing token
        if not token:
            if self.require_auth:
                logger.warning(f"Missing authentication token for {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            else:
                # Set anonymous user context
                request.state.user = None
                request.state.user_id = None
                request.state.authenticated = False
                return await call_next(request)
        
        # Validate token and set user context
        try:
            user_context = await self._validate_and_extract_user(token, request)
            
            # Inject user context into request state
            request.state.user = user_context
            request.state.user_id = user_context.get('sub')
            request.state.authenticated = True
            request.state.token_data = user_context
            
            # Add tenant context if available
            if 'tenant_id' in user_context:
                request.state.tenant_id = user_context['tenant_id']
            
            self.metrics['authenticated_requests'] += 1
            
            # Log successful authentication
            logger.debug(
                f"Authenticated user {user_context.get('sub')} for {request.url.path}"
            )
            
        except AuthenticationError as e:
            self.metrics['failed_authentications'] += 1
            logger.warning(f"Authentication failed for {request.url.path}: {e}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        except AuthorizationError as e:
            self.metrics['failed_authentications'] += 1
            logger.warning(f"Authorization failed for {request.url.path}: {e}")
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
            
        except Exception as e:
            self.metrics['failed_authentications'] += 1
            logger.error(f"Unexpected error in authentication middleware: {e}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
        
        # Update performance metrics
        validation_time = time.time() - start_time
        self._update_metrics(validation_time)
        
        # Continue to next middleware/endpoint
        return await call_next(request)
    
    def _should_skip_auth(self, path: str) -> bool:
        """
        Check if authentication should be skipped for the given path.
        
        Args:
            path: Request path
            
        Returns:
            True if authentication should be skipped
        """
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract Bearer token from Authorization header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            JWT token if present, None otherwise
        """
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return None
        
        return token
    
    async def _validate_and_extract_user(
        self, 
        token: str, 
        request: Request
    ) -> Dict[str, Any]:
        """
        Validate token and extract user information.
        
        Args:
            token: JWT token to validate
            request: FastAPI request object
            
        Returns:
            User context dictionary
            
        Raises:
            AuthenticationError: Invalid token
            AuthorizationError: Insufficient permissions
        """
        try:
            # Validate token using configured strategy
            token_data = await self.token_validator.validate_token(
                token,
                realm=self.auth_config.default_realm,
                strategy=self.validation_strategy,
                critical=False
            )
            
            # Extract user information
            user_context = {
                'sub': token_data.get('sub'),
                'username': token_data.get('preferred_username', ''),
                'email': token_data.get('email', ''),
                'given_name': token_data.get('given_name'),
                'family_name': token_data.get('family_name'),
                'name': token_data.get('name'),
                'realm_access': token_data.get('realm_access', {}),
                'resource_access': token_data.get('resource_access', {}),
                'scope': token_data.get('scope', ''),
                'exp': token_data.get('exp'),
                'iat': token_data.get('iat'),
                'raw_token': token_data
            }
            
            # Add request metadata
            user_context.update({
                'ip_address': self._get_client_ip(request),
                'user_agent': request.headers.get('User-Agent', ''),
                'request_path': request.url.path,
                'request_method': request.method
            })
            
            return user_context
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise AuthenticationError("Invalid or expired token")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        forwarded = request.headers.get('X-Forwarded-Host')
        if forwarded:
            return forwarded
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"
    
    def _update_metrics(self, validation_time: float) -> None:
        """
        Update performance metrics.
        
        Args:
            validation_time: Time taken for token validation
        """
        # Simple moving average for validation time
        current_avg = self.metrics['avg_validation_time']
        total_requests = self.metrics['total_requests']
        
        self.metrics['avg_validation_time'] = (
            (current_avg * (total_requests - 1) + validation_time) / total_requests
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get middleware performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            'total_requests': self.metrics['total_requests'],
            'authenticated_requests': self.metrics['authenticated_requests'],
            'failed_authentications': self.metrics['failed_authentications'],
            'authentication_rate': (
                self.metrics['authenticated_requests'] / max(1, self.metrics['total_requests'])
            ) * 100,
            'failure_rate': (
                self.metrics['failed_authentications'] / max(1, self.metrics['total_requests'])
            ) * 100,
            'avg_validation_time_ms': self.metrics['avg_validation_time'] * 1000
        }
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics = {
            'total_requests': 0,
            'authenticated_requests': 0,
            'failed_authentications': 0,
            'avg_validation_time': 0.0
        }
        logger.info("Reset authentication middleware metrics")


class TenantAwareAuthMiddleware(AuthenticationMiddleware):
    """
    Extended authentication middleware with tenant awareness.
    
    Adds tenant context resolution and validation for multi-tenant applications.
    """
    
    def __init__(
        self,
        token_validator: TokenValidatorProtocol,
        auth_config: AuthConfigProtocol,
        tenant_resolver: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize tenant-aware authentication middleware.
        
        Args:
            token_validator: Token validation service
            auth_config: Authentication configuration
            tenant_resolver: Optional function to resolve tenant from request
            **kwargs: Additional arguments for base middleware
        """
        super().__init__(token_validator, auth_config, **kwargs)
        self.tenant_resolver = tenant_resolver
    
    async def _validate_and_extract_user(
        self, 
        token: str, 
        request: Request
    ) -> Dict[str, Any]:
        """
        Validate token and extract user information with tenant context.
        
        Args:
            token: JWT token to validate
            request: FastAPI request object
            
        Returns:
            User context dictionary with tenant information
        """
        user_context = await super()._validate_and_extract_user(token, request)
        
        # Resolve tenant context if resolver is provided
        if self.tenant_resolver:
            try:
                tenant_id = await self.tenant_resolver(request, user_context)
                if tenant_id:
                    user_context['tenant_id'] = tenant_id
                    logger.debug(f"Resolved tenant {tenant_id} for user {user_context.get('sub')}")
            except Exception as e:
                logger.warning(f"Tenant resolution failed: {e}")
        
        return user_context


# Factory functions for creating configured middleware
def create_auth_middleware(
    token_validator: TokenValidatorProtocol,
    auth_config: AuthConfigProtocol,
    **kwargs
) -> AuthenticationMiddleware:
    """
    Create configured authentication middleware.
    
    Args:
        token_validator: Token validation service
        auth_config: Authentication configuration
        **kwargs: Additional middleware configuration
        
    Returns:
        Configured AuthenticationMiddleware instance
    """
    return AuthenticationMiddleware(token_validator, auth_config, **kwargs)


def create_tenant_aware_middleware(
    token_validator: TokenValidatorProtocol,
    auth_config: AuthConfigProtocol,
    tenant_resolver: Optional[Callable] = None,
    **kwargs
) -> TenantAwareAuthMiddleware:
    """
    Create configured tenant-aware authentication middleware.
    
    Args:
        token_validator: Token validation service
        auth_config: Authentication configuration
        tenant_resolver: Function to resolve tenant from request
        **kwargs: Additional middleware configuration
        
    Returns:
        Configured TenantAwareAuthMiddleware instance
    """
    return TenantAwareAuthMiddleware(
        token_validator, auth_config, tenant_resolver, **kwargs
    )


__all__ = [
    "AuthenticationMiddleware",
    "TenantAwareAuthMiddleware",
    "create_auth_middleware",
    "create_tenant_aware_middleware",
]