"""Configurable health check strategy implementations for database connections."""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass
import logging

from ..entities.database_connection import DatabaseConnection
from ....config.constants import ConnectionType
from ..utils.queries import BASIC_HEALTH_CHECK, DATABASE_ACTIVITY_STATS, DATABASE_DETAILED_ACTIVITY

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckQuery:
    """Configuration for a health check query."""
    name: str
    query: str
    timeout_seconds: int = 5
    description: str = ""
    is_critical: bool = True  # If True, failure means unhealthy, if False means degraded


class HealthCheckStrategy(ABC):
    """Abstract base class for health check strategies."""
    
    @abstractmethod
    def get_queries_for_connection(self, connection: DatabaseConnection) -> Dict[str, HealthCheckQuery]:
        """Get health check queries appropriate for the given connection."""
        pass
    
    @abstractmethod
    def evaluate_health_results(self, connection: DatabaseConnection, results: Dict[str, bool]) -> str:
        """Evaluate health check results and return health status."""
        pass


class StandardHealthCheckStrategy(HealthCheckStrategy):
    """Standard health check strategy with basic, extended, and deep checks."""
    
    def __init__(self):
        self._queries = {
            "basic": HealthCheckQuery(
                name="basic",
                query=BASIC_HEALTH_CHECK,
                timeout_seconds=3,
                description="Basic connectivity check",
                is_critical=True
            ),
            "extended": HealthCheckQuery(
                name="extended",
                query="SELECT current_timestamp, version()",
                timeout_seconds=5,
                description="Extended functionality check",
                is_critical=False
            ),
            "deep": HealthCheckQuery(
                name="deep",
                query=DATABASE_ACTIVITY_STATS,
                timeout_seconds=10,
                description="Deep system status check",
                is_critical=False
            )
        }
    
    def get_queries_for_connection(self, connection: DatabaseConnection) -> Dict[str, HealthCheckQuery]:
        """Get health check queries appropriate for the given connection."""
        queries = {"basic": self._queries["basic"]}
        
        # Add extended checks for primary connections
        if connection.connection_type == ConnectionType.PRIMARY:
            queries["extended"] = self._queries["extended"]
            queries["deep"] = self._queries["deep"]
        
        # Add basic extended check for replicas
        elif connection.connection_type == ConnectionType.REPLICA:
            queries["extended"] = self._queries["extended"]
        
        return queries
    
    def evaluate_health_results(self, connection: DatabaseConnection, results: Dict[str, bool]) -> str:
        """Evaluate health check results and return health status."""
        # Check critical queries first
        critical_passed = all(
            results.get(name, False) 
            for name, query in self._queries.items() 
            if query.is_critical and name in results
        )
        
        if not critical_passed:
            return "unhealthy"
        
        # Check non-critical queries
        non_critical_passed = all(
            results.get(name, True)  # Default to True for missing non-critical checks
            for name, query in self._queries.items()
            if not query.is_critical and name in results
        )
        
        # Factor in connection's failure history
        if connection.consecutive_failures > 0:
            failure_threshold = connection.max_consecutive_failures // 2
            if connection.consecutive_failures >= failure_threshold:
                return "degraded" if non_critical_passed else "unhealthy"
        
        return "healthy" if non_critical_passed else "degraded"


class MinimalHealthCheckStrategy(HealthCheckStrategy):
    """Minimal health check strategy - only basic connectivity."""
    
    def __init__(self):
        self._basic_query = HealthCheckQuery(
            name="basic",
            query=BASIC_HEALTH_CHECK,
            timeout_seconds=3,
            description="Basic connectivity check",
            is_critical=True
        )
    
    def get_queries_for_connection(self, connection: DatabaseConnection) -> Dict[str, HealthCheckQuery]:
        """Get minimal health check queries."""
        return {"basic": self._basic_query}
    
    def evaluate_health_results(self, connection: DatabaseConnection, results: Dict[str, bool]) -> str:
        """Simple evaluation - healthy if basic check passes."""
        return "healthy" if results.get("basic", False) else "unhealthy"


class CustomHealthCheckStrategy(HealthCheckStrategy):
    """Customizable health check strategy with user-defined queries."""
    
    def __init__(self, custom_queries: Dict[str, HealthCheckQuery]):
        self._custom_queries = custom_queries
    
    def get_queries_for_connection(self, connection: DatabaseConnection) -> Dict[str, HealthCheckQuery]:
        """Get custom health check queries."""
        return self._custom_queries.copy()
    
    def evaluate_health_results(self, connection: DatabaseConnection, results: Dict[str, bool]) -> str:
        """Evaluate based on custom criteria."""
        # All critical queries must pass
        critical_queries = [q for q in self._custom_queries.values() if q.is_critical]
        if critical_queries:
            critical_passed = all(results.get(q.name, False) for q in critical_queries)
            if not critical_passed:
                return "unhealthy"
        
        # Non-critical queries affect degraded vs healthy
        non_critical_queries = [q for q in self._custom_queries.values() if not q.is_critical]
        if non_critical_queries:
            non_critical_passed = all(results.get(q.name, True) for q in non_critical_queries)
            return "healthy" if non_critical_passed else "degraded"
        
        return "healthy"


class DatabaseTypeSpecificStrategy(HealthCheckStrategy):
    """Health check strategy that adapts to different database types."""
    
    def __init__(self):
        # PostgreSQL specific queries
        self._postgres_queries = {
            "basic": HealthCheckQuery(
                name="basic",
                query=BASIC_HEALTH_CHECK,
                timeout_seconds=3,
                description="Basic PostgreSQL connectivity",
                is_critical=True
            ),
            "replication": HealthCheckQuery(
                name="replication", 
                query="SELECT pg_is_in_recovery(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()",
                timeout_seconds=5,
                description="PostgreSQL replication status",
                is_critical=False
            ),
            "performance": HealthCheckQuery(
                name="performance",
                query=DATABASE_DETAILED_ACTIVITY,
                timeout_seconds=7,
                description="PostgreSQL performance metrics",
                is_critical=False
            )
        }
    
    def get_queries_for_connection(self, connection: DatabaseConnection) -> Dict[str, HealthCheckQuery]:
        """Get database-type-specific health check queries."""
        queries = {"basic": self._postgres_queries["basic"]}
        
        # Add replication check for replicas
        if connection.connection_type == ConnectionType.REPLICA:
            queries["replication"] = self._postgres_queries["replication"]
        
        # Add performance monitoring for primary connections
        if connection.connection_type == ConnectionType.PRIMARY:
            queries["performance"] = self._postgres_queries["performance"]
        
        return queries
    
    def evaluate_health_results(self, connection: DatabaseConnection, results: Dict[str, bool]) -> str:
        """Evaluate with database-specific logic."""
        # Basic connectivity is always critical
        if not results.get("basic", False):
            return "unhealthy"
        
        # For replicas, check replication health
        if connection.connection_type == ConnectionType.REPLICA:
            replication_healthy = results.get("replication", True)
            return "healthy" if replication_healthy else "degraded"
        
        # For primary, check performance metrics
        if connection.connection_type == ConnectionType.PRIMARY:
            performance_healthy = results.get("performance", True)
            return "healthy" if performance_healthy else "degraded"
        
        return "healthy"


# Factory function for easy strategy creation
def create_health_strategy(strategy_name: str = "standard", 
                          custom_queries: Optional[Dict[str, HealthCheckQuery]] = None) -> HealthCheckStrategy:
    """Factory function to create health check strategies.
    
    Args:
        strategy_name: Name of the strategy ('standard', 'minimal', 'custom', 'database_specific')
        custom_queries: Custom queries for 'custom' strategy
        
    Returns:
        Health check strategy instance
    """
    strategies = {
        "standard": StandardHealthCheckStrategy,
        "minimal": MinimalHealthCheckStrategy,
        "database_specific": DatabaseTypeSpecificStrategy,
    }
    
    if strategy_name == "custom":
        if not custom_queries:
            raise ValueError("Custom queries required for 'custom' strategy")
        return CustomHealthCheckStrategy(custom_queries)
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategies.keys())}")
    
    return strategies[strategy_name]()