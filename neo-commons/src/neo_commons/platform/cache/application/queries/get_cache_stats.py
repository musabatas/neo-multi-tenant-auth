"""Get cache stats query.

ONLY statistics retrieval - handles cache performance metrics
and operational statistics.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy


@dataclass
class GetCacheStatsData:
    """Data required to get cache statistics."""
    
    namespace: Optional[str] = None  # None = global stats
    include_detailed: bool = False
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class GetCacheStatsResult:
    """Result of cache statistics query."""
    
    success: bool
    namespace: Optional[str]
    stats: Dict[str, Any]
    timestamp: str
    error_message: Optional[str] = None


class GetCacheStatsQuery:
    """Query to get cache statistics and metrics.
    
    Handles cache statistics retrieval with:
    - Global and namespace-specific statistics
    - Performance metrics (hit rate, response times)
    - Operational metrics (memory usage, entry counts)
    - Detailed breakdowns when requested
    - Error handling for unavailable metrics
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize get cache stats query.
        
        Args:
            repository: Cache repository for statistics
        """
        self._repository = repository
    
    async def execute(self, data: GetCacheStatsData) -> GetCacheStatsResult:
        """Execute cache statistics query.
        
        Args:
            data: Cache statistics query data
            
        Returns:
            Result with cache statistics and metrics
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            if data.namespace:
                # Namespace-specific statistics
                stats = await self._get_namespace_stats(data)
            else:
                # Global statistics
                stats = await self._get_global_stats(data)
            
            return GetCacheStatsResult(
                success=True,
                namespace=data.namespace,
                stats=stats,
                timestamp=timestamp
            )
                
        except Exception as e:
            return GetCacheStatsResult(
                success=False,
                namespace=data.namespace,
                stats={},
                timestamp=datetime.utcnow().isoformat(),
                error_message=f"Failed to get statistics: {str(e)}"
            )
    
    async def _get_global_stats(self, data: GetCacheStatsData) -> Dict[str, Any]:
        """Get global cache statistics."""
        # Get repository statistics
        repo_stats = await self._repository.get_stats()
        
        # Get repository info
        repo_info = await self._repository.get_info()
        
        # Combine statistics
        stats = {
            **repo_stats,
            **repo_info,
            "query_timestamp": datetime.utcnow().isoformat(),
            "scope": "global"
        }
        
        # Add calculated metrics
        if data.include_detailed:
            stats.update(self._calculate_detailed_metrics(repo_stats))
        
        return stats
    
    async def _get_namespace_stats(self, data: GetCacheStatsData) -> Dict[str, Any]:
        """Get namespace-specific statistics."""
        # Create namespace
        namespace = self._create_namespace(data.namespace, data.tenant_id)
        
        try:
            # Get namespace-specific metrics
            entry_count = await self._repository.get_namespace_size(namespace)
            memory_usage = await self._repository.get_namespace_memory(namespace)
            
            stats = {
                "namespace": data.namespace,
                "tenant_id": data.tenant_id,
                "entry_count": entry_count,
                "memory_usage_bytes": memory_usage,
                "memory_usage_mb": round(memory_usage / (1024 * 1024), 2) if memory_usage else 0,
                "query_timestamp": datetime.utcnow().isoformat(),
                "scope": "namespace"
            }
            
            if data.include_detailed:
                # Add global stats for context
                global_stats = await self._repository.get_stats()
                stats["global_context"] = global_stats
            
            return stats
            
        except Exception as e:
            # Return basic stats if detailed stats fail
            return {
                "namespace": data.namespace,
                "tenant_id": data.tenant_id,
                "error": f"Detailed namespace stats unavailable: {str(e)}",
                "query_timestamp": datetime.utcnow().isoformat(),
                "scope": "namespace"
            }
    
    def _calculate_detailed_metrics(self, repo_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional detailed metrics."""
        detailed = {}
        
        try:
            # Cache effectiveness metrics
            total_requests = repo_stats.get("get_count", 0)
            hit_count = repo_stats.get("hit_count", 0)
            miss_count = repo_stats.get("miss_count", 0)
            
            if total_requests > 0:
                detailed["cache_effectiveness"] = {
                    "hit_rate_percentage": round((hit_count / total_requests) * 100, 2),
                    "miss_rate_percentage": round((miss_count / total_requests) * 100, 2),
                    "total_requests": total_requests
                }
            
            # Performance metrics
            avg_get_time = repo_stats.get("average_get_time_ms", 0)
            avg_set_time = repo_stats.get("average_set_time_ms", 0)
            
            detailed["performance_metrics"] = {
                "average_get_time_ms": avg_get_time,
                "average_set_time_ms": avg_set_time,
                "performance_category": self._get_performance_category(avg_get_time)
            }
            
            # Operational health
            error_count = repo_stats.get("error_count", 0)
            error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
            
            detailed["operational_health"] = {
                "error_count": error_count,
                "error_rate_percentage": round(error_rate, 2),
                "health_status": self._get_health_status(error_rate)
            }
            
        except Exception:
            detailed["calculation_error"] = "Some detailed metrics could not be calculated"
        
        return detailed
    
    def _get_performance_category(self, avg_get_time_ms: float) -> str:
        """Categorize performance based on average get time."""
        if avg_get_time_ms <= 1.0:
            return "excellent"
        elif avg_get_time_ms <= 5.0:
            return "good"
        elif avg_get_time_ms <= 10.0:
            return "acceptable"
        else:
            return "needs_optimization"
    
    def _get_health_status(self, error_rate: float) -> str:
        """Determine health status based on error rate."""
        if error_rate <= 0.1:
            return "healthy"
        elif error_rate <= 1.0:
            return "warning"
        else:
            return "critical"
    
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
def create_get_cache_stats_query(repository: CacheRepository) -> GetCacheStatsQuery:
    """Create get cache stats query."""
    return GetCacheStatsQuery(repository=repository)