"""
Core authentication enums and constants.

Defines fundamental enums used throughout the authentication system
for validation strategies, permission scopes, and auth-related status values.
"""

from enum import Enum


class ValidationStrategy(Enum):
    """
    Token validation strategies for different security requirements.
    
    Used to determine how JWT tokens are validated in the system:
    - LOCAL: Fast validation using cached public keys
    - INTROSPECTION: Secure server-side validation via Keycloak
    - DUAL: Both local and server-side validation for critical operations
    """
    LOCAL = "local"  # Fast JWT validation with cached public keys
    INTROSPECTION = "introspection"  # Secure server-side validation
    DUAL = "dual"  # Both local and introspection validation


class PermissionScope(Enum):
    """
    Permission scope levels for multi-tenant authorization.
    
    Defines the scope at which permissions are evaluated:
    - PLATFORM: System-wide permissions (admin operations)
    - TENANT: Tenant-scoped permissions (within organization)
    - USER: User-specific permissions (personal data access)
    """
    PLATFORM = "platform"  # Platform-wide permissions
    TENANT = "tenant"  # Tenant-scoped permissions
    USER = "user"  # User-specific permissions


class AuthenticationStatus(Enum):
    """
    Authentication status for user sessions and token validation.
    
    Represents the current authentication state:
    - AUTHENTICATED: Valid, active authentication
    - EXPIRED: Authentication expired, needs refresh
    - INVALID: Authentication is invalid
    - REVOKED: Authentication has been revoked
    - PENDING: Authentication in progress
    """
    AUTHENTICATED = "authenticated"
    EXPIRED = "expired"
    INVALID = "invalid"
    REVOKED = "revoked"
    PENDING = "pending"


class PermissionAction(Enum):
    """
    Standard permission actions for RBAC operations.
    
    Common actions that can be performed on resources:
    - CREATE: Create new resources
    - READ: Read/view resources
    - UPDATE: Modify existing resources
    - DELETE: Remove resources
    - EXECUTE: Execute or run operations
    """
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"


class CacheStrategy(Enum):
    """
    Caching strategies for auth data with different TTL and invalidation rules.
    
    - AGGRESSIVE: Long TTL, high performance, eventual consistency
    - BALANCED: Medium TTL, good performance with reasonable freshness
    - CONSERVATIVE: Short TTL, strong consistency, lower performance
    - CRITICAL: No caching, always fetch fresh data
    """
    AGGRESSIVE = "aggressive"  # Long TTL (1 hour+)
    BALANCED = "balanced"  # Medium TTL (5-15 minutes)
    CONSERVATIVE = "conservative"  # Short TTL (1-5 minutes)
    CRITICAL = "critical"  # No caching


class SessionType(Enum):
    """
    Types of user sessions supported by the authentication system.
    
    - USER: Authenticated user session with full permissions
    - GUEST: Unauthenticated guest session with limited access
    - SERVICE: Service-to-service authentication session
    - ADMIN: Administrative session with elevated privileges
    """
    USER = "user"
    GUEST = "guest"
    SERVICE = "service"
    ADMIN = "admin"


class TokenType(Enum):
    """
    Types of authentication tokens used in the system.
    
    - ACCESS: Short-lived access token for API requests
    - REFRESH: Long-lived token for renewing access tokens
    - ID: Identity token containing user claims
    - SESSION: Session token for web applications
    """
    ACCESS = "access"
    REFRESH = "refresh"
    ID = "id"
    SESSION = "session"


__all__ = [
    "ValidationStrategy",
    "PermissionScope",
    "AuthenticationStatus",
    "PermissionAction",
    "CacheStrategy",
    "SessionType",
    "TokenType",
]