"""Warm cache command.

ONLY cache warming - handles proactive cache population
with intelligent warming strategies.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, List, Callable, Dict
from uuid import uuid4

from ...core.protocols.cache_repository import CacheRepository
from ...core.protocols.cache_serializer import CacheSerializer
from ...core.entities.cache_entry import CacheEntry
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.cache_ttl import CacheTTL
from ...core.value_objects.cache_priority import CachePriority
from ...core.value_objects.cache_size import CacheSize
from ...core.exceptions.cache_key_invalid import CacheKeyInvalid


@dataclass
class WarmCacheEntry:
    """Single entry for cache warming."""
    
    key: str
    value: Any
    ttl_seconds: Optional[int] = None
    priority: str = "medium"


@dataclass
class WarmCacheData:
    """Data required for cache warming operation."""
    
    # Single entry or multiple entries
    entry: Optional[WarmCacheEntry] = None
    entries: Optional[List[WarmCacheEntry]] = None
    
    # Or factory function for lazy loading
    key_factory: Optional[Callable[[], List[str]]] = None
    value_factory: Optional[Callable[[str], Any]] = None
    
    # Configuration
    namespace: str = "default"
    batch_size: int = 100
    replace_existing: bool = False
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class WarmCacheResult:
    """Result of cache warming operation."""
    
    success: bool
    namespace: str
    entries_warmed: int = 0
    entries_skipped: int = 0
    entries_failed: int = 0
    failed_keys: List[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.failed_keys is None:
            self.failed_keys = []


class WarmCacheCommand:
    """Command to warm cache with data.
    
    Handles proactive cache population with:
    - Single entry and batch warming support
    - Factory-based lazy loading for large datasets
    - Duplicate detection and replacement control
    - Batch processing with configurable size
    - Error handling for partial failures
    - Performance tracking and statistics
    """
    
    def __init__(
        self,
        repository: CacheRepository,
        serializer: Optional[CacheSerializer] = None
    ):
        """Initialize warm cache command.
        
        Args:
            repository: Cache repository for storage
            serializer: Optional serializer for size estimation
        """
        self._repository = repository
        self._serializer = serializer
    
    async def execute(self, data: WarmCacheData) -> WarmCacheResult:
        """Execute cache warming operation.
        
        Args:
            data: Cache warming data and configuration
            
        Returns:
            Result of the warming operation with statistics
        """
        try:
            # Create cache namespace
            namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Determine warming strategy and get entries
            entries_to_warm = await self._prepare_entries(data)
            
            if not entries_to_warm:
                return WarmCacheResult(
                    success=True,
                    namespace=data.namespace,
                    entries_warmed=0,
                    entries_skipped=0,
                    entries_failed=0
                )
            
            # Process entries in batches
            result = await self._process_batches(
                entries_to_warm, namespace, data
            )
            
            return result
                
        except Exception as e:
            return WarmCacheResult(
                success=False,
                namespace=data.namespace,
                entries_warmed=0,
                entries_skipped=0,
                entries_failed=0,
                error_message=f"Warming failed: {str(e)}"
            )
    
    async def _prepare_entries(self, data: WarmCacheData) -> List[WarmCacheEntry]:
        """Prepare entries for warming based on data source."""
        entries = []
        
        if data.entry:
            # Single entry
            entries = [data.entry]
        
        elif data.entries:
            # Multiple entries provided
            entries = data.entries
        
        elif data.key_factory and data.value_factory:
            # Factory-based generation
            keys = data.key_factory()
            for key in keys:
                try:
                    value = data.value_factory(key)
                    entries.append(WarmCacheEntry(key=key, value=value))
                except Exception:
                    # Skip keys that fail to generate values
                    continue
        
        return entries
    
    async def _process_batches(
        self,
        entries: List[WarmCacheEntry],
        namespace: CacheNamespace,
        data: WarmCacheData
    ) -> WarmCacheResult:
        """Process entries in batches for warming."""
        total_entries = len(entries)
        entries_warmed = 0
        entries_skipped = 0
        entries_failed = 0
        failed_keys = []
        
        # Process in batches
        for i in range(0, total_entries, data.batch_size):
            batch = entries[i:i + data.batch_size]
            
            batch_result = await self._process_batch(
                batch, namespace, data
            )
            
            entries_warmed += batch_result["warmed"]
            entries_skipped += batch_result["skipped"]
            entries_failed += batch_result["failed"]
            failed_keys.extend(batch_result["failed_keys"])
        
        return WarmCacheResult(
            success=entries_failed == 0,
            namespace=data.namespace,
            entries_warmed=entries_warmed,
            entries_skipped=entries_skipped,
            entries_failed=entries_failed,
            failed_keys=failed_keys
        )
    
    async def _process_batch(
        self,
        batch: List[WarmCacheEntry],
        namespace: CacheNamespace,
        data: WarmCacheData
    ) -> Dict[str, Any]:
        """Process a single batch of entries."""
        warmed = 0
        skipped = 0
        failed = 0
        failed_keys = []
        
        for entry_data in batch:
            try:
                # Create cache key
                cache_key = CacheKey(entry_data.key)
                
                # Check if entry already exists
                if not data.replace_existing:
                    exists = await self._repository.exists(cache_key, namespace)
                    if exists:
                        skipped += 1
                        continue
                
                # Create cache entry
                cache_entry = await self._create_cache_entry(
                    entry_data, cache_key, namespace
                )
                
                # Store in repository
                success = await self._repository.set(cache_entry)
                
                if success:
                    warmed += 1
                else:
                    failed += 1
                    failed_keys.append(entry_data.key)
                    
            except Exception:
                failed += 1
                failed_keys.append(entry_data.key)
        
        return {
            "warmed": warmed,
            "skipped": skipped,
            "failed": failed,
            "failed_keys": failed_keys
        }
    
    async def _create_cache_entry(
        self,
        entry_data: WarmCacheEntry,
        cache_key: CacheKey,
        namespace: CacheNamespace
    ) -> CacheEntry:
        """Create cache entry from warming data."""
        # Create TTL if specified
        ttl = CacheTTL(entry_data.ttl_seconds) if entry_data.ttl_seconds else None
        
        # Create priority
        priority = self._create_priority(entry_data.priority)
        
        # Estimate size
        size = self._estimate_size(entry_data.value)
        
        return CacheEntry(
            key=cache_key,
            value=entry_data.value,
            ttl=ttl,
            priority=priority,
            namespace=namespace,
            created_at=datetime.utcnow(),
            accessed_at=datetime.utcnow(),
            access_count=0,
            size_bytes=size
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
    
    def _create_priority(self, priority_str: str) -> CachePriority:
        """Create cache priority from string."""
        priority_map = {
            "low": CachePriority.low(),
            "medium": CachePriority.medium(),
            "high": CachePriority.high(),
            "critical": CachePriority.critical()
        }
        
        return priority_map.get(priority_str.lower(), CachePriority.medium())
    
    def _estimate_size(self, value: Any) -> CacheSize:
        """Estimate value size."""
        if self._serializer:
            estimated = self._serializer.estimate_serialized_size(value)
            return CacheSize(estimated)
        else:
            # Basic estimation using string representation
            return CacheSize.estimate_json_size(str(value))


# Factory function for dependency injection
def create_warm_cache_command(
    repository: CacheRepository,
    serializer: Optional[CacheSerializer] = None
) -> WarmCacheCommand:
    """Create warm cache command."""
    return WarmCacheCommand(repository=repository, serializer=serializer)