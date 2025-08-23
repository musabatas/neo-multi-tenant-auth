"""
Enhanced User Identity Mapper for Neo-Commons

Provides sophisticated user identity mapping and transformation capabilities
with support for multiple authentication providers, bulk operations,
and advanced caching strategies.
"""
from typing import Dict, Any, Optional, List, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from datetime import datetime, timedelta
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    ExternalServiceError,
    UserNotFoundError,
    ValidationError,
)
# from .protocols import UserIdentityMapperProtocol  # Avoiding circular import


class MappingStatus(Enum):
    """Status of user identity mapping operations."""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    CACHE_HIT = "cache_hit"
    PARTIAL = "partial"
    FAILED = "failed"


class MappingStrategy(Enum):
    """Strategy for handling identity mapping conflicts."""
    PREFER_PLATFORM = "prefer_platform"  # Prefer platform user ID when multiple matches
    PREFER_EXTERNAL = "prefer_external"  # Prefer external user ID
    STRICT = "strict"  # Fail on conflicts
    MERGE = "merge"  # Attempt to merge user contexts


@dataclass
class MappingResult:
    """Result of an identity mapping operation."""
    user_id: str
    platform_user_id: Optional[str] = None
    external_user_id: Optional[str] = None
    provider: Optional[str] = None
    status: MappingStatus = MappingStatus.SUCCESS
    metadata: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    processing_time_ms: float = 0.0


@dataclass
class BulkMappingResult:
    """Result of bulk identity mapping operations."""
    total_requested: int
    successful_mappings: List[MappingResult] = field(default_factory=list)
    failed_mappings: List[MappingResult] = field(default_factory=list)
    cache_hits: int = 0
    processing_time_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_requested == 0:
            return 0.0
        return (len(self.successful_mappings) / self.total_requested) * 100


class DefaultUserIdentityMapper:
    """
    Enhanced user identity mapper with advanced caching and bulk operations.
    
    This implementation provides sophisticated user identity mapping capabilities
    including bulk operations, multiple provider support, conflict resolution,
    and intelligent caching strategies.
    
    Features:
    - Bulk mapping operations with parallel processing
    - Multiple mapping strategies for conflict resolution
    - Intelligent caching with different TTL strategies
    - Performance metrics and monitoring
    - Support for mapping chains and transformations
    - Graceful degradation and error recovery
    """
    
    def __init__(
        self,
        user_resolver,  # DefaultUserIdentityResolver
        cache_service,  # TenantAwareCacheProtocol
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize enhanced user identity mapper.
        
        Args:
            user_resolver: User identity resolver for basic operations
            cache_service: Cache service for performance optimization
            config: Optional configuration
        """
        self.resolver = user_resolver
        self.cache = cache_service
        self.config = config
        
        # Configuration with defaults
        self.bulk_batch_size = 50
        self.max_concurrent_mappings = 10
        self.mapping_cache_ttl = 1800  # 30 minutes
        self.bulk_cache_ttl = 600  # 10 minutes
        self.performance_cache_ttl = 86400  # 24 hours
        
        # Load from config if available
        if config:
            self.bulk_batch_size = getattr(config, 'IDENTITY_BULK_BATCH_SIZE', 50)
            self.max_concurrent_mappings = getattr(config, 'IDENTITY_MAX_CONCURRENT', 10)
            self.mapping_cache_ttl = getattr(config, 'IDENTITY_MAPPING_CACHE_TTL', 1800)
        
        # Performance tracking
        self.performance_metrics = {
            'total_mappings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'failed_mappings': 0,
            'avg_response_time_ms': 0.0
        }
        
        logger.info(
            f"Initialized DefaultUserIdentityMapper with batch_size: {self.bulk_batch_size}, "
            f"max_concurrent: {self.max_concurrent_mappings}"
        )
    
    def _build_mapping_cache_key(self, user_id: str, provider: Optional[str] = None) -> str:
        """Build cache key for identity mapping."""
        if provider:
            return f"identity_mapping:{provider}:{user_id}"
        return f"identity_mapping:auto:{user_id}"
    
    def _build_bulk_cache_key(self, user_ids: List[str], provider: Optional[str] = None) -> str:
        """Build cache key for bulk mapping results."""
        user_ids_hash = hash(tuple(sorted(user_ids)))
        provider_part = f":{provider}" if provider else ":auto"
        return f"identity_bulk{provider_part}:{user_ids_hash}"
    
    async def map_user_identity(
        self,
        user_id: str,
        provider: Optional[str] = None,
        strategy: MappingStrategy = MappingStrategy.PREFER_PLATFORM,
        use_cache: bool = True
    ) -> MappingResult:
        """
        Map a single user identity with advanced options.
        
        Args:
            user_id: User ID to map
            provider: Optional provider hint
            strategy: Mapping strategy for conflict resolution
            use_cache: Whether to use caching
            
        Returns:
            MappingResult with mapping details and metadata
        """
        start_time = datetime.now()
        cache_key = self._build_mapping_cache_key(user_id, provider)
        
        try:
            # Check cache if enabled
            if use_cache:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    self.performance_metrics['cache_hits'] += 1
                    logger.debug(f"Cache hit for user mapping: {user_id}")
                    
                    result = MappingResult(**cached_result)
                    result.cached = True
                    result.status = MappingStatus.CACHE_HIT
                    return result
            
            self.performance_metrics['cache_misses'] += 1
            
            # Resolve user context
            context = await self.resolver.resolve_user_context(user_id, provider)
            
            # Build mapping result
            result = MappingResult(
                user_id=user_id,
                platform_user_id=context.get('platform_user_id'),
                external_user_id=context.get('external_user_id'),
                provider=context.get('provider'),
                status=MappingStatus.SUCCESS,
                metadata={
                    'is_mapped': context.get('is_mapped', False),
                    'user_metadata': context.get('user_metadata', {}),
                    'strategy_used': strategy.value,
                    'timestamp': datetime.utcnow().isoformat()
                },
                cached=False
            )
            
            # Apply mapping strategy if needed
            if strategy != MappingStrategy.PREFER_PLATFORM:
                result = await self._apply_mapping_strategy(result, strategy)
            
            # Cache successful result
            if use_cache and result.status == MappingStatus.SUCCESS:
                cache_data = {
                    'user_id': result.user_id,
                    'platform_user_id': result.platform_user_id,
                    'external_user_id': result.external_user_id,
                    'provider': result.provider,
                    'status': result.status.value,
                    'metadata': result.metadata
                }
                await self.cache.set(cache_key, cache_data, ttl=self.mapping_cache_ttl)
            
            self.performance_metrics['total_mappings'] += 1
            
        except UserNotFoundError:
            result = MappingResult(
                user_id=user_id,
                status=MappingStatus.NOT_FOUND,
                metadata={'error': 'User not found', 'strategy_used': strategy.value}
            )
            self.performance_metrics['failed_mappings'] += 1
            
        except Exception as e:
            logger.error(f"Failed to map user identity for {user_id}: {e}")
            result = MappingResult(
                user_id=user_id,
                status=MappingStatus.FAILED,
                metadata={'error': str(e), 'strategy_used': strategy.value}
            )
            self.performance_metrics['failed_mappings'] += 1
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        result.processing_time_ms = processing_time
        
        return result
    
    async def map_user_identities_bulk(
        self,
        user_ids: List[str],
        provider: Optional[str] = None,
        strategy: MappingStrategy = MappingStrategy.PREFER_PLATFORM,
        use_cache: bool = True,
        parallel: bool = True
    ) -> BulkMappingResult:
        """
        Map multiple user identities efficiently.
        
        Args:
            user_ids: List of user IDs to map
            provider: Optional provider hint for all IDs
            strategy: Mapping strategy for conflict resolution
            use_cache: Whether to use caching
            parallel: Whether to process mappings in parallel
            
        Returns:
            BulkMappingResult with detailed mapping results
        """
        start_time = datetime.now()
        total_requested = len(user_ids)
        
        if total_requested == 0:
            return BulkMappingResult(total_requested=0)
        
        # Check bulk cache first
        bulk_cache_key = self._build_bulk_cache_key(user_ids, provider)
        if use_cache:
            cached_bulk_result = await self.cache.get(bulk_cache_key)
            if cached_bulk_result:
                logger.debug(f"Bulk cache hit for {total_requested} user mappings")
                result = BulkMappingResult(**cached_bulk_result)
                result.cache_hits = total_requested
                return result
        
        logger.debug(f"Processing bulk mapping for {total_requested} users")
        
        successful_mappings = []
        failed_mappings = []
        cache_hits = 0
        
        if parallel and total_requested > 1:
            # Process in parallel with semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_mappings)
            
            async def map_with_semaphore(uid: str) -> MappingResult:
                async with semaphore:
                    return await self.map_user_identity(uid, provider, strategy, use_cache)
            
            # Process in batches
            tasks = []
            for i in range(0, total_requested, self.bulk_batch_size):
                batch = user_ids[i:i + self.bulk_batch_size]
                batch_tasks = [map_with_semaphore(uid) for uid in batch]
                tasks.extend(batch_tasks)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    # Handle exceptions from gather
                    failed_mappings.append(MappingResult(
                        user_id="unknown",
                        status=MappingStatus.FAILED,
                        metadata={'error': str(result)}
                    ))
                elif result.status == MappingStatus.SUCCESS or result.status == MappingStatus.CACHE_HIT:
                    successful_mappings.append(result)
                    if result.cached:
                        cache_hits += 1
                else:
                    failed_mappings.append(result)
        else:
            # Process sequentially
            for user_id in user_ids:
                try:
                    result = await self.map_user_identity(user_id, provider, strategy, use_cache)
                    if result.status == MappingStatus.SUCCESS or result.status == MappingStatus.CACHE_HIT:
                        successful_mappings.append(result)
                        if result.cached:
                            cache_hits += 1
                    else:
                        failed_mappings.append(result)
                except Exception as e:
                    failed_mappings.append(MappingResult(
                        user_id=user_id,
                        status=MappingStatus.FAILED,
                        metadata={'error': str(e)}
                    ))
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        bulk_result = BulkMappingResult(
            total_requested=total_requested,
            successful_mappings=successful_mappings,
            failed_mappings=failed_mappings,
            cache_hits=cache_hits,
            processing_time_ms=processing_time
        )
        
        # Cache bulk result if mostly successful
        if use_cache and bulk_result.success_rate >= 80.0:
            cache_data = {
                'total_requested': bulk_result.total_requested,
                'successful_mappings': [
                    {
                        'user_id': r.user_id,
                        'platform_user_id': r.platform_user_id,
                        'external_user_id': r.external_user_id,
                        'provider': r.provider,
                        'status': r.status.value,
                        'metadata': r.metadata
                    }
                    for r in bulk_result.successful_mappings
                ],
                'failed_mappings': [
                    {
                        'user_id': r.user_id,
                        'status': r.status.value,
                        'metadata': r.metadata
                    }
                    for r in bulk_result.failed_mappings
                ],
                'cache_hits': cache_hits,
                'processing_time_ms': processing_time
            }
            await self.cache.set(bulk_cache_key, cache_data, ttl=self.bulk_cache_ttl)
        
        logger.info(
            f"Bulk mapping completed: {len(successful_mappings)}/{total_requested} successful "
            f"({bulk_result.success_rate:.1f}%) in {processing_time:.1f}ms"
        )
        
        return bulk_result
    
    async def _apply_mapping_strategy(
        self,
        result: MappingResult,
        strategy: MappingStrategy
    ) -> MappingResult:
        """Apply mapping strategy for conflict resolution."""
        if strategy == MappingStrategy.PREFER_PLATFORM:
            # Default behavior - no changes needed
            return result
        
        elif strategy == MappingStrategy.PREFER_EXTERNAL:
            # Prefer external ID representation
            if result.external_user_id:
                result.user_id = result.external_user_id
                result.metadata['strategy_applied'] = 'prefer_external'
        
        elif strategy == MappingStrategy.STRICT:
            # Fail if there are mapping ambiguities
            if result.external_user_id and result.platform_user_id != result.user_id:
                result.status = MappingStatus.FAILED
                result.metadata['error'] = 'Strict mode: ambiguous user mapping'
        
        elif strategy == MappingStrategy.MERGE:
            # Attempt to merge user contexts (placeholder for future enhancement)
            result.metadata['strategy_applied'] = 'merge_attempted'
        
        return result
    
    async def invalidate_mapping_cache(
        self,
        user_id: str,
        provider: Optional[str] = None
    ) -> None:
        """
        Invalidate cached mapping for a user.
        
        Args:
            user_id: User ID to invalidate
            provider: Optional provider to limit scope
        """
        try:
            cache_key = self._build_mapping_cache_key(user_id, provider)
            await self.cache.delete(cache_key)
            
            # Also invalidate the underlying resolver cache
            await self.resolver.invalidate_user_mapping(user_id, provider)
            
            logger.debug(f"Invalidated mapping cache for user: {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to invalidate mapping cache for {user_id}: {e}")
    
    async def get_mapping_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for identity mapping operations.
        
        Returns:
            Dictionary with performance statistics
        """
        total_operations = self.performance_metrics['total_mappings']
        if total_operations > 0:
            cache_hit_rate = (self.performance_metrics['cache_hits'] / total_operations) * 100
            failure_rate = (self.performance_metrics['failed_mappings'] / total_operations) * 100
        else:
            cache_hit_rate = 0.0
            failure_rate = 0.0
        
        return {
            'total_mappings': total_operations,
            'cache_hits': self.performance_metrics['cache_hits'],
            'cache_misses': self.performance_metrics['cache_misses'],
            'failed_mappings': self.performance_metrics['failed_mappings'],
            'cache_hit_rate_percent': cache_hit_rate,
            'failure_rate_percent': failure_rate,
            'avg_response_time_ms': self.performance_metrics['avg_response_time_ms']
        }
    
    async def reset_performance_metrics(self) -> None:
        """Reset performance metrics counters."""
        self.performance_metrics = {
            'total_mappings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'failed_mappings': 0,
            'avg_response_time_ms': 0.0
        }
        logger.info("Reset identity mapping performance metrics")


# Factory function for dependency injection
def create_user_identity_mapper(
    user_resolver,
    cache_service,
    config: Optional[AuthConfigProtocol] = None
) -> DefaultUserIdentityMapper:
    """
    Create a user identity mapper instance.
    
    Args:
        user_resolver: User identity resolver
        cache_service: Cache service implementation
        config: Optional configuration
        
    Returns:
        Configured DefaultUserIdentityMapper instance
    """
    return DefaultUserIdentityMapper(
        user_resolver=user_resolver,
        cache_service=cache_service,
        config=config
    )


__all__ = [
    "DefaultUserIdentityMapper",
    "MappingResult",
    "BulkMappingResult",
    "MappingStatus",
    "MappingStrategy",
    "create_user_identity_mapper",
]