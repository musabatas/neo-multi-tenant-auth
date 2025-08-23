"""Authentication context entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set

from ....core.value_objects.identifiers import (
    KeycloakUserId,
    PermissionCode,
    RealmId,
    RoleCode,
    TenantId,
    UserId,
)


@dataclass(frozen=True)
class AuthContext:
    """Authentication context containing user and permission information."""
    
    # User identifiers
    user_id: UserId
    keycloak_user_id: KeycloakUserId
    tenant_id: TenantId
    realm_id: RealmId
    
    # User information
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    
    # Authentication info
    authenticated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    session_id: Optional[str] = None
    
    # Authorization info
    roles: Set[RoleCode] = None
    permissions: Set[PermissionCode] = None
    scopes: Set[str] = None
    
    # Token claims
    token_claims: Dict = None
    
    # User metadata
    metadata: Dict = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        # Set defaults using object.__setattr__ since dataclass is frozen
        if self.roles is None:
            object.__setattr__(self, 'roles', set())
        
        if self.permissions is None:
            object.__setattr__(self, 'permissions', set())
        
        if self.scopes is None:
            object.__setattr__(self, 'scopes', set())
        
        if self.token_claims is None:
            object.__setattr__(self, 'token_claims', {})
        
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
        
        if self.authenticated_at is None:
            object.__setattr__(self, 'authenticated_at', datetime.utcnow())
    
    @property
    def full_name(self) -> Optional[str]:
        """Get user's full name."""
        if self.display_name:
            return self.display_name
        
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        
        if self.first_name:
            return self.first_name
        
        if self.last_name:
            return self.last_name
        
        return self.username or self.email
    
    @property
    def is_expired(self) -> bool:
        """Check if authentication context is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at
    
    def has_role(self, role: str | RoleCode) -> bool:
        """Check if user has specific role."""
        role_code = role if isinstance(role, RoleCode) else RoleCode(role)
        return role_code in self.roles
    
    def has_any_role(self, roles: List[str | RoleCode]) -> bool:
        """Check if user has any of the specified roles."""
        role_codes = {
            role if isinstance(role, RoleCode) else RoleCode(role)
            for role in roles
        }
        return bool(self.roles & role_codes)
    
    def has_all_roles(self, roles: List[str | RoleCode]) -> bool:
        """Check if user has all specified roles."""
        role_codes = {
            role if isinstance(role, RoleCode) else RoleCode(role)
            for role in roles
        }
        return role_codes.issubset(self.roles)
    
    def has_permission(self, permission: str | PermissionCode) -> bool:
        """Check if user has specific permission."""
        perm_code = (
            permission if isinstance(permission, PermissionCode) 
            else PermissionCode(permission)
        )
        return perm_code in self.permissions
    
    def has_any_permission(self, permissions: List[str | PermissionCode]) -> bool:
        """Check if user has any of the specified permissions."""
        perm_codes = {
            perm if isinstance(perm, PermissionCode) else PermissionCode(perm)
            for perm in permissions
        }
        return bool(self.permissions & perm_codes)
    
    def has_all_permissions(self, permissions: List[str | PermissionCode]) -> bool:
        """Check if user has all specified permissions."""
        perm_codes = {
            perm if isinstance(perm, PermissionCode) else PermissionCode(perm)
            for perm in permissions
        }
        return perm_codes.issubset(self.permissions)
    
    def has_scope(self, scope: str) -> bool:
        """Check if user has specific scope."""
        return scope in self.scopes
    
    def get_claim(self, claim_name: str, default=None):
        """Get a specific claim from token."""
        return self.token_claims.get(claim_name, default)
    
    def get_metadata(self, key: str, default=None):
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict:
        """Convert auth context to dictionary."""
        return {
            'user_id': self.user_id.value,
            'keycloak_user_id': self.keycloak_user_id.value,
            'tenant_id': self.tenant_id.value,
            'realm_id': self.realm_id.value,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'display_name': self.display_name,
            'authenticated_at': self.authenticated_at.isoformat() if self.authenticated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'session_id': self.session_id,
            'roles': [role.value for role in self.roles] if self.roles else [],
            'permissions': [perm.value for perm in self.permissions] if self.permissions else [],
            'scopes': list(self.scopes) if self.scopes else [],
            'token_claims': self.token_claims,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AuthContext':
        """Create auth context from dictionary (for cache deserialization)."""
        from datetime import datetime
        
        # Parse timestamps
        authenticated_at = None
        expires_at = None
        
        if data.get('authenticated_at'):
            authenticated_at = datetime.fromisoformat(data['authenticated_at'])
        
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        # Convert role and permission strings back to value objects
        roles = {RoleCode(role) for role in data.get('roles', [])}
        permissions = {PermissionCode(perm) for perm in data.get('permissions', [])}
        scopes = set(data.get('scopes', []))
        
        return cls(
            user_id=UserId(data['user_id']),
            keycloak_user_id=KeycloakUserId(data['keycloak_user_id']),
            tenant_id=TenantId(data['tenant_id']),
            realm_id=RealmId(data['realm_id']),
            email=data.get('email'),
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            display_name=data.get('display_name'),
            authenticated_at=authenticated_at,
            expires_at=expires_at,
            session_id=data.get('session_id'),
            roles=roles,
            permissions=permissions,
            scopes=scopes,
            token_claims=data.get('token_claims', {}),
            metadata=data.get('metadata', {}),
        )
    
    @classmethod
    def from_token_claims(
        cls,
        claims: Dict,
        user_id: UserId,
        keycloak_user_id: KeycloakUserId,
        tenant_id: TenantId,
        realm_id: RealmId,
        roles: Optional[Set[RoleCode]] = None,
        permissions: Optional[Set[PermissionCode]] = None,
    ) -> 'AuthContext':
        """Create auth context from JWT token claims."""
        
        # Extract user info from claims
        email = claims.get('email')
        username = claims.get('preferred_username')
        first_name = claims.get('given_name')
        last_name = claims.get('family_name')
        display_name = claims.get('name')
        
        # Extract scopes
        scope_str = claims.get('scope', '')
        scopes = set(scope_str.split()) if scope_str else set()
        
        # Extract session info
        session_id = claims.get('session_state')
        
        # Parse timestamps
        authenticated_at = None
        expires_at = None
        
        if 'iat' in claims:
            authenticated_at = datetime.utcfromtimestamp(claims['iat'])
        
        if 'exp' in claims:
            expires_at = datetime.utcfromtimestamp(claims['exp'])
        
        return cls(
            user_id=user_id,
            keycloak_user_id=keycloak_user_id,
            tenant_id=tenant_id,
            realm_id=realm_id,
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            authenticated_at=authenticated_at,
            expires_at=expires_at,
            session_id=session_id,
            roles=roles or set(),
            permissions=permissions or set(),
            scopes=scopes,
            token_claims=claims,
        )