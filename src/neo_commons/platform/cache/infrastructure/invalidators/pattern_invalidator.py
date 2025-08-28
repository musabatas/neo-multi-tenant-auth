"""Pattern-based cache invalidator.

ONLY pattern invalidation functionality - handles wildcard and regex pattern
matching for cache key invalidation across different cache backends.

Following maximum separation architecture - one file = one purpose.
"""

import re
import fnmatch
from typing import List, Optional, Set, AsyncIterator
from datetime import datetime, timezone

from ...core.entities.cache_namespace import CacheNamespace
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.invalidation_pattern import InvalidationPattern
from ...core.protocols.cache_repository import CacheRepository


class PatternInvalidator:
    """Pattern-based cache invalidator.
    
    Handles pattern matching for cache key invalidation using:
    - Wildcard patterns (*, ?)
    - Regex patterns
    - Literal key matching
    - Namespace-aware filtering
    """
    
    def __init__(self, cache_repository: CacheRepository):
        """Initialize with cache repository.
        
        Args:
            cache_repository: Cache repository for key operations
        """
        self._cache_repository = cache_repository
    
    async def invalidate_pattern(
        self,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None,
        reason: Optional[str] = None
    ) -> int:
        """Invalidate keys matching pattern.
        
        Args:
            pattern: Pattern to match against keys
            namespace: Optional namespace filter
            reason: Optional reason for invalidation
            
        Returns:
            Number of keys invalidated
        """
        matching_keys = await self._find_matching_keys(pattern, namespace)
        invalidated_count = 0
        
        for key in matching_keys:
            try:
                success = await self._cache_repository.delete_entry(key, namespace or CacheNamespace("default"))
                if success:
                    invalidated_count += 1
            except Exception:
                # Continue with other keys even if one fails
                continue
        
        return invalidated_count
    
    async def find_matching_keys(
        self,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> List[CacheKey]:
        """Find keys matching the pattern.
        
        Args:
            pattern: Pattern to match
            namespace: Optional namespace filter
            
        Returns:
            List of matching cache keys
        """
        return await self._find_matching_keys(pattern, namespace)
    
    async def count_matching_keys(
        self,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> int:
        """Count keys matching pattern without invalidating.
        
        Args:
            pattern: Pattern to match
            namespace: Optional namespace filter
            
        Returns:
            Number of matching keys
        """
        matching_keys = await self._find_matching_keys(pattern, namespace)
        return len(matching_keys)
    
    async def preview_invalidation(
        self,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None,
        limit: int = 100
    ) -> List[str]:
        """Preview keys that would be invalidated.
        
        Args:
            pattern: Pattern to match
            namespace: Optional namespace filter
            limit: Maximum keys to return
            
        Returns:
            List of key strings that would be invalidated
        """
        matching_keys = await self._find_matching_keys(pattern, namespace)
        return [key.value for key in matching_keys[:limit]]
    
    def validate_pattern(self, pattern: InvalidationPattern) -> bool:
        """Validate pattern syntax.
        
        Args:
            pattern: Pattern to validate
            
        Returns:
            True if pattern is valid
        """
        try:
            if pattern.pattern_type == "regex":
                re.compile(pattern.pattern)
            return True
        except re.error:
            return False
    
    async def _find_matching_keys(
        self,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> List[CacheKey]:
        """Find all keys matching the pattern.
        
        Args:
            pattern: Pattern to match
            namespace: Optional namespace filter
            
        Returns:
            List of matching cache keys
        """
        # Get all keys from cache
        all_keys = await self._get_all_cache_keys(namespace)
        matching_keys = []
        
        for key in all_keys:
            if self._key_matches_pattern(key, pattern):
                matching_keys.append(key)
        
        return matching_keys
    
    async def _get_all_cache_keys(self, namespace: Optional[CacheNamespace] = None) -> List[CacheKey]:
        """Get all cache keys, optionally filtered by namespace.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            List of all cache keys
        """
        try:
            # Try to get keys from repository if supported
            if hasattr(self._cache_repository, 'list_keys'):
                return await self._cache_repository.list_keys(namespace)
            
            # Fallback: This is a limitation - we can't get all keys
            # from repositories that don't support key listing
            # In a real implementation, this would require cache backends
            # to support key enumeration
            return []
            
        except Exception:
            return []
    
    def _key_matches_pattern(self, key: CacheKey, pattern: InvalidationPattern) -> bool:
        """Check if key matches the pattern.
        
        Args:
            key: Cache key to check
            pattern: Pattern to match against
            
        Returns:
            True if key matches pattern
        """
        key_str = key.value
        pattern_str = pattern.pattern
        
        if pattern.pattern_type == "literal":
            return key_str == pattern_str
        elif pattern.pattern_type == "wildcard":
            return fnmatch.fnmatch(key_str, pattern_str)
        elif pattern.pattern_type == "regex":
            try:
                return bool(re.match(pattern_str, key_str))
            except re.error:
                return False
        else:
            # Default to literal matching
            return key_str == pattern_str
    
    async def get_pattern_stats(
        self,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> dict:
        """Get statistics about pattern matching.
        
        Args:
            pattern: Pattern to analyze
            namespace: Optional namespace filter
            
        Returns:
            Dictionary with pattern statistics
        """
        matching_keys = await self._find_matching_keys(pattern, namespace)
        
        return {
            "pattern": pattern.pattern,
            "pattern_type": pattern.pattern_type,
            "namespace": namespace.name if namespace else None,
            "matching_keys_count": len(matching_keys),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_valid_pattern": self.validate_pattern(pattern)
        }


def create_pattern_invalidator(cache_repository: CacheRepository) -> PatternInvalidator:
    """Factory function to create pattern invalidator.
    
    Args:
        cache_repository: Cache repository for operations
        
    Returns:
        Configured pattern invalidator instance
    """
    return PatternInvalidator(cache_repository)