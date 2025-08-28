"""List cache keys query.

ONLY key listing - handles cache key discovery and listing
with pattern support and pagination.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.value_objects.invalidation_pattern import InvalidationPattern, PatternType


@dataclass
class ListCacheKeysData:
    """Data required to list cache keys."""
    
    namespace: Optional[str] = None  # None = all namespaces
    pattern: Optional[str] = None    # Optional pattern filter
    pattern_type: str = "wildcard"   # wildcard, regex, prefix, suffix, exact
    case_sensitive: bool = True
    
    # Pagination
    limit: int = 100
    offset: int = 0
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class ListCacheKeysResult:
    """Result of cache keys listing."""
    
    success: bool
    namespace: Optional[str]
    keys: List[str]
    total_found: int
    has_more: bool
    pattern: Optional[str] = None
    query_time_ms: float = 0.0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.keys is None:
            self.keys = []


class ListCacheKeysQuery:
    """Query to list cache keys with filtering.
    
    Handles cache key listing with:
    - Optional namespace filtering
    - Pattern-based key filtering (wildcard, regex, prefix, suffix)
    - Pagination support for large key sets
    - Performance monitoring and timing
    - Error handling for invalid patterns or repository issues
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize list cache keys query.
        
        Args:
            repository: Cache repository for key discovery
        """
        self._repository = repository
    
    async def execute(self, data: ListCacheKeysData) -> ListCacheKeysResult:
        """Execute cache keys listing operation.
        
        Args:
            data: Cache keys listing data and filters
            
        Returns:
            Result with filtered cache keys and pagination info
        """
        start_time = datetime.utcnow()
        
        try:
            # Create namespace if specified
            namespace = None
            if data.namespace:
                namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Create pattern if specified
            pattern = None
            if data.pattern:
                pattern = self._create_pattern(data)
            
            # Get keys from repository
            if pattern:
                # Use pattern-based key discovery
                all_keys = await self._repository.find_keys(pattern, namespace)
            else:
                # Get all keys in namespace (this would need to be implemented in repository)
                # For now, return empty list if no pattern specified
                all_keys = []
            
            # Apply pagination
            total_found = len(all_keys)
            start_idx = data.offset
            end_idx = data.offset + data.limit
            
            paginated_keys = [str(key) for key in all_keys[start_idx:end_idx]]
            has_more = end_idx < total_found
            
            # Calculate query time
            query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ListCacheKeysResult(
                success=True,
                namespace=data.namespace,
                keys=paginated_keys,
                total_found=total_found,
                has_more=has_more,
                pattern=data.pattern,
                query_time_ms=query_time_ms
            )
                
        except ValueError as e:
            query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ListCacheKeysResult(
                success=False,
                namespace=data.namespace,
                keys=[],
                total_found=0,
                has_more=False,
                pattern=data.pattern,
                query_time_ms=query_time_ms,
                error_message=f"Invalid pattern: {str(e)}"
            )
        
        except Exception as e:
            query_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ListCacheKeysResult(
                success=False,
                namespace=data.namespace,
                keys=[],
                total_found=0,
                has_more=False,
                pattern=data.pattern,
                query_time_ms=query_time_ms,
                error_message=f"Query failed: {str(e)}"
            )
    
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
    
    def _create_pattern(self, data: ListCacheKeysData) -> InvalidationPattern:
        """Create pattern for key filtering."""
        pattern_type_map = {
            "exact": PatternType.EXACT,
            "wildcard": PatternType.WILDCARD,
            "regex": PatternType.REGEX,
            "prefix": PatternType.PREFIX,
            "suffix": PatternType.SUFFIX
        }
        
        pattern_type = pattern_type_map.get(data.pattern_type.lower(), PatternType.WILDCARD)
        
        return InvalidationPattern(
            pattern=data.pattern,
            pattern_type=pattern_type,
            case_sensitive=data.case_sensitive
        )


# Factory function for dependency injection
def create_list_cache_keys_query(repository: CacheRepository) -> ListCacheKeysQuery:
    """Create list cache keys query."""
    return ListCacheKeysQuery(repository=repository)