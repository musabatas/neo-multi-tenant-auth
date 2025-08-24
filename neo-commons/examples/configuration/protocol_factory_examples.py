"""Examples of using the Protocol Factory for runtime protocol adaptation.

This demonstrates how to use the protocol factory for flexible dependency injection
with runtime adaptation capabilities.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from typing import Optional, Dict, Any
from neo_commons.infrastructure.protocols.factory import (
    RuntimeProtocolFactory, ProtocolImplementation, AdaptationStrategy,
    protocol_implementation, create_protocol, register_implementation
)
from neo_commons.infrastructure.protocols.infrastructure import (
    CacheProtocol, DatabaseConnectionProtocol, AuthenticationProviderProtocol
)


# Example Protocol Implementation Classes

class RedisCache:
    """Redis-based cache implementation."""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self._connected = False
    
    async def get(self, key: str, tenant_id: Optional[str] = None) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self._connected:
            await self.connect()
        
        # Mock implementation
        print(f"Redis GET: {key} (tenant: {tenant_id})")
        return None
    
    async def set(self, key: str, value: Any, ttl: int, tenant_id: Optional[str] = None) -> None:
        """Set value in Redis cache."""
        if not self._connected:
            await self.connect()
        
        print(f"Redis SET: {key}={value}, TTL={ttl} (tenant: {tenant_id})")
    
    async def delete(self, key: str, tenant_id: Optional[str] = None) -> None:
        """Delete from Redis cache."""
        if not self._connected:
            await self.connect()
        
        print(f"Redis DELETE: {key} (tenant: {tenant_id})")
    
    async def invalidate_pattern(self, pattern: str, tenant_id: Optional[str] = None) -> None:
        """Invalidate Redis keys matching pattern."""
        if not self._connected:
            await self.connect()
        
        print(f"Redis INVALIDATE: {pattern} (tenant: {tenant_id})")
    
    async def connect(self):
        """Connect to Redis."""
        print(f"Connecting to Redis at {self.host}:{self.port}")
        self._connected = True


class MemoryCache:
    """In-memory cache implementation."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
    
    async def get(self, key: str, tenant_id: Optional[str] = None) -> Optional[Any]:
        """Get from memory cache."""
        cache_key = f"{tenant_id}:{key}" if tenant_id else key
        value = self._data.get(cache_key)
        print(f"Memory GET: {key}={value} (tenant: {tenant_id})")
        return value
    
    async def set(self, key: str, value: Any, ttl: int, tenant_id: Optional[str] = None) -> None:
        """Set in memory cache."""
        cache_key = f"{tenant_id}:{key}" if tenant_id else key
        self._data[cache_key] = value
        print(f"Memory SET: {key}={value} (tenant: {tenant_id})")
        # Note: TTL not implemented in this simple example
    
    async def delete(self, key: str, tenant_id: Optional[str] = None) -> None:
        """Delete from memory cache."""
        cache_key = f"{tenant_id}:{key}" if tenant_id else key
        self._data.pop(cache_key, None)
        print(f"Memory DELETE: {key} (tenant: {tenant_id})")
    
    async def invalidate_pattern(self, pattern: str, tenant_id: Optional[str] = None) -> None:
        """Invalidate memory cache patterns."""
        prefix = f"{tenant_id}:" if tenant_id else ""
        keys_to_delete = [
            key for key in self._data.keys() 
            if key.startswith(prefix) and pattern in key
        ]
        for key in keys_to_delete:
            del self._data[key]
        print(f"Memory INVALIDATE: {pattern}, deleted {len(keys_to_delete)} keys")


@protocol_implementation(
    protocol_type=CacheProtocol,
    name="redis_cache_auto",
    priority=10,
    condition=lambda: True,  # Always available in this example
    dependencies={"host": "localhost", "port": 6379},
    description="Redis cache with automatic registration"
)
class AutoRedisCache(RedisCache):
    """Redis cache with automatic protocol registration."""
    pass


# Mock conditions
def redis_available() -> bool:
    """Check if Redis is available."""
    # In real implementation, this would check Redis connectivity
    return True

def memory_fallback_only() -> bool:
    """Only use memory cache as fallback."""
    return not redis_available()


async def demonstrate_basic_usage():
    """Demonstrate basic protocol factory usage."""
    print("🏭 Basic Protocol Factory Usage")
    print("=" * 50)
    
    # Create factory with priority-based strategy
    factory = RuntimeProtocolFactory(strategy=AdaptationStrategy.PRIORITY_ORDER)
    
    # Register Redis cache implementation (high priority)
    redis_impl = ProtocolImplementation(
        name="redis_cache",
        implementation_class=RedisCache,
        priority=10,
        condition=redis_available,
        dependencies={"host": "redis.example.com", "port": 6379},
        description="Production Redis cache"
    )
    factory.register(CacheProtocol, redis_impl)
    
    # Register memory cache fallback (lower priority)
    memory_impl = ProtocolImplementation(
        name="memory_cache",
        implementation_class=MemoryCache,
        priority=5,
        condition=lambda: True,  # Always available
        description="In-memory fallback cache"
    )
    factory.register(CacheProtocol, memory_impl)
    
    # Create cache instance (will use highest priority available)
    cache = factory.create(CacheProtocol)
    
    # Use the cache
    await cache.set("user:123", {"name": "Alice"}, ttl=300, tenant_id="tenant1")
    value = await cache.get("user:123", tenant_id="tenant1")
    await cache.delete("user:123", tenant_id="tenant1")
    
    print(f"\n✅ Created cache implementation: {cache.__class__.__name__}")


async def demonstrate_failover_strategy():
    """Demonstrate failover adaptation strategy."""
    print("\n🔄 Failover Strategy Demonstration")
    print("=" * 50)
    
    # Factory with failover strategy
    factory = RuntimeProtocolFactory(strategy=AdaptationStrategy.FAILOVER)
    
    # Failing implementation (primary)
    class FailingCache:
        def __init__(self):
            raise Exception("Cache service unavailable")
    
    # Register implementations
    factory.register(CacheProtocol, ProtocolImplementation(
        name="failing_cache",
        implementation_class=FailingCache,
        priority=10,
        description="Primary cache that fails"
    ))
    
    factory.register(CacheProtocol, ProtocolImplementation(
        name="backup_cache",
        implementation_class=MemoryCache,
        priority=5,
        description="Backup memory cache"
    ))
    
    # Create cache - should failover to backup
    cache = factory.create(CacheProtocol)
    
    await cache.set("failover:test", "backup_works", ttl=60)
    
    print(f"✅ Failover successful: {cache.__class__.__name__}")


async def demonstrate_named_implementations():
    """Demonstrate creating specific named implementations."""
    print("\n🏷️  Named Implementation Selection")
    print("=" * 50)
    
    factory = RuntimeProtocolFactory()
    
    # Register multiple cache implementations
    factory.register(CacheProtocol, ProtocolImplementation(
        name="redis_primary",
        implementation_class=RedisCache,
        dependencies={"host": "redis-primary.example.com", "port": 6379}
    ))
    
    factory.register(CacheProtocol, ProtocolImplementation(
        name="redis_secondary", 
        implementation_class=RedisCache,
        dependencies={"host": "redis-secondary.example.com", "port": 6379}
    ))
    
    factory.register(CacheProtocol, ProtocolImplementation(
        name="memory_local",
        implementation_class=MemoryCache
    ))
    
    # Create specific implementations
    primary_cache = factory.create_named(CacheProtocol, "redis_primary")
    secondary_cache = factory.create_named(CacheProtocol, "redis_secondary")
    local_cache = factory.create_named(CacheProtocol, "memory_local")
    
    # Use different caches for different purposes
    await primary_cache.set("session:abc", {"user_id": 123}, ttl=1800)
    await secondary_cache.set("temp:xyz", {"data": "temp"}, ttl=60)
    await local_cache.set("config:app", {"debug": True}, ttl=300)
    
    print(f"✅ Created primary cache: {primary_cache.__class__.__name__}")
    print(f"✅ Created secondary cache: {secondary_cache.__class__.__name__}")
    print(f"✅ Created local cache: {local_cache.__class__.__name__}")


async def demonstrate_load_balancing():
    """Demonstrate load balancing strategy."""
    print("\n⚖️  Load Balancing Strategy")
    print("=" * 50)
    
    factory = RuntimeProtocolFactory(strategy=AdaptationStrategy.LOAD_BALANCED)
    
    # Register multiple equivalent implementations
    for i in range(3):
        factory.register(CacheProtocol, ProtocolImplementation(
            name=f"redis_node_{i}",
            implementation_class=RedisCache,
            priority=10,  # Same priority for load balancing
            dependencies={"host": f"redis-{i}.cluster.local", "port": 6379},
            description=f"Redis cluster node {i}"
        ))
    
    # Create multiple cache instances (will be distributed)
    print("Creating 5 cache instances with load balancing:")
    for i in range(5):
        cache = factory.create(CacheProtocol)
        print(f"Instance {i+1}: Connected to {cache.host}")


def demonstrate_decorator_registration():
    """Demonstrate automatic registration via decorator."""
    print("\n🎭 Decorator-Based Registration")
    print("=" * 50)
    
    # The AutoRedisCache class was registered via decorator
    factory = RuntimeProtocolFactory()
    
    # Check registered implementations
    available = factory.get_available_implementations(CacheProtocol)
    print(f"Available implementations: {available}")
    
    # Registry info
    info = factory.get_registry_info()
    for protocol_name, impls in info.items():
        print(f"\n{protocol_name}:")
        for impl in impls:
            print(f"  - {impl['name']}: {impl['class']} (priority: {impl['priority']})")


async def demonstrate_conditional_implementations():
    """Demonstrate conditional implementations."""
    print("\n🔀 Conditional Implementation Loading")
    print("=" * 50)
    
    factory = RuntimeProtocolFactory()
    
    # Register implementations with conditions
    factory.register(CacheProtocol, ProtocolImplementation(
        name="redis_production",
        implementation_class=RedisCache,
        priority=10,
        condition=lambda: os.getenv("ENVIRONMENT") == "production",
        dependencies={"host": "redis-prod.example.com", "port": 6379},
        description="Production Redis (only in prod environment)"
    ))
    
    factory.register(CacheProtocol, ProtocolImplementation(
        name="redis_development",
        implementation_class=RedisCache,
        priority=8,
        condition=lambda: os.getenv("ENVIRONMENT", "development") == "development",
        dependencies={"host": "localhost", "port": 6379},
        description="Development Redis"
    ))
    
    factory.register(CacheProtocol, ProtocolImplementation(
        name="memory_testing",
        implementation_class=MemoryCache,
        priority=5,
        condition=lambda: os.getenv("ENVIRONMENT") == "testing",
        description="Testing memory cache"
    ))
    
    # Show available implementations based on environment
    available = factory.get_available_implementations(CacheProtocol)
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"Available cache implementations: {available}")
    
    # Create cache based on environment
    if available:
        cache = factory.create(CacheProtocol)
        await cache.set("env:test", f"running_in_{os.getenv('ENVIRONMENT', 'development')}", ttl=60)
        print(f"✅ Using cache: {cache.__class__.__name__}")


async def demonstrate_singleton_behavior():
    """Demonstrate singleton pattern in protocol factory."""
    print("\n🔄 Singleton Behavior")
    print("=" * 50)
    
    factory = RuntimeProtocolFactory()
    
    # Register singleton implementation
    factory.register(CacheProtocol, ProtocolImplementation(
        name="singleton_cache",
        implementation_class=MemoryCache,
        singleton=True
    ))
    
    # Create multiple instances - should be same object
    cache1 = factory.create(CacheProtocol)
    cache2 = factory.create(CacheProtocol)
    
    print(f"Cache 1 ID: {id(cache1)}")
    print(f"Cache 2 ID: {id(cache2)}")
    print(f"Same instance: {cache1 is cache2}")
    
    # Set value in cache1, should be visible in cache2
    await cache1.set("singleton:test", "shared_state", ttl=60)
    value = await cache2.get("singleton:test")
    print(f"Shared state verification: {value is not None}")


async def main():
    """Main demonstration."""
    print("🏭 Protocol Factory Pattern Demonstration")
    print("=" * 60)
    
    await demonstrate_basic_usage()
    await demonstrate_failover_strategy()
    await demonstrate_named_implementations()
    await demonstrate_load_balancing()
    demonstrate_decorator_registration()
    await demonstrate_conditional_implementations()
    await demonstrate_singleton_behavior()
    
    print("\n🎉 Protocol Factory Demonstration Complete!")
    print("\n💡 Key Benefits:")
    print("   • Dynamic protocol implementation selection at runtime")
    print("   • Automatic failover and fallback mechanisms")
    print("   • Environment-specific implementation loading")
    print("   • Load balancing across multiple implementations")
    print("   • Singleton pattern support for resource management")
    print("   • Configuration-driven protocol adaptation")
    print("   • Clean separation of interface and implementation")


if __name__ == "__main__":
    # Set environment for testing
    os.environ["ENVIRONMENT"] = "development"
    
    asyncio.run(main())