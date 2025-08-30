"""Realm identifier value object with validation rules."""

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class RealmIdentifier:
    """Realm identifier value object for multi-realm authentication.
    
    Handles ONLY realm identification and validation.
    Does not manage realm configuration - that's handled by realm providers.
    """
    
    value: str
    
    # Class constants for validation
    MIN_LENGTH: ClassVar[int] = 2
    MAX_LENGTH: ClassVar[int] = 100
    
    def __post_init__(self) -> None:
        """Validate realm identifier format and rules."""
        if not self.value:
            raise ValueError("Realm identifier cannot be empty")
        
        if not isinstance(self.value, str):
            raise TypeError("Realm identifier must be a string")
        
        # Normalize to lowercase
        normalized_value = self.value.lower().strip()
        object.__setattr__(self, 'value', normalized_value)
        
        # Validate length
        if len(self.value) < self.MIN_LENGTH:
            raise ValueError(f"Realm identifier must be at least {self.MIN_LENGTH} characters")
        
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(f"Realm identifier cannot exceed {self.MAX_LENGTH} characters")
        
        # Validate character set (alphanumeric, hyphens, underscores)
        # Must start and end with alphanumeric
        if not re.match(r'^[a-z0-9][a-z0-9_-]*[a-z0-9]$', self.value):
            if len(self.value) == 1:
                # Single character must be alphanumeric
                if not re.match(r'^[a-z0-9]$', self.value):
                    raise ValueError("Single character realm identifier must be alphanumeric")
            else:
                raise ValueError("Realm identifier must start and end with alphanumeric characters, contain only lowercase letters, numbers, hyphens, and underscores")
        
        # Validate against reserved names
        if self._is_reserved_name():
            raise ValueError(f"Realm identifier '{self.value}' is reserved")
        
        # Validate against common patterns that could cause issues
        if self._has_problematic_patterns():
            raise ValueError(f"Realm identifier '{self.value}' contains problematic patterns")
    
    def _is_reserved_name(self) -> bool:
        """Check if realm identifier uses reserved names."""
        reserved_names = {
            # System reserved
            'master', 'admin', 'system', 'root', 'api',
            'default', 'public', 'private', 'internal',
            
            # Keycloak reserved
            'master-realm', 'account', 'account-console',
            'admin-cli', 'broker', 'realm-management',
            'security-admin-console',
            
            # HTTP/URL reserved
            'www', 'api', 'app', 'web', 'mobile',
            'staging', 'production', 'development', 'test',
            
            # Database reserved
            'postgres', 'mysql', 'redis', 'mongodb',
            'database', 'db', 'schema',
            
            # Common service names
            'auth', 'oauth', 'sso', 'ldap', 'saml',
            'jwt', 'token', 'session', 'login', 'logout'
        }
        
        return self.value in reserved_names
    
    def _has_problematic_patterns(self) -> bool:
        """Check for patterns that could cause issues."""
        # Multiple consecutive hyphens or underscores
        if '--' in self.value or '__' in self.value:
            return True
        
        # Starts or ends with hyphen/underscore (should be caught by regex, but double-check)
        if self.value.startswith(('-', '_')) or self.value.endswith(('-', '_')):
            return True
        
        # All hyphens/underscores
        if all(c in '-_' for c in self.value):
            return True
        
        # Common problematic patterns
        problematic_patterns = [
            'tenant-', '-tenant', 'user-', '-user',
            'org-', '-org', 'client-', '-client'
        ]
        
        return any(pattern in self.value for pattern in problematic_patterns)
    
    @property
    def is_default_realm(self) -> bool:
        """Check if this is a default/fallback realm."""
        return self.value in {'default', 'main', 'primary'}
    
    @property
    def is_tenant_realm(self) -> bool:
        """Check if this appears to be a tenant-specific realm."""
        # Common tenant realm patterns
        tenant_patterns = [
            r'^tenant-[a-z0-9]+$',
            r'^[a-z0-9]+-tenant$', 
            r'^org-[a-z0-9]+$',
            r'^[a-z0-9]+-org$'
        ]
        
        return any(re.match(pattern, self.value) for pattern in tenant_patterns)
    
    @classmethod
    def from_tenant_slug(cls, tenant_slug: str) -> 'RealmIdentifier':
        """Create realm identifier from tenant slug.
        
        Args:
            tenant_slug: Tenant slug to convert
            
        Returns:
            RealmIdentifier for the tenant
        """
        if not tenant_slug:
            raise ValueError("Tenant slug cannot be empty")
        
        # Create tenant-prefixed realm identifier
        realm_value = f"tenant-{tenant_slug.lower().strip()}"
        return cls(realm_value)
    
    @classmethod
    def default(cls) -> 'RealmIdentifier':
        """Create default realm identifier.
        
        Returns:
            Default RealmIdentifier instance
        """
        return cls('default')
    
    def to_keycloak_realm_name(self) -> str:
        """Convert to Keycloak realm name format.
        
        Returns:
            Keycloak-compatible realm name
        """
        # Keycloak realm names are case-sensitive, use original case if needed
        # For now, use lowercase as normalized
        return self.value
    
    def __str__(self) -> str:
        """String representation."""
        return f"RealmIdentifier({self.value})"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"RealmIdentifier(value='{self.value}')"