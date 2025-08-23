"""Keycloak configuration entity."""

from dataclasses import dataclass
from typing import Dict, Optional

from ....core.value_objects.identifiers import RealmId, TenantId


@dataclass(frozen=True)
class KeycloakConfig:
    """Keycloak realm configuration for a tenant."""
    
    # Keycloak connection details (required)
    server_url: str
    realm_name: str
    client_id: str
    
    # Core identifiers (optional for admin/platform configurations)
    realm_id: Optional[RealmId] = None
    tenant_id: Optional[TenantId] = None
    client_secret: Optional[str] = None
    
    # Authentication settings
    verify_signature: bool = True
    verify_audience: bool = True
    verify_exp: bool = True
    verify_nbf: bool = True
    verify_iat: bool = True
    
    # Token settings
    algorithms: list[str] = None
    audience: Optional[str] = None
    issuer: Optional[str] = None
    
    # Connection settings
    timeout: int = 30
    max_retries: int = 3
    
    # Security settings
    require_https: bool = True
    check_revocation: bool = False
    
    # Caching settings
    cache_public_key: bool = True
    public_key_ttl: int = 3600  # 1 hour
    
    # Additional configuration
    metadata: Dict = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.server_url:
            raise ValueError("server_url is required")
        
        if not self.realm_name:
            raise ValueError("realm_name is required")
            
        if not self.client_id:
            raise ValueError("client_id is required")
        
        if self.require_https and not self.server_url.startswith('https://'):
            raise ValueError("HTTPS is required but server_url is not HTTPS")
        
        # Set defaults using object.__setattr__ since dataclass is frozen
        if self.algorithms is None:
            object.__setattr__(self, 'algorithms', ['RS256'])
            
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
    
    @property
    def auth_url(self) -> str:
        """Get the authentication URL for this realm."""
        return f"{self.server_url}/realms/{self.realm_name}/protocol/openid-connect/auth"
    
    @property
    def token_url(self) -> str:
        """Get the token URL for this realm."""
        return f"{self.server_url}/realms/{self.realm_name}/protocol/openid-connect/token"
    
    @property
    def userinfo_url(self) -> str:
        """Get the userinfo URL for this realm."""
        return f"{self.server_url}/realms/{self.realm_name}/protocol/openid-connect/userinfo"
    
    @property
    def jwks_url(self) -> str:
        """Get the JWKS URL for this realm."""
        return f"{self.server_url}/realms/{self.realm_name}/protocol/openid-connect/certs"
    
    @property
    def introspect_url(self) -> str:
        """Get the token introspection URL for this realm."""
        return f"{self.server_url}/realms/{self.realm_name}/protocol/openid-connect/token/introspect"
    
    @property
    def logout_url(self) -> str:
        """Get the logout URL for this realm."""
        return f"{self.server_url}/realms/{self.realm_name}/protocol/openid-connect/logout"
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'realm_id': self.realm_id.value if self.realm_id else None,
            'tenant_id': self.tenant_id.value if self.tenant_id else None,
            'server_url': self.server_url,
            'realm_name': self.realm_name,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'verify_signature': self.verify_signature,
            'verify_audience': self.verify_audience,
            'verify_exp': self.verify_exp,
            'verify_nbf': self.verify_nbf,
            'verify_iat': self.verify_iat,
            'algorithms': self.algorithms,
            'audience': self.audience,
            'issuer': self.issuer,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'require_https': self.require_https,
            'check_revocation': self.check_revocation,
            'cache_public_key': self.cache_public_key,
            'public_key_ttl': self.public_key_ttl,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'KeycloakConfig':
        """Create configuration from dictionary."""
        return cls(
            server_url=data['server_url'],
            realm_name=data['realm_name'],
            client_id=data['client_id'],
            realm_id=RealmId(data['realm_id']) if data.get('realm_id') else None,
            tenant_id=TenantId(data['tenant_id']) if data.get('tenant_id') else None,
            client_secret=data.get('client_secret'),
            verify_signature=data.get('verify_signature', True),
            verify_audience=data.get('verify_audience', True),
            verify_exp=data.get('verify_exp', True),
            verify_nbf=data.get('verify_nbf', True),
            verify_iat=data.get('verify_iat', True),
            algorithms=data.get('algorithms', ['RS256']),
            audience=data.get('audience'),
            issuer=data.get('issuer'),
            timeout=data.get('timeout', 30),
            max_retries=data.get('max_retries', 3),
            require_https=data.get('require_https', True),
            check_revocation=data.get('check_revocation', False),
            cache_public_key=data.get('cache_public_key', True),
            public_key_ttl=data.get('public_key_ttl', 3600),
            metadata=data.get('metadata', {}),
        )