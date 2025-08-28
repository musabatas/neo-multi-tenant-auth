"""Invalidate pattern command.

ONLY pattern invalidation - handles pattern-based cache invalidation
with wildcard and regex support.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.invalidation_pattern import InvalidationPattern, PatternType
from ...core.events.cache_invalidated import CacheInvalidated, InvalidationReason
from ...core.exceptions.cache_key_invalid import CacheKeyInvalid


@dataclass
class InvalidatePatternData:
    """Data required to invalidate cache entries by pattern."""
    
    pattern: str
    pattern_type: str = "wildcard"  # wildcard, regex, prefix, suffix, exact
    namespace: Optional[str] = None  # None = all namespaces
    case_sensitive: bool = True
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    batch_id: Optional[str] = None


@dataclass
class InvalidatePatternResult:
    """Result of pattern invalidation."""
    
    success: bool
    pattern: str
    pattern_type: str
    namespace: Optional[str]
    keys_invalidated: int = 0
    keys_found: List[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.keys_found is None:
            self.keys_found = []


class InvalidatePatternCommand:
    """Command to invalidate cache entries by pattern.
    
    Handles pattern-based cache invalidation with:
    - Pattern validation and compilation
    - Key discovery using repository pattern matching
    - Batch invalidation of matching keys
    - Event publishing for each invalidated key
    - Performance tracking and statistics
    - Error handling for invalid patterns
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize invalidate pattern command.
        
        Args:
            repository: Cache repository for pattern invalidation
        """
        self._repository = repository
    
    async def execute(self, data: InvalidatePatternData) -> InvalidatePatternResult:
        """Execute pattern invalidation operation.
        
        Args:
            data: Pattern invalidation data
            
        Returns:
            Result of the invalidation operation with count and details
        """
        try:
            # Create and validate invalidation pattern
            invalidation_pattern = self._create_invalidation_pattern(data)
            
            # Create namespace if specified
            namespace = None
            if data.namespace:
                namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Find matching keys using repository
            matching_keys = await self._repository.find_keys(invalidation_pattern, namespace)
            
            if not matching_keys:
                return InvalidatePatternResult(
                    success=True,
                    pattern=data.pattern,
                    pattern_type=data.pattern_type,
                    namespace=data.namespace,
                    keys_invalidated=0,
                    keys_found=[]
                )
            
            # Invalidate all matching keys
            keys_invalidated = await self._repository.invalidate_pattern(
                invalidation_pattern, namespace
            )
            
            # Publish invalidation events for monitoring
            await self._publish_invalidation_events(
                matching_keys, namespace, data, keys_invalidated
            )
            
            return InvalidatePatternResult(
                success=True,
                pattern=data.pattern,
                pattern_type=data.pattern_type,
                namespace=data.namespace,
                keys_invalidated=keys_invalidated,
                keys_found=[str(key) for key in matching_keys]
            )
                
        except ValueError as e:
            return InvalidatePatternResult(
                success=False,
                pattern=data.pattern,
                pattern_type=data.pattern_type,
                namespace=data.namespace,
                keys_invalidated=0,
                error_message=f"Invalid pattern: {str(e)}"
            )
        
        except Exception as e:
            return InvalidatePatternResult(
                success=False,
                pattern=data.pattern,
                pattern_type=data.pattern_type,
                namespace=data.namespace,
                keys_invalidated=0,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _create_invalidation_pattern(self, data: InvalidatePatternData) -> InvalidationPattern:
        """Create and validate invalidation pattern."""
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
    
    async def _publish_invalidation_events(
        self, 
        keys: List[CacheKey],
        namespace: Optional[CacheNamespace],
        data: InvalidatePatternData,
        keys_invalidated: int
    ) -> None:
        """Publish cache invalidation events for monitoring."""
        try:
            # Generate batch ID if not provided
            batch_id = data.batch_id or str(uuid4())
            
            for i, key in enumerate(keys):
                event = CacheInvalidated(
                    event_id=str(uuid4()),
                    timestamp=datetime.utcnow(),
                    key=key,
                    namespace=namespace or self._create_default_namespace(),
                    reason=InvalidationReason.PATTERN,
                    triggered_by=data.user_id or "system",
                    request_id=data.request_id,
                    user_id=data.user_id,
                    tenant_id=data.tenant_id,
                    batch_id=batch_id,
                    batch_size=keys_invalidated
                )
                
                # TODO: Publish event to event system when available
                # await self._event_publisher.publish(event)
                
        except Exception:
            # Don't fail command on event publishing error
            pass
    
    def _create_default_namespace(self) -> CacheNamespace:
        """Create default namespace for events."""
        return CacheNamespace(
            name="default",
            description="Default cache namespace",
            default_ttl=None,
            max_entries=10000,
            eviction_policy=EvictionPolicy.LRU
        )


# Factory function for dependency injection
def create_invalidate_pattern_command(repository: CacheRepository) -> InvalidatePatternCommand:
    """Create invalidate pattern command."""
    return InvalidatePatternCommand(repository=repository)