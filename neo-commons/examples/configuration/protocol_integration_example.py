"""Real-world integration example showing protocol factory with neo-commons features.

This demonstrates how to use the protocol factory to enhance existing
neo-commons features with runtime protocol adaptation.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from typing import Optional, Dict, Any
from neo_commons.infrastructure.protocols.factory import (
    RuntimeProtocolFactory, ProtocolImplementation, AdaptationStrategy,
    protocol_implementation, register_implementation
)
from neo_commons.infrastructure.protocols.infrastructure import CacheProtocol
from neo_commons.features.cache.entities.protocols import Cache
from neo_commons.features.cache.entities.config import CacheBackendConfig, CacheBackend
from neo_commons.features.cache.adapters.memory_adapter import MemoryAdapter


class EnhancedCacheService:
    """Cache service enhanced with protocol factory for runtime adaptation."""
    
    def __init__(self, protocol_factory: Optional[RuntimeProtocolFactory] = None):
        self.factory = protocol_factory or RuntimeProtocolFactory()
        self._setup_implementations()
    
    def _setup_implementations(self):
        """Setup cache implementations with runtime conditions."""
        
        # Create cache backend configurations
        memory_config = CacheBackendConfig(
            name="memory_fallback",
            backend_type=CacheBackend.MEMORY,
            max_memory_mb=100,
            eviction_policy="lru"
        )
        
        # Memory cache fallback
        self.factory.register(CacheProtocol, ProtocolImplementation(
            name="memory_fallback",
            implementation_class=MemoryAdapter,
            priority=5,
            condition=lambda: True,  # Always available
            dependencies={
                "config": memory_config,
                "max_size": 1000
            },
            singleton=True,
            description="In-memory cache fallback"
        ))
        
        # High-performance memory cache for development
        high_perf_config = CacheBackendConfig(
            name="memory_high_perf",
            backend_type=CacheBackend.MEMORY,
            max_memory_mb=200,
            eviction_policy="lru"
        )
        
        self.factory.register(CacheProtocol, ProtocolImplementation(
            name="memory_high_performance",
            implementation_class=MemoryAdapter,
            priority=10,
            condition=lambda: os.getenv("CACHE_TYPE", "memory").lower() == "memory",
            dependencies={
                "config": high_perf_config,
                "max_size": 2000
            },
            singleton=True,
            description="High-performance memory cache with metrics"
        ))
    
    async def get_cache(self, cache_type: Optional[str] = None) -> CacheProtocol:
        """Get cache implementation based on runtime conditions."""
        if cache_type:
            # Get specific named implementation
            return self.factory.create_named(CacheProtocol, cache_type)
        else:
            # Use adaptive selection based on environment
            return self.factory.create(CacheProtocol)
    
    async def get_distributed_cache(self) -> CacheProtocol:
        """Get distributed cache suitable for multi-instance deployments."""
        # Try to get high-performance cache first, fallback to memory with warning
        try:
            return self.factory.create_named(CacheProtocol, "memory_high_performance")
        except ValueError:
            print("WARNING: Using basic memory cache for distributed operations")
            return self.factory.create_named(CacheProtocol, "memory_fallback")
    
    async def get_local_cache(self) -> CacheProtocol:
        """Get local cache for single-instance operations."""
        return self.factory.create_named(CacheProtocol, "memory_fallback")
    
    def get_available_cache_types(self) -> list[str]:
        """Get list of available cache implementations."""
        return self.factory.get_available_implementations(CacheProtocol)


class DatabaseServiceWithProtocolFactory:
    """Database service enhanced with protocol factory for connection management."""
    
    def __init__(self):
        self.factory = RuntimeProtocolFactory()
        self._setup_connection_strategies()
    
    def _setup_connection_strategies(self):
        """Setup different database connection strategies."""
        
        # Production: Primary + read replicas
        # Development: Single connection
        # Testing: In-memory/mock
        pass  # Implementation would register different connection protocols


async def demonstrate_cache_adaptation():
    """Demonstrate cache adaptation based on environment."""
    print("🔧 Cache Service with Protocol Factory")
    print("=" * 50)
    
    cache_service = EnhancedCacheService()
    
    # Show available implementations
    available = cache_service.get_available_cache_types()
    print(f"Available cache types: {available}")
    
    # Get adaptive cache (selects based on environment/config)
    cache = await cache_service.get_cache()
    print(f"Selected cache: {cache.__class__.__name__}")
    
    # Initialize and use the cache
    await cache.connect()
    await cache.set("adaptive:test", b"works", ttl=60)
    value = await cache.get("adaptive:test")
    print(f"Cache test: {value}")
    await cache.disconnect()
    
    # Get distributed cache (prioritizes high-performance)
    dist_cache = await cache_service.get_distributed_cache()
    print(f"Distributed cache: {dist_cache.__class__.__name__}")
    
    # Get local cache (always memory fallback)
    local_cache = await cache_service.get_local_cache()
    print(f"Local cache: {local_cache.__class__.__name__}")


async def demonstrate_failover_scenario():
    """Demonstrate failover from Redis to memory cache."""
    print("\n🔄 Failover Scenario Demonstration")
    print("=" * 50)
    
    # Create factory with failover strategy
    factory = RuntimeProtocolFactory(strategy=AdaptationStrategy.FAILOVER)
    
    # Simulate Redis unavailable
    class UnavailableRedis:
        def __init__(self, **kwargs):
            raise ConnectionError("Redis connection failed")
    
    # Register failing Redis implementation
    factory.register(CacheProtocol, ProtocolImplementation(
        name="failing_redis",
        implementation_class=UnavailableRedis,
        priority=10
    ))
    
    # Create working memory fallback configuration
    backup_config = CacheBackendConfig(
        name="memory_backup",
        backend_type=CacheBackend.MEMORY,
        max_memory_mb=50,
        eviction_policy="lru"
    )
    
    # Register working memory fallback
    factory.register(CacheProtocol, ProtocolImplementation(
        name="memory_backup",
        implementation_class=MemoryAdapter,
        priority=5,
        dependencies={
            "config": backup_config,
            "max_size": 500
        }
    ))
    
    # Create cache with failover
    cache_service = EnhancedCacheService(protocol_factory=factory)
    
    # This should failover to memory cache
    cache = await cache_service.get_cache()
    print(f"Failover result: {cache.__class__.__name__}")
    
    # Initialize the adapter
    await cache.connect()
    
    await cache.set("failover:test", b"memory_backup_works", ttl=300)
    value = await cache.get("failover:test")
    print(f"Failover cache test: {value}")
    
    # Cleanup
    await cache.disconnect()


async def demonstrate_environment_specific_config():
    """Demonstrate environment-specific configuration selection."""
    print("\n🌍 Environment-Specific Configuration")
    print("=" * 50)
    
    environments = ["development", "staging", "production"]
    
    for env in environments:
        print(f"\n--- Environment: {env} ---")
        
        # Set environment
        os.environ["ENVIRONMENT"] = env
        os.environ["CACHE_TYPE"] = "redis" if env == "production" else "memory"
        
        cache_service = EnhancedCacheService()
        available = cache_service.get_available_cache_types()
        
        print(f"Available in {env}: {available}")
        
        if available:
            cache = await cache_service.get_cache()
            print(f"Selected: {cache.__class__.__name__}")
            
            # Initialize and test the cache
            await cache.connect()
            await cache.set(f"{env}:config", f"configured_for_{env}".encode(), ttl=60)
            value = await cache.get(f"{env}:config")
            print(f"Config test: {value}")
            await cache.disconnect()


async def demonstrate_performance_optimization():
    """Demonstrate performance optimization through protocol selection."""
    print("\n⚡ Performance-Optimized Protocol Selection")
    print("=" * 50)
    
    factory = RuntimeProtocolFactory()
    
    # Create performance-optimized configurations
    high_perf_config = CacheBackendConfig(
        name="high_performance",
        backend_type=CacheBackend.MEMORY,
        max_memory_mb=500,
        eviction_policy="lru"
    )
    
    balanced_config = CacheBackendConfig(
        name="balanced",
        backend_type=CacheBackend.MEMORY,
        max_memory_mb=200,
        eviction_policy="lfu"
    )
    
    # Register different performance tiers
    factory.register(CacheProtocol, ProtocolImplementation(
        name="high_performance_cache",
        implementation_class=MemoryAdapter,  # Fast memory access
        priority=15,
        condition=lambda: os.getenv("PERFORMANCE_TIER") == "high",
        dependencies={
            "config": high_perf_config,
            "max_size": 5000
        },
        description="High-performance memory cache for latency-critical operations"
    ))
    
    factory.register(CacheProtocol, ProtocolImplementation(
        name="balanced_cache",
        implementation_class=MemoryAdapter,  # Memory with different strategy
        priority=10,
        condition=lambda: os.getenv("PERFORMANCE_TIER", "balanced") == "balanced",
        dependencies={
            "config": balanced_config,
            "max_size": 2000
        },
        description="Balanced cache with different eviction strategy"
    ))
    
    # Test different performance tiers
    tiers = ["high", "balanced"]
    
    for tier in tiers:
        print(f"\n--- Performance Tier: {tier} ---")
        os.environ["PERFORMANCE_TIER"] = tier
        
        cache_service = EnhancedCacheService(protocol_factory=factory)
        cache = await cache_service.get_cache()
        
        print(f"Selected for {tier} performance: {cache.__class__.__name__}")
        
        # Initialize the adapter
        await cache.connect()
        
        # Simulate performance test
        import time
        start = time.perf_counter()
        await cache.set(f"perf:{tier}", b"performance_data", ttl=60)
        await cache.get(f"perf:{tier}")
        end = time.perf_counter()
        
        print(f"Operation time: {(end - start) * 1000:.2f}ms")
        
        # Cleanup
        await cache.disconnect()


async def main():
    """Main demonstration."""
    print("🏭 Protocol Factory Integration with Neo-Commons")
    print("=" * 60)
    
    await demonstrate_cache_adaptation()
    await demonstrate_failover_scenario()
    await demonstrate_environment_specific_config()
    await demonstrate_performance_optimization()
    
    print("\n🎉 Integration Demonstration Complete!")
    print("\n💡 Integration Benefits:")
    print("   • Environment-aware service configuration")
    print("   • Automatic failover without code changes")
    print("   • Performance tier optimization")
    print("   • Clean separation of concerns")
    print("   • Runtime adaptation without restarts")
    print("   • Consistent interface across implementations")


if __name__ == "__main__":
    asyncio.run(main())