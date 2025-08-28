"""Cache namespace domain entity.

ONLY namespace entity - provides logical grouping of cache entries
with bulk operations, isolation, and namespace-level policies.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..value_objects.cache_ttl import CacheTTL


class EvictionPolicy(Enum):
    """Cache eviction policies for namespace-level control."""
    
    LRU = "lru"           # Least Recently Used
    LFU = "lfu"           # Least Frequently Used
    FIFO = "fifo"         # First In, First Out
    TTL = "ttl"           # Time To Live based
    PRIORITY = "priority"  # Priority-based eviction
    HYBRID = "hybrid"     # Combination of multiple policies


@dataclass
class CacheNamespace:
    """Cache namespace domain entity.
    
    Provides logical grouping of cache entries with bulk operations,
    isolation, and namespace-level policies.
    
    Namespaces enable:
    - Logical grouping and organization
    - Bulk operations (flush, invalidate)
    - Isolation between different data types
    - Namespace-specific policies and limits
    - Multi-tenancy support
    - Performance optimization
    """
    
    # Core identity
    name: str
    description: str
    
    # Namespace policies
    default_ttl: Optional[CacheTTL]
    max_entries: int
    eviction_policy: EvictionPolicy
    
    # Resource limits
    max_memory_mb: Optional[int] = None
    max_key_length: int = 250
    
    # Multi-tenancy support
    tenant_id: Optional[str] = None
    
    # Metadata
    created_at: Optional[str] = None
    tags: Optional[list[str]] = None
    
    def __post_init__(self):
        """Validate namespace configuration."""
        if not self.name:
            raise ValueError("Namespace name cannot be empty")
        
        if self.max_entries <= 0:
            raise ValueError("max_entries must be positive")
        
        if self.max_key_length <= 0:
            raise ValueError("max_key_length must be positive")
        
        if self.max_memory_mb is not None and self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive if specified")
    
    def is_tenant_isolated(self) -> bool:
        """Check if namespace is tenant-specific."""
        return self.tenant_id is not None
    
    def get_full_key(self, cache_key: str) -> str:
        """Generate full cache key with namespace prefix."""
        if self.tenant_id:
            return f"{self.tenant_id}:{self.name}:{cache_key}"
        return f"{self.name}:{cache_key}"
    
    def matches_tenant(self, tenant_id: Optional[str]) -> bool:
        """Check if namespace belongs to specified tenant."""
        return self.tenant_id == tenant_id
    
    def has_tag(self, tag: str) -> bool:
        """Check if namespace has specific tag."""
        return self.tags is not None and tag in self.tags
    
    def __eq__(self, other) -> bool:
        """Compare namespaces by name and tenant."""
        if not isinstance(other, CacheNamespace):
            return False
        return self.name == other.name and self.tenant_id == other.tenant_id
    
    def __hash__(self) -> int:
        """Hash namespace by name and tenant."""
        return hash((self.name, self.tenant_id))
    
    def __str__(self) -> str:
        """String representation of namespace."""
        if self.tenant_id:
            return f"{self.tenant_id}:{self.name}"
        return self.name