"""Cache feature for neo-commons.

Feature-First architecture with Redis and in-memory cache support:
- entities/: Cache domain objects, protocols, and configuration
- services/: Cache business logic and orchestration  
- adapters/: Redis and in-memory cache implementations
"""

# Core cache protocols and configuration
from .entities.protocols import Cache, CacheBackend
from .entities.config import CacheSettings, CacheInstanceConfig

# Cache service orchestration
from .services.cache_service import CacheService

# Cache adapters (Redis and Memory only)
from .adapters.redis_adapter import RedisAdapter
from .adapters.memory_adapter import MemoryAdapter

# Tenant cache - moved to tenants feature

__all__ = [
    # Core protocols
    "Cache",
    "CacheBackend",
    
    # Configuration
    "CacheSettings",
    "CacheInstanceConfig",
    
    # Services
    "CacheService",
    
    # Adapters
    "RedisAdapter",
    "MemoryAdapter",
    
    # Tenant cache - moved to tenants feature
]