"""Check cache exists query.

ONLY existence checking - handles cache key existence validation
with performance monitoring.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.value_objects.cache_key import CacheKey
from ...core.exceptions.cache_key_invalid import CacheKeyInvalid


@dataclass
class CheckCacheExistsData:
    """Data required to check cache entry existence."""
    
    key: str
    namespace: str = "default"
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class CheckCacheExistsResult:
    """Result of cache existence check."""
    
    exists: bool
    key: str
    namespace: str
    ttl_remaining_seconds: Optional[int] = None
    check_time_ms: float = 0.0
    error_message: Optional[str] = None


class CheckCacheExistsQuery:
    """Query to check cache entry existence.
    
    Handles cache existence checking with:
    - Key validation and namespace resolution
    - Repository existence check with timeout handling
    - TTL information retrieval
    - Performance measurement
    - Error handling and graceful degradation
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize check cache exists query.
        
        Args:
            repository: Cache repository for existence checking
        """
        self._repository = repository
    
    async def execute(self, data: CheckCacheExistsData) -> CheckCacheExistsResult:
        """Execute cache existence check operation.
        
        Args:
            data: Cache existence check data
            
        Returns:
            Result indicating if key exists and TTL information
            
        Raises:
            CacheKeyInvalid: If cache key is invalid
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate and create cache key
            cache_key = self._create_cache_key(data.key)
            
            # Create cache namespace
            namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Check existence in repository
            exists = await self._repository.exists(cache_key, namespace)
            
            # Get TTL if exists
            ttl_remaining = None
            if exists:
                ttl_remaining = await self._repository.get_ttl(cache_key, namespace)
            
            # Calculate check time
            check_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return CheckCacheExistsResult(
                exists=exists,
                key=data.key,
                namespace=data.namespace,
                ttl_remaining_seconds=ttl_remaining,
                check_time_ms=check_time_ms
            )
                
        except CacheKeyInvalid as e:
            check_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return CheckCacheExistsResult(
                exists=False,
                key=data.key,
                namespace=data.namespace,
                check_time_ms=check_time_ms,
                error_message=f"Invalid cache key: {e.reason}"
            )
        
        except Exception as e:
            check_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return CheckCacheExistsResult(
                exists=False,
                key=data.key,
                namespace=data.namespace,
                check_time_ms=check_time_ms,
                error_message=f"Check failed: {str(e)}"
            )
    
    def _create_cache_key(self, key: str) -> CacheKey:
        """Create and validate cache key."""
        return CacheKey(key)
    
    def _create_namespace(self, name: str, tenant_id: Optional[str] = None) -> CacheNamespace:
        """Create cache namespace."""
        return CacheNamespace(
            name=name,
            description=f"Cache namespace: {name}",
            default_ttl=None,
            max_entries=10000,  # TODO: Get from config
            eviction_policy=EvictionPolicy.LRU,
            tenant_id=tenant_id
        )


# Factory function for dependency injection
def create_check_cache_exists_query(repository: CacheRepository) -> CheckCacheExistsQuery:
    """Create check cache exists query."""
    return CheckCacheExistsQuery(repository=repository)