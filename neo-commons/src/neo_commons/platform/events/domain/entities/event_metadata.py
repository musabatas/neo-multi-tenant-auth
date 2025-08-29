"""Event metadata entity for storing additional event context."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID


@dataclass
class EventMetadata:
    """Metadata associated with an event for context and tracking."""
    
    # Request context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    
    # User context
    user_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    
    # Source context
    source_service: Optional[str] = None
    source_version: Optional[str] = None
    
    # Custom metadata
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate metadata fields."""
        # Convert string UUIDs to UUID objects
        if self.user_id is not None and not isinstance(self.user_id, UUID):
            try:
                self.user_id = UUID(str(self.user_id))
            except (ValueError, TypeError):
                raise ValueError(f"user_id must be a valid UUID, got: {self.user_id}")
        
        if self.tenant_id is not None and not isinstance(self.tenant_id, UUID):
            try:
                self.tenant_id = UUID(str(self.tenant_id))
            except (ValueError, TypeError):
                raise ValueError(f"tenant_id must be a valid UUID, got: {self.tenant_id}")
        
        if self.organization_id is not None and not isinstance(self.organization_id, UUID):
            try:
                self.organization_id = UUID(str(self.organization_id))
            except (ValueError, TypeError):
                raise ValueError(f"organization_id must be a valid UUID, got: {self.organization_id}")
    
    def add_custom(self, key: str, value: Any) -> None:
        """Add custom metadata field."""
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Custom metadata key must be a non-empty string")
        
        self.custom[key] = value
    
    def get_custom(self, key: str, default: Any = None) -> Any:
        """Get custom metadata field."""
        return self.custom.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        
        # Add non-None standard fields
        if self.ip_address is not None:
            result['ip_address'] = self.ip_address
        if self.user_agent is not None:
            result['user_agent'] = self.user_agent
        if self.request_id is not None:
            result['request_id'] = self.request_id
        if self.user_id is not None:
            result['user_id'] = str(self.user_id)
        if self.tenant_id is not None:
            result['tenant_id'] = str(self.tenant_id)
        if self.organization_id is not None:
            result['organization_id'] = str(self.organization_id)
        if self.source_service is not None:
            result['source_service'] = self.source_service
        if self.source_version is not None:
            result['source_version'] = self.source_version
        
        # Add custom fields
        if self.custom:
            result['custom'] = self.custom
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventMetadata':
        """Create from dictionary representation."""
        custom = data.pop('custom', {})
        
        # Convert UUID strings back to UUIDs
        if 'user_id' in data and data['user_id'] is not None:
            data['user_id'] = UUID(data['user_id'])
        if 'tenant_id' in data and data['tenant_id'] is not None:
            data['tenant_id'] = UUID(data['tenant_id'])
        if 'organization_id' in data and data['organization_id'] is not None:
            data['organization_id'] = UUID(data['organization_id'])
        
        return cls(**data, custom=custom)
    
    @classmethod
    def create_empty(cls) -> 'EventMetadata':
        """Create empty metadata instance."""
        return cls()
    
    def __repr__(self) -> str:
        return f"EventMetadata({self.to_dict()})"