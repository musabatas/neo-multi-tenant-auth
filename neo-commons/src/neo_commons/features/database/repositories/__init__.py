"""Database repositories - concrete implementations.

This module provides concrete implementations of database protocols
including connection management, schema resolution, and health monitoring.
"""

from .connection_manager import DatabaseConnectionManager, AsyncConnectionPool
from .connection_registry import InMemoryConnectionRegistry
from .redis_connection_registry import RedisConnectionRegistry
from .health_checker import DatabaseHealthChecker, ContinuousHealthMonitor
from .schema_resolver import DatabaseSchemaResolver, SchemaInfo
from .load_balancer import RoundRobinLoadBalancer, WeightedLoadBalancer
from .admin_failover import AdminDatabaseFailover, FailoverState, AdminConnection, FailoverMetrics
from .pool_optimizer import ConnectionPoolOptimizer, OptimizationStrategy, OptimizationTarget, PoolOptimizationDecision

__all__ = [
    "DatabaseConnectionManager",
    "AsyncConnectionPool",
    "InMemoryConnectionRegistry",
    "RedisConnectionRegistry", 
    "DatabaseHealthChecker",
    "ContinuousHealthMonitor",
    "DatabaseSchemaResolver",
    "SchemaInfo",
    "RoundRobinLoadBalancer",
    "WeightedLoadBalancer",
    "AdminDatabaseFailover",
    "FailoverState",
    "AdminConnection", 
    "FailoverMetrics",
    "ConnectionPoolOptimizer",
    "OptimizationStrategy",
    "OptimizationTarget",
    "PoolOptimizationDecision",
]