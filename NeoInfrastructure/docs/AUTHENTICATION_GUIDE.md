# Authentication Implementation Guide

This guide provides detailed instructions for implementing authentication and authorization in the Infrastructure API, following the established patterns from the Admin API.

## 🎯 Authentication Overview

### Architecture Goals
- **Secure by Default**: All endpoints require authentication except health checks
- **Platform Permissions**: Fine-grained permissions for infrastructure operations
- **Keycloak Integration**: Leverage existing Keycloak infrastructure
- **Token Validation**: JWT token validation with caching for performance
- **Role-Based Access**: Different access levels for different user types

### Permission Model
```
Infrastructure Operations:
├── migrations:read        # View migration status and history
├── migrations:execute     # Execute migration operations
├── migrations:manage      # Manage schedules and advanced operations
├── databases:read         # View database connections
├── databases:manage       # CRUD operations on database connections
├── infrastructure:admin   # Full administrative access
└── system:monitor         # System monitoring and metrics
```

---

## 🔧 Implementation Steps

### Step 1: Keycloak Integration Setup

#### Task 1.1: Copy and Adapt Keycloak Client (1 day)
**File**: `src/integrations/keycloak/async_client.py`

```python
"""
Infrastructure API Keycloak client implementation.
"""
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timedelta
import aiohttp
from python_keycloak import KeycloakOpenIDAsync, KeycloakUMA
from loguru import logger
import redis.asyncio as redis
import json

from src.common.config.settings import settings
from src.common.exceptions.base import AuthenticationException

class InfrastructureKeycloakClient:
    """Async Keycloak client for infrastructure operations."""
    
    def __init__(self):
        self.admin_client = KeycloakOpenIDAsync(
            server_url=settings.keycloak_url,
            client_id=settings.keycloak_admin_client_id,
            realm_name=settings.keycloak_admin_realm,
            client_secret_key=settings.keycloak_admin_client_secret,
            verify=not settings.is_development
        )
        
        # Redis client for caching (optional)
        self.redis_client: Optional[redis.Redis] = None
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_expiry: Dict[str, datetime] = {}
    
    async def initialize(self):
        """Initialize Keycloak client and optional Redis cache."""
        try:
            # Test connection to Keycloak
            well_known = await self.admin_client.well_known()
            logger.info(f"Connected to Keycloak: {well_known.get('issuer')}")
            
            # Initialize Redis cache if available
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_timeout=5
                )
                await self.redis_client.ping()
                logger.info("Redis cache initialized for token validation")
            except Exception as e:
                logger.warning(f"Redis cache not available, using in-memory cache: {e}")
                self.redis_client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize Keycloak client: {e}")
            raise AuthenticationException(f"Keycloak initialization failed: {str(e)}")
    
    async def validate_token(
        self, 
        token: str, 
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Validate JWT token and return user claims.
        
        Args:
            token: JWT token to validate
            use_cache: Whether to use cache for validation
            
        Returns:
            User claims and permissions
            
        Raises:
            AuthenticationException: If token is invalid or expired
        """
        
        # Check cache first
        if use_cache:
            cached_data = await self._get_cached_token_data(token)
            if cached_data:
                return cached_data
        
        try:
            # Introspect token for active status
            token_info = await self.admin_client.introspect(token)
            
            if not token_info.get("active", False):
                raise AuthenticationException("Token is not active")
            
            # Get user info from token
            userinfo = await self.admin_client.userinfo(token)
            
            # Extract roles and permissions
            permissions = await self._extract_permissions(token_info, userinfo)
            
            # Combine all user data
            user_data = {
                **token_info,
                **userinfo,
                "permissions": permissions,
                "validated_at": datetime.utcnow().isoformat()
            }
            
            # Cache the validated data
            if use_cache:
                await self._cache_token_data(token, user_data)
            
            logger.debug(f"Token validated for user: {userinfo.get('preferred_username')}")
            return user_data
            
        except Exception as e:
            if isinstance(e, AuthenticationException):
                raise
            logger.error(f"Token validation failed: {e}")
            raise AuthenticationException(f"Token validation error: {str(e)}")
    
    async def _extract_permissions(
        self, 
        token_info: Dict[str, Any], 
        userinfo: Dict[str, Any]
    ) -> List[str]:
        """Extract permissions from token claims."""
        
        permissions = set()
        
        # Extract from resource access (client-specific roles)
        resource_access = token_info.get("resource_access", {})
        if settings.keycloak_admin_client_id in resource_access:
            client_roles = resource_access[settings.keycloak_admin_client_id].get("roles", [])
            permissions.update(client_roles)
        
        # Extract from realm access (realm-wide roles)
        realm_access = token_info.get("realm_access", {})
        realm_roles = realm_access.get("roles", [])
        permissions.update(realm_roles)
        
        # Map roles to infrastructure permissions
        infrastructure_permissions = self._map_roles_to_permissions(list(permissions))
        
        logger.debug(f"Extracted permissions for user: {infrastructure_permissions}")
        return infrastructure_permissions
    
    def _map_roles_to_permissions(self, roles: List[str]) -> List[str]:
        """Map Keycloak roles to infrastructure permissions."""
        
        permission_mapping = {
            # Admin roles
            "platform_admin": [
                "migrations:read", "migrations:execute", "migrations:manage",
                "databases:read", "databases:manage", 
                "infrastructure:admin", "system:monitor"
            ],
            "infrastructure_admin": [
                "migrations:read", "migrations:execute", "migrations:manage",
                "databases:read", "databases:manage", "system:monitor"
            ],
            
            # Migration-specific roles
            "migration_operator": [
                "migrations:read", "migrations:execute", "databases:read"
            ],
            "migration_viewer": [
                "migrations:read", "databases:read"
            ],
            
            # Database roles
            "database_admin": [
                "databases:read", "databases:manage", "migrations:read"
            ],
            "database_viewer": [
                "databases:read"
            ],
            
            # System roles
            "system_monitor": [
                "system:monitor"
            ]
        }
        
        permissions = set()
        for role in roles:
            if role in permission_mapping:
                permissions.update(permission_mapping[role])
        
        return list(permissions)
    
    async def _get_cached_token_data(self, token: str) -> Optional[Dict[str, Any]]:
        """Get cached token validation data."""
        
        cache_key = f"token_validation:{hash(token)}"
        
        try:
            if self.redis_client:
                cached_json = await self.redis_client.get(cache_key)
                if cached_json:
                    return json.loads(cached_json)
            else:
                # In-memory cache
                if cache_key in self._token_cache:
                    if datetime.utcnow() < self._cache_expiry.get(cache_key, datetime.min):
                        return self._token_cache[cache_key]
                    else:
                        # Expired
                        del self._token_cache[cache_key]
                        del self._cache_expiry[cache_key]
        except Exception as e:
            logger.debug(f"Cache retrieval failed: {e}")
        
        return None
    
    async def _cache_token_data(
        self, 
        token: str, 
        data: Dict[str, Any], 
        ttl_seconds: int = 300  # 5 minutes
    ):
        """Cache token validation data."""
        
        cache_key = f"token_validation:{hash(token)}"
        
        try:
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key, 
                    ttl_seconds, 
                    json.dumps(data, default=str)
                )
            else:
                # In-memory cache
                self._token_cache[cache_key] = data
                self._cache_expiry[cache_key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
                
                # Simple cleanup of expired entries
                if len(self._token_cache) > 1000:  # Prevent memory leak
                    expired_keys = [
                        k for k, expiry in self._cache_expiry.items() 
                        if expiry < datetime.utcnow()
                    ]
                    for key in expired_keys:
                        self._token_cache.pop(key, None)
                        self._cache_expiry.pop(key, None)
                        
        except Exception as e:
            logger.debug(f"Cache storage failed: {e}")
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed user information by user ID."""
        
        try:
            # This would require admin access to get user details
            # Implementation depends on your Keycloak setup
            logger.debug(f"Getting user info for: {user_id}")
            return None  # Placeholder
            
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return None
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.redis_client:
            await self.redis_client.close()

# Global client instance
_keycloak_client: Optional[InfrastructureKeycloakClient] = None

async def get_keycloak_client() -> InfrastructureKeycloakClient:
    """Get initialized Keycloak client instance."""
    global _keycloak_client
    
    if _keycloak_client is None:
        _keycloak_client = InfrastructureKeycloakClient()
        await _keycloak_client.initialize()
    
    return _keycloak_client

async def cleanup_keycloak_client():
    """Cleanup Keycloak client resources."""
    global _keycloak_client
    
    if _keycloak_client:
        await _keycloak_client.cleanup()
        _keycloak_client = None
```

#### Task 1.2: Token Manager Implementation (1 day)
**File**: `src/integrations/keycloak/token_manager.py`

```python
"""
Token management for Infrastructure API.
"""
from typing import Optional, Dict, Any
from enum import Enum
from loguru import logger

from src.integrations.keycloak.async_client import get_keycloak_client
from src.common.exceptions.base import AuthenticationException

class ValidationStrategy(str, Enum):
    """Token validation strategy."""
    STRICT = "strict"      # Always validate with Keycloak
    CACHED = "cached"      # Use cache when available
    DUAL = "dual"          # Try cache first, fallback to Keycloak

class TokenManager:
    """Manages token validation and caching strategies."""
    
    def __init__(self):
        self.keycloak_client = None
    
    async def initialize(self):
        """Initialize token manager."""
        self.keycloak_client = await get_keycloak_client()
        logger.info("Token manager initialized")
    
    async def validate_token(
        self,
        token: str,
        strategy: ValidationStrategy = ValidationStrategy.DUAL,
        required_permissions: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Validate token and check permissions.
        
        Args:
            token: JWT token to validate
            strategy: Validation strategy to use
            required_permissions: Permissions required for access
            
        Returns:
            User data including permissions
            
        Raises:
            AuthenticationException: If validation fails
        """
        
        if not self.keycloak_client:
            await self.initialize()
        
        try:
            # Validate token based on strategy
            use_cache = strategy in [ValidationStrategy.CACHED, ValidationStrategy.DUAL]
            user_data = await self.keycloak_client.validate_token(token, use_cache=use_cache)
            
            # Check required permissions
            if required_permissions:
                user_permissions = user_data.get("permissions", [])
                missing_permissions = set(required_permissions) - set(user_permissions)
                
                if missing_permissions:
                    raise AuthenticationException(
                        f"Missing required permissions: {', '.join(missing_permissions)}"
                    )
            
            return user_data
            
        except AuthenticationException:
            raise
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise AuthenticationException(f"Token validation error: {str(e)}")
    
    async def extract_user_context(self, token: str) -> Dict[str, Any]:
        """Extract user context without full validation (for logging)."""
        
        try:
            import jwt
            
            # Decode without verification for context extraction
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            return {
                "user_id": decoded.get("sub"),
                "username": decoded.get("preferred_username"),
                "email": decoded.get("email"),
                "realm": decoded.get("iss", "").split("/")[-1] if decoded.get("iss") else None
            }
            
        except Exception as e:
            logger.debug(f"Failed to extract user context: {e}")
            return {"user_id": "unknown", "username": "unknown"}

# Global token manager
_token_manager: Optional[TokenManager] = None

async def get_token_manager() -> TokenManager:
    """Get initialized token manager instance."""
    global _token_manager
    
    if _token_manager is None:
        _token_manager = TokenManager()
        await _token_manager.initialize()
    
    return _token_manager
```

---

### Step 2: Authentication Dependencies

#### Task 2.1: Infrastructure-Specific Dependencies (1 day)
**File**: `src/features/auth/dependencies.py`

```python
"""
Authentication dependencies for Infrastructure API endpoints.
"""
from typing import Optional, List, Dict, Any, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from src.integrations.keycloak.token_manager import get_token_manager, ValidationStrategy
from src.common.exceptions.base import AuthenticationException

# Security scheme
security = HTTPBearer(
    description="JWT token from Keycloak for infrastructure operations",
    auto_error=False
)

class InfrastructureAuth:
    """
    Authentication dependency for infrastructure operations.
    
    This dependency validates JWT tokens and checks infrastructure-specific
    permissions for secure access to migration and database operations.
    """
    
    def __init__(
        self, 
        required_permissions: Optional[List[str]] = None,
        any_permission: bool = False,
        strategy: ValidationStrategy = ValidationStrategy.DUAL
    ):
        """
        Initialize authentication dependency.
        
        Args:
            required_permissions: List of required permissions
            any_permission: If True, user needs ANY permission; if False, needs ALL
            strategy: Token validation strategy
        """
        self.required_permissions = required_permissions or []
        self.any_permission = any_permission
        self.strategy = strategy
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        """
        Validate token and check permissions.
        
        Args:
            request: FastAPI request object
            credentials: HTTP bearer credentials
            
        Returns:
            User information with permissions
            
        Raises:
            HTTPException: If authentication or authorization fails
        """
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for infrastructure operations",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        try:
            token_manager = await get_token_manager()
            
            # Validate token with required permissions
            user_data = await token_manager.validate_token(
                token=credentials.credentials,
                strategy=self.strategy,
                required_permissions=self.required_permissions if not self.any_permission else None
            )
            
            # Handle "any permission" logic
            if self.any_permission and self.required_permissions:
                user_permissions = user_data.get("permissions", [])
                has_any_permission = any(perm in user_permissions for perm in self.required_permissions)
                
                if not has_any_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Requires any of: {', '.join(self.required_permissions)}"
                    )
            
            # Add request context
            user_data.update({
                "request_id": request.headers.get("x-request-id", "unknown"),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "unknown")
            })
            
            logger.debug(
                f"User authenticated for infrastructure operation",
                extra={
                    "user_id": user_data.get("sub"),
                    "username": user_data.get("preferred_username"),
                    "permissions": user_data.get("permissions", []),
                    "endpoint": str(request.url),
                    "method": request.method
                }
            )
            
            return user_data
            
        except AuthenticationException as e:
            logger.warning(f"Authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header (nginx)
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"

class OptionalAuth:
    """Optional authentication for endpoints that support both auth and public access."""
    
    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[Dict[str, Any]]:
        """Return user data if authenticated, None otherwise."""
        
        if not credentials:
            return None
        
        try:
            auth = InfrastructureAuth()
            return await auth(credentials)
        except HTTPException:
            return None

# Permission-based dependencies
require_migration_read = InfrastructureAuth(["migrations:read"])
require_migration_execute = InfrastructureAuth(["migrations:execute"])
require_migration_manage = InfrastructureAuth(["migrations:manage"])

require_database_read = InfrastructureAuth(["databases:read"])
require_database_manage = InfrastructureAuth(["databases:manage"])

require_infrastructure_admin = InfrastructureAuth(["infrastructure:admin"])
require_system_monitor = InfrastructureAuth(["system:monitor"])

# Flexible permission dependencies
require_migration_access = InfrastructureAuth(
    ["migrations:read", "migrations:execute", "migrations:manage"],
    any_permission=True
)

require_database_access = InfrastructureAuth(
    ["databases:read", "databases:manage"],
    any_permission=True
)

# Optional authentication
get_current_user_optional = OptionalAuth()

def require_any_permissions(*permissions: str):
    """Create a dependency that requires ANY of the specified permissions."""
    return InfrastructureAuth(list(permissions), any_permission=True)

def require_all_permissions(*permissions: str):
    """Create a dependency that requires ALL of the specified permissions."""
    return InfrastructureAuth(list(permissions), any_permission=False)

def require_admin_or_permission(permission: str):
    """Create a dependency that requires admin access OR a specific permission."""
    return InfrastructureAuth(
        ["infrastructure:admin", permission], 
        any_permission=True
    )
```

#### Task 2.2: Authentication Router (0.5 days)
**File**: `src/features/auth/routers/auth.py`

```python
"""
Authentication endpoints for Infrastructure API.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from src.features.auth.dependencies import (
    get_current_user_optional, 
    require_infrastructure_admin
)
from src.integrations.keycloak.token_manager import get_token_manager

router = APIRouter()

@router.get("/profile")
async def get_user_profile(
    user_data: Dict[str, Any] = Depends(get_current_user_optional)
):
    """Get current user profile information."""
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return {
        "user_id": user_data.get("sub"),
        "username": user_data.get("preferred_username"),
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "permissions": user_data.get("permissions", []),
        "realm": user_data.get("iss", "").split("/")[-1] if user_data.get("iss") else None,
        "validated_at": user_data.get("validated_at"),
        "session_info": {
            "client_ip": user_data.get("client_ip"),
            "user_agent": user_data.get("user_agent"),
            "request_id": user_data.get("request_id")
        }
    }

@router.post("/validate-token")
async def validate_token(
    user_data: Dict[str, Any] = Depends(get_current_user_optional)
):
    """Validate current token and return status."""
    
    if not user_data:
        return {
            "valid": False,
            "reason": "No token provided or invalid token"
        }
    
    return {
        "valid": True,
        "user_id": user_data.get("sub"),
        "username": user_data.get("preferred_username"),
        "permissions": user_data.get("permissions", []),
        "expires_at": user_data.get("exp"),
        "validated_at": datetime.utcnow().isoformat()
    }

@router.get("/permissions")
async def get_user_permissions(
    user_data: Dict[str, Any] = Depends(get_current_user_optional)
):
    """Get current user's infrastructure permissions."""
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    permissions = user_data.get("permissions", [])
    
    return {
        "user_id": user_data.get("sub"),
        "permissions": permissions,
        "permission_count": len(permissions),
        "categorized_permissions": {
            "migrations": [p for p in permissions if p.startswith("migrations:")],
            "databases": [p for p in permissions if p.startswith("databases:")],
            "infrastructure": [p for p in permissions if p.startswith("infrastructure:")],
            "system": [p for p in permissions if p.startswith("system:")]
        }
    }

@router.get("/health")
async def auth_health():
    """Check authentication service health."""
    
    try:
        token_manager = await get_token_manager()
        # Could add more sophisticated health checks here
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "authentication",
            "keycloak_connection": "operational"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unhealthy: {str(e)}"
        )

@router.post("/admin/clear-cache")
async def clear_auth_cache(
    user_data: Dict[str, Any] = Depends(require_infrastructure_admin)
):
    """Clear authentication cache (admin only)."""
    
    try:
        # This would clear the token validation cache
        # Implementation depends on caching strategy
        
        return {
            "status": "success",
            "message": "Authentication cache cleared",
            "cleared_by": user_data.get("preferred_username"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )
```

---

### Step 3: Middleware Integration

#### Task 3.1: Security Middleware (0.5 days)
**File**: `src/common/middleware/config.py`

```python
"""
Middleware configuration for Infrastructure API.
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.common.config.settings import settings
from src.common.middleware.logging import RequestLoggingMiddleware
from src.common.middleware.security import SecurityHeadersMiddleware
from src.common.middleware.rate_limiting import RateLimitMiddleware

def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the Infrastructure API."""
    
    # Trusted hosts (if configured)
    if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # Security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        force_https=settings.is_production,
        include_security_headers=True
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"]
    )
    
    # Rate limiting
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.rate_limit_requests_per_minute
        )
    
    # Request logging
    app.add_middleware(
        RequestLoggingMiddleware,
        exclude_paths=["/health", "/docs", "/openapi.json"]
    )
```

---

### Step 4: Testing Strategy

#### Task 4.1: Authentication Tests (1 day)
**File**: `tests/features/auth/test_dependencies.py`

```python
"""
Tests for authentication dependencies.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.features.auth.dependencies import InfrastructureAuth
from src.common.exceptions.base import AuthenticationException

class TestInfrastructureAuth:
    """Test infrastructure authentication dependency."""
    
    @pytest.fixture
    def auth_dependency(self):
        """Create auth dependency for testing."""
        return InfrastructureAuth(["migrations:read"])
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request object."""
        request = AsyncMock()
        request.headers = {"x-request-id": "test-123", "user-agent": "test-agent"}
        request.client.host = "127.0.0.1"
        request.url = "http://test.com/test"
        request.method = "GET"
        return request
    
    @pytest.mark.asyncio
    async def test_valid_token_with_permissions(self, auth_dependency, mock_request):
        """Test successful authentication with valid token and permissions."""
        
        # Mock credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-token"
        )
        
        # Mock token manager
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.return_value = {
                "sub": "user-123",
                "preferred_username": "testuser",
                "permissions": ["migrations:read", "databases:read"]
            }
            mock_get_manager.return_value = mock_manager
            
            # Call dependency
            result = await auth_dependency(mock_request, credentials)
            
            # Assertions
            assert result["sub"] == "user-123"
            assert result["preferred_username"] == "testuser"
            assert "migrations:read" in result["permissions"]
            assert result["client_ip"] == "127.0.0.1"
    
    @pytest.mark.asyncio
    async def test_missing_credentials(self, auth_dependency, mock_request):
        """Test authentication failure with missing credentials."""
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_dependency(mock_request, None)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_invalid_token(self, auth_dependency, mock_request):
        """Test authentication failure with invalid token."""
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-token"
        )
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.side_effect = AuthenticationException("Invalid token")
            mock_get_manager.return_value = mock_manager
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_dependency(mock_request, credentials)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_insufficient_permissions(self, mock_request):
        """Test authorization failure with insufficient permissions."""
        
        auth_dependency = InfrastructureAuth(["infrastructure:admin"])
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-token"
        )
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.side_effect = AuthenticationException(
                "Missing required permissions: infrastructure:admin"
            )
            mock_get_manager.return_value = mock_manager
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_dependency(mock_request, credentials)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_any_permission_logic(self, mock_request):
        """Test 'any permission' authorization logic."""
        
        auth_dependency = InfrastructureAuth(
            ["migrations:admin", "infrastructure:admin"],
            any_permission=True
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-token"
        )
        
        with patch('src.features.auth.dependencies.get_token_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_manager.validate_token.return_value = {
                "sub": "user-123",
                "preferred_username": "testuser",
                "permissions": ["migrations:read"]  # Doesn't have required perms
            }
            mock_get_manager.return_value = mock_manager
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_dependency(mock_request, credentials)
            
            assert exc_info.value.status_code == 403
```

---

## 🔒 Security Considerations

### Token Security
- **Token Expiration**: Enforce reasonable token expiration times
- **Token Revocation**: Support for token revocation checks
- **Rate Limiting**: Prevent brute force attacks on authentication
- **Secure Headers**: Add security headers to all responses

### Permission Security
- **Principle of Least Privilege**: Grant minimum required permissions
- **Permission Validation**: Validate permissions on every request
- **Audit Logging**: Log all authentication and authorization events
- **Regular Review**: Periodic review of user permissions

### Configuration Security
```python
# Environment variables for secure configuration
KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=master
KEYCLOAK_CLIENT_ID=infrastructure-api
KEYCLOAK_CLIENT_SECRET=secure-client-secret

# Redis for caching (optional)
REDIS_URL=redis://redis:6379/1

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# CORS configuration
CORS_ALLOW_ORIGINS=["https://admin.example.com"]
CORS_ALLOW_CREDENTIALS=true
```

---

## 📋 Implementation Checklist

### Phase 1: Core Authentication (Week 1)
- [ ] Copy and adapt Keycloak client from Admin API
- [ ] Implement token validation with caching
- [ ] Create infrastructure permission mappings
- [ ] Setup authentication dependencies
- [ ] Implement basic auth endpoints

### Phase 2: Authorization System (Week 1)
- [ ] Define infrastructure permission model
- [ ] Implement role-to-permission mapping
- [ ] Create permission validation middleware
- [ ] Add audit logging for auth events
- [ ] Test permission enforcement

### Phase 3: Integration & Testing (Week 2)
- [ ] Integrate with existing Keycloak setup
- [ ] Add comprehensive test coverage
- [ ] Performance test token validation
- [ ] Security audit of authentication flow
- [ ] Documentation and examples

### Phase 4: Production Hardening
- [ ] Configure production security settings
- [ ] Setup monitoring and alerting
- [ ] Implement rate limiting
- [ ] Security headers configuration
- [ ] Load testing and optimization

---

## 🚀 Performance Optimization

### Caching Strategy
- **Token Validation**: Cache valid tokens for 5 minutes
- **Permission Lookup**: Cache user permissions
- **Redis Integration**: Use Redis for distributed caching
- **Cache Invalidation**: Clear cache on permission changes

### Monitoring
- **Authentication Metrics**: Success/failure rates
- **Performance Metrics**: Token validation times
- **Security Metrics**: Failed authentication attempts
- **Cache Metrics**: Hit/miss ratios

This authentication implementation guide provides a comprehensive approach to securing the Infrastructure API while maintaining high performance and following established security best practices.