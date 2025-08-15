"""
Session entity - Keycloak session context and validation.

Represents validated Keycloak tokens and session state for authorization decisions.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from datetime import datetime


class SessionStatus(str, Enum):
    """Session status for tracking active sessions."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"


class UserType(str, Enum):
    """User type classification."""
    AUTHENTICATED = "authenticated"  # Keycloak-authenticated user
    GUEST = "guest"                 # Anonymous guest session
    SERVICE = "service"             # Service account
    SYSTEM = "system"               # System operation


@dataclass(frozen=True)
class SessionContext:
    """
    Keycloak session context extracted from validated tokens.
    
    Contains all relevant information from JWT claims for authorization.
    """
    # Core session info
    session_id: str
    user_id: str  # Keycloak subject (sub claim)
    user_type: UserType = UserType.AUTHENTICATED
    
    # Token info
    token_issued_at: datetime = None
    token_expires_at: datetime = None
    token_scopes: List[str] = None
    
    # Keycloak context
    realm: str = None
    client_id: str = None
    authorized_party: Optional[str] = None
    authentication_context_class: Optional[str] = None
    
    # User profile from Keycloak
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email_verified: bool = False
    
    # Keycloak roles (for reference only - authorization uses our DB)
    realm_roles: List[str] = None
    client_roles: Dict[str, List[str]] = None
    
    # Request context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    tenant_id: Optional[str] = None  # Derived from request or token
    
    def __post_init__(self):
        """Initialize collections as empty if None."""
        if self.token_scopes is None:
            object.__setattr__(self, 'token_scopes', [])
        if self.realm_roles is None:
            object.__setattr__(self, 'realm_roles', [])
        if self.client_roles is None:
            object.__setattr__(self, 'client_roles', {})
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        if self.token_expires_at is None:
            return False
        from neo_commons.utils.datetime import utc_now
        return utc_now() > self.token_expires_at
    
    @property
    def is_guest(self) -> bool:
        """Check if this is a guest session."""
        return self.user_type == UserType.GUEST
    
    @property
    def is_authenticated(self) -> bool:
        """Check if this is an authenticated user."""
        return self.user_type == UserType.AUTHENTICATED
    
    @property
    def is_service_account(self) -> bool:
        """Check if this is a service account."""
        return self.user_type == UserType.SERVICE
    
    @property
    def full_name(self) -> Optional[str]:
        """Get full name from first and last name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name
    
    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        return self.full_name or self.username or self.email or f"user:{self.user_id}"
    
    def has_realm_role(self, role: str) -> bool:
        """Check if user has a Keycloak realm role."""
        return role in self.realm_roles
    
    def has_client_role(self, client: str, role: str) -> bool:
        """Check if user has a Keycloak client role."""
        return client in self.client_roles and role in self.client_roles[client]
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        return scope in self.token_scopes
    
    def get_cache_key(self) -> str:
        """Generate cache key for this session."""
        return f"session:{self.session_id}"
    
    def get_context_key(self) -> str:
        """Get context key for authorization."""
        if self.tenant_id:
            return f"tenant:{self.tenant_id}"
        return "platform"
    
    @classmethod
    def from_keycloak_token(cls, token_claims: Dict[str, Any], **kwargs) -> "SessionContext":
        """
        Create session context from Keycloak JWT token claims.
        
        Args:
            token_claims: Decoded JWT token claims
            **kwargs: Additional context (ip_address, user_agent, tenant_id)
        """
        from datetime import datetime, timezone
        
        # Extract realm roles
        realm_access = token_claims.get("realm_access", {})
        realm_roles = realm_access.get("roles", [])
        
        # Extract client roles
        resource_access = token_claims.get("resource_access", {})
        client_roles = {}
        for client, access in resource_access.items():
            if "roles" in access:
                client_roles[client] = access["roles"]
        
        return cls(
            session_id=token_claims.get("sid", token_claims.get("jti", "unknown")),
            user_id=token_claims.get("sub"),
            token_issued_at=datetime.fromtimestamp(token_claims.get("iat", 0), timezone.utc) if token_claims.get("iat") else None,
            token_expires_at=datetime.fromtimestamp(token_claims.get("exp", 0), timezone.utc) if token_claims.get("exp") else None,
            token_scopes=token_claims.get("scope", "").split() if token_claims.get("scope") else [],
            realm=token_claims.get("iss", "").split("/")[-1] if token_claims.get("iss") else None,
            client_id=token_claims.get("aud"),
            authorized_party=token_claims.get("azp"),
            authentication_context_class=token_claims.get("acr"),
            email=token_claims.get("email"),
            username=token_claims.get("preferred_username"),
            first_name=token_claims.get("given_name"),
            last_name=token_claims.get("family_name"),
            email_verified=token_claims.get("email_verified", False),
            realm_roles=realm_roles,
            client_roles=client_roles,
            **kwargs
        )


@dataclass(frozen=True)
class Session:
    """
    Complete session state with validation and authorization context.
    
    Combines Keycloak session context with our authorization data.
    """
    # Core session
    context: SessionContext
    status: SessionStatus = SessionStatus.ACTIVE
    
    # Security tracking
    created_at: datetime = None
    last_accessed_at: datetime = None
    access_count: int = 0
    
    # Rate limiting
    rate_limit_remaining: int = 1000
    rate_limit_reset: datetime = None
    
    # Authorization cache info
    permissions_cache_key: Optional[str] = None
    roles_cache_key: Optional[str] = None
    acl_cache_key: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            from neo_commons.utils.datetime import utc_now
            now = utc_now()
            object.__setattr__(self, 'created_at', now)
            if self.last_accessed_at is None:
                object.__setattr__(self, 'last_accessed_at', now)
    
    @property
    def is_valid(self) -> bool:
        """Check if session is currently valid."""
        return (
            self.status == SessionStatus.ACTIVE and 
            not self.context.is_expired and
            self.rate_limit_remaining > 0
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return self.status == SessionStatus.EXPIRED or self.context.is_expired
    
    @property
    def is_revoked(self) -> bool:
        """Check if session was revoked."""
        return self.status == SessionStatus.REVOKED
    
    @property
    def user_id(self) -> str:
        """Get user ID from context."""
        return self.context.user_id
    
    @property
    def session_id(self) -> str:
        """Get session ID from context."""
        return self.context.session_id
    
    @property
    def tenant_id(self) -> Optional[str]:
        """Get tenant ID from context."""
        return self.context.tenant_id
    
    def validate_security_context(self, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
        """
        Validate security context for session hijacking detection.
        
        Args:
            ip_address: Current request IP address
            user_agent: Current request user agent
            
        Returns:
            True if security context is valid
        """
        # For now, simple validation - can be enhanced with fingerprinting
        if ip_address and self.context.ip_address:
            return ip_address == self.context.ip_address
        
        if user_agent and self.context.user_agent:
            return user_agent == self.context.user_agent
        
        return True
    
    def record_access(self) -> "Session":
        """Record session access and update counters."""
        from neo_commons.utils.datetime import utc_now
        
        return Session(
            context=self.context,
            status=self.status,
            created_at=self.created_at,
            last_accessed_at=utc_now(),
            access_count=self.access_count + 1,
            rate_limit_remaining=max(0, self.rate_limit_remaining - 1),
            rate_limit_reset=self.rate_limit_reset,
            permissions_cache_key=self.permissions_cache_key,
            roles_cache_key=self.roles_cache_key,
            acl_cache_key=self.acl_cache_key
        )
    
    def invalidate(self, reason: str = "Manual invalidation") -> "Session":
        """Invalidate the session."""
        return Session(
            context=self.context,
            status=SessionStatus.REVOKED,
            created_at=self.created_at,
            last_accessed_at=self.last_accessed_at,
            access_count=self.access_count,
            rate_limit_remaining=self.rate_limit_remaining,
            rate_limit_reset=self.rate_limit_reset
        )
    
    def get_authorization_cache_keys(self) -> Dict[str, str]:
        """Get all authorization-related cache keys."""
        base = f"auth:{self.user_id}"
        context = self.context.get_context_key()
        
        return {
            "permissions": f"{base}:perms:{context}",
            "roles": f"{base}:roles:{context}",
            "acl": f"{base}:acl:{context}"
        }
    
    def __str__(self) -> str:
        return f"Session({self.session_id}, {self.status.value})"
    
    def __repr__(self) -> str:
        return f"Session(user={self.user_id}, status={self.status}, valid={self.is_valid})"