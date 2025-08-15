"""
User context value objects.

Immutable types representing user identity and authorization context.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from enum import Enum


class UserType(str, Enum):
    """User type classification for authorization."""
    AUTHENTICATED = "authenticated"  # Full Keycloak-authenticated user
    GUEST = "guest"                 # Anonymous guest with limited access
    SERVICE = "service"             # Service account
    SYSTEM = "system"               # System/admin operation
    IMPERSONATED = "impersonated"   # User being impersonated by admin


@dataclass(frozen=True)
class UserContext:
    """
    Immutable user context for authorization decisions.
    
    Contains all user identity and context information needed for authorization.
    """
    # Core identity
    user_id: str
    user_type: UserType = UserType.AUTHENTICATED
    
    # Profile information
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    
    # Authorization context
    tenant_id: Optional[str] = None
    team_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Flags
    is_superadmin: bool = False
    is_active: bool = True
    email_verified: bool = False
    
    # Keycloak context (reference only)
    external_user_id: Optional[str] = None  # Keycloak sub claim
    realm: Optional[str] = None
    client_id: Optional[str] = None
    
    # Request context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata as empty dict if None."""
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is fully authenticated."""
        return self.user_type == UserType.AUTHENTICATED
    
    @property
    def is_guest(self) -> bool:
        """Check if this is a guest user."""
        return self.user_type == UserType.GUEST
    
    @property
    def is_service_account(self) -> bool:
        """Check if this is a service account."""
        return self.user_type == UserType.SERVICE
    
    @property
    def is_system(self) -> bool:
        """Check if this is a system operation."""
        return self.user_type == UserType.SYSTEM
    
    @property
    def is_impersonated(self) -> bool:
        """Check if user is being impersonated."""
        return self.user_type == UserType.IMPERSONATED
    
    @property
    def effective_display_name(self) -> str:
        """Get effective display name for UI."""
        return (
            self.display_name or
            self.username or
            self.email or
            f"user:{self.user_id}"
        )
    
    @property
    def context_key(self) -> str:
        """Get context key for authorization caching."""
        if self.tenant_id:
            if self.team_id:
                return f"tenant:{self.tenant_id}:team:{self.team_id}"
            return f"tenant:{self.tenant_id}"
        return "platform"
    
    def get_cache_namespace(self) -> str:
        """Get cache namespace for this user context."""
        return f"user:{self.user_id}:{self.context_key}"
    
    def has_tenant_context(self) -> bool:
        """Check if user has tenant context."""
        return self.tenant_id is not None
    
    def has_team_context(self) -> bool:
        """Check if user has team context."""
        return self.team_id is not None
    
    def matches_context(self, tenant_id: Optional[str] = None, team_id: Optional[str] = None) -> bool:
        """
        Check if this user context matches the given tenant/team context.
        
        Args:
            tenant_id: Tenant ID to match
            team_id: Team ID to match
            
        Returns:
            True if context matches
        """
        # Superadmin matches any context
        if self.is_superadmin:
            return True
        
        # Check tenant context
        if tenant_id and self.tenant_id != tenant_id:
            return False
        
        # Check team context
        if team_id and self.team_id != team_id:
            return False
        
        return True
    
    def with_tenant(self, tenant_id: str) -> "UserContext":
        """Create new context with tenant scope."""
        return UserContext(
            user_id=self.user_id,
            user_type=self.user_type,
            email=self.email,
            username=self.username,
            display_name=self.display_name,
            tenant_id=tenant_id,
            team_id=self.team_id,
            session_id=self.session_id,
            is_superadmin=self.is_superadmin,
            is_active=self.is_active,
            email_verified=self.email_verified,
            external_user_id=self.external_user_id,
            realm=self.realm,
            client_id=self.client_id,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            request_id=self.request_id,
            metadata=self.metadata
        )
    
    def with_team(self, team_id: str) -> "UserContext":
        """Create new context with team scope."""
        return UserContext(
            user_id=self.user_id,
            user_type=self.user_type,
            email=self.email,
            username=self.username,
            display_name=self.display_name,
            tenant_id=self.tenant_id,
            team_id=team_id,
            session_id=self.session_id,
            is_superadmin=self.is_superadmin,
            is_active=self.is_active,
            email_verified=self.email_verified,
            external_user_id=self.external_user_id,
            realm=self.realm,
            client_id=self.client_id,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            request_id=self.request_id,
            metadata=self.metadata
        )
    
    @classmethod
    def guest(cls, session_id: str, ip_address: Optional[str] = None) -> "UserContext":
        """Create guest user context."""
        return cls(
            user_id=f"guest:{session_id}",
            user_type=UserType.GUEST,
            session_id=session_id,
            ip_address=ip_address,
            is_active=True
        )
    
    @classmethod
    def system(cls, operation_id: str) -> "UserContext":
        """Create system operation context."""
        return cls(
            user_id=f"system:{operation_id}",
            user_type=UserType.SYSTEM,
            is_superadmin=True,
            is_active=True
        )
    
    @classmethod
    def service_account(cls, client_id: str, realm: str) -> "UserContext":
        """Create service account context."""
        return cls(
            user_id=f"service:{client_id}",
            user_type=UserType.SERVICE,
            client_id=client_id,
            realm=realm,
            is_active=True
        )
    
    def __str__(self) -> str:
        return f"{self.user_type}:{self.effective_display_name}"
    
    def __repr__(self) -> str:
        return f"UserContext(id='{self.user_id}', type='{self.user_type}', context='{self.context_key}')"