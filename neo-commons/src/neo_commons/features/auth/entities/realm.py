"""Keycloak realm entity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from ....core.value_objects.identifiers import RealmId, TenantId
from .keycloak_config import KeycloakConfig


@dataclass(frozen=True)
class Realm:
    """Keycloak realm entity."""
    
    # Core identifiers
    realm_id: RealmId
    tenant_id: TenantId
    
    # Realm info
    name: str
    display_name: Optional[str] = None
    enabled: bool = True
    
    # Configuration
    config: KeycloakConfig = None
    
    # Status
    status: str = "active"  # active, disabled, deleted
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict = None
    
    def __post_init__(self):
        """Validate realm data."""
        if not self.name:
            raise ValueError("Realm name is required")
        
        # Set defaults using object.__setattr__ since dataclass is frozen
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
        
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.utcnow())
        
        if self.updated_at is None:
            object.__setattr__(self, 'updated_at', datetime.utcnow())
    
    @property
    def is_active(self) -> bool:
        """Check if realm is active."""
        return self.enabled and self.status == "active"
    
    @property
    def realm_pattern(self) -> str:
        """Get realm naming pattern (tenant-{tenant_slug})."""
        return f"tenant-{self.tenant_id.value}"
    
    def get_metadata(self, key: str, default=None):
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict:
        """Convert realm to dictionary."""
        return {
            'realm_id': self.realm_id.value,
            'tenant_id': self.tenant_id.value,
            'name': self.name,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.metadata,
            'config': self.config.to_dict() if self.config else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Realm':
        """Create realm from dictionary."""
        config = None
        if data.get('config'):
            config = KeycloakConfig.from_dict(data['config'])
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            realm_id=RealmId(data['realm_id']),
            tenant_id=TenantId(data['tenant_id']),
            name=data['name'],
            display_name=data.get('display_name'),
            enabled=data.get('enabled', True),
            config=config,
            status=data.get('status', 'active'),
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get('metadata', {}),
        )