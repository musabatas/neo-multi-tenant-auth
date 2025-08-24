"""Connection load balancer implementation for neo-commons."""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, field

from ..entities.protocols import ConnectionLoadBalancer
from ..entities.database_connection import DatabaseConnection
from ....core.value_objects.identifiers import RegionId
from ....config.constants import ConnectionType

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """Performance metrics for a database connection."""
    response_times: List[float] = field(default_factory=list)
    error_count: int = 0
    last_error: Optional[datetime] = None
    total_requests: int = 0
    active_requests: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


class RoundRobinLoadBalancer(ConnectionLoadBalancer):
    """Round-robin load balancing implementation."""
    
    def __init__(self, connection_registry):
        self._connection_registry = connection_registry
        self._metrics: Dict[str, ConnectionMetrics] = {}
        self._round_robin_index: Dict[str, int] = {}  # Per connection type
        self._lock = asyncio.Lock()
    
    async def get_best_connection(self, 
                                 connection_type: ConnectionType,
                                 region_id: Optional[RegionId] = None,
                                 read_only: bool = False) -> Optional[DatabaseConnection]:
        """Get the best available connection based on round-robin strategy."""
        try:
            # Get healthy connections of the specified type
            connections = await self._connection_registry.get_healthy_connections(
                connection_type=connection_type,
                region_id=region_id
            )
            
            if not connections:
                logger.warning(f"No healthy connections found for type {connection_type}")
                return None
            
            # For read-only requests, prefer replica connections if available
            if read_only and connection_type == ConnectionType.PRIMARY:
                replica_connections = await self._connection_registry.get_healthy_connections(
                    connection_type=ConnectionType.REPLICA,
                    region_id=region_id
                )
                if replica_connections:
                    connections = replica_connections
                    connection_type = ConnectionType.REPLICA
            
            # Round-robin selection
            async with self._lock:
                type_key = f"{connection_type.value}:{region_id.value if region_id else 'any'}"
                
                if type_key not in self._round_robin_index:
                    self._round_robin_index[type_key] = 0
                
                index = self._round_robin_index[type_key]
                selected_connection = connections[index % len(connections)]
                
                # Update index for next selection
                self._round_robin_index[type_key] = (index + 1) % len(connections)
                
                logger.debug(f"Selected connection {selected_connection.connection_name} "
                           f"(index {index % len(connections)} of {len(connections)})")
                
                return selected_connection
                
        except Exception as e:
            logger.error(f"Failed to get best connection: {e}")
            return None
    
    async def update_connection_metrics(self, 
                                       connection: DatabaseConnection,
                                       response_time_ms: float,
                                       error: Optional[Exception] = None) -> None:
        """Update connection performance metrics."""
        try:
            conn_name = connection.connection_name
            
            if conn_name not in self._metrics:
                self._metrics[conn_name] = ConnectionMetrics()
            
            metrics = self._metrics[conn_name]
            
            # Update response time (keep last 100 measurements)
            metrics.response_times.append(response_time_ms)
            if len(metrics.response_times) > 100:
                metrics.response_times.pop(0)
            
            # Update error tracking
            if error:
                metrics.error_count += 1
                metrics.last_error = datetime.now()
                logger.warning(f"Connection {conn_name} error: {error}")
            
            # Update request counters
            metrics.total_requests += 1
            metrics.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to update connection metrics: {e}")
    
    async def get_connection_load(self, connection: DatabaseConnection) -> float:
        """Get current load metric for a connection (0.0 to 1.0)."""
        try:
            conn_name = connection.connection_name
            
            if conn_name not in self._metrics:
                return 0.0  # No load data available
            
            metrics = self._metrics[conn_name]
            
            # Calculate load based on active requests and error rate
            if metrics.total_requests == 0:
                return 0.0
            
            # Base load from active requests (assuming 10 is high load)
            active_load = min(metrics.active_requests / 10.0, 1.0)
            
            # Error rate penalty (recent errors increase perceived load)
            error_rate = metrics.error_count / max(metrics.total_requests, 1)
            error_penalty = min(error_rate * 2.0, 0.5)  # Max 50% penalty
            
            # Response time factor (slower connections have higher load)
            if metrics.response_times:
                avg_response_time = sum(metrics.response_times) / len(metrics.response_times)
                # Normalize around 100ms baseline
                response_factor = min(max(avg_response_time - 100, 0) / 500.0, 0.3)
            else:
                response_factor = 0.0
            
            total_load = min(active_load + error_penalty + response_factor, 1.0)
            return total_load
            
        except Exception as e:
            logger.error(f"Failed to get connection load: {e}")
            return 1.0  # Assume high load on error


class WeightedLoadBalancer(ConnectionLoadBalancer):
    """Weighted load balancing based on connection performance metrics."""
    
    def __init__(self, connection_registry):
        self._connection_registry = connection_registry
        self._metrics: Dict[str, ConnectionMetrics] = {}
        self._lock = asyncio.Lock()
    
    async def get_best_connection(self, 
                                 connection_type: ConnectionType,
                                 region_id: Optional[RegionId] = None,
                                 read_only: bool = False) -> Optional[DatabaseConnection]:
        """Get the best connection based on performance metrics."""
        try:
            connections = await self._connection_registry.get_healthy_connections(
                connection_type=connection_type,
                region_id=region_id
            )
            
            if not connections:
                return None
            
            if len(connections) == 1:
                return connections[0]
            
            # Calculate weights based on inverse load (lower load = higher weight)
            weighted_connections = []
            
            for conn in connections:
                load = await self.get_connection_load(conn)
                weight = max(1.0 - load, 0.1)  # Minimum weight of 0.1
                weighted_connections.append((conn, weight))
            
            # Select connection based on weights
            total_weight = sum(weight for _, weight in weighted_connections)
            
            if total_weight == 0:
                # Fallback to random selection
                return connections[0]
            
            # Weighted random selection
            import random
            random_value = random.random() * total_weight
            current_weight = 0
            
            for conn, weight in weighted_connections:
                current_weight += weight
                if random_value <= current_weight:
                    logger.debug(f"Selected connection {conn.connection_name} "
                               f"with weight {weight:.2f} (load: {1-weight:.2f})")
                    return conn
            
            # Fallback (should not happen)
            return connections[0]
            
        except Exception as e:
            logger.error(f"Failed to get best connection: {e}")
            return None
    
    async def update_connection_metrics(self, 
                                       connection: DatabaseConnection,
                                       response_time_ms: float,
                                       error: Optional[Exception] = None) -> None:
        """Update connection performance metrics."""
        # Same implementation as RoundRobinLoadBalancer
        try:
            conn_name = connection.connection_name
            
            if conn_name not in self._metrics:
                self._metrics[conn_name] = ConnectionMetrics()
            
            metrics = self._metrics[conn_name]
            metrics.response_times.append(response_time_ms)
            
            if len(metrics.response_times) > 100:
                metrics.response_times.pop(0)
            
            if error:
                metrics.error_count += 1
                metrics.last_error = datetime.now()
            
            metrics.total_requests += 1
            metrics.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to update connection metrics: {e}")
    
    async def get_connection_load(self, connection: DatabaseConnection) -> float:
        """Get current load metric for a connection (0.0 to 1.0)."""
        # Same implementation as RoundRobinLoadBalancer
        try:
            conn_name = connection.connection_name
            
            if conn_name not in self._metrics:
                return 0.0
            
            metrics = self._metrics[conn_name]
            
            if metrics.total_requests == 0:
                return 0.0
            
            active_load = min(metrics.active_requests / 10.0, 1.0)
            error_rate = metrics.error_count / max(metrics.total_requests, 1)
            error_penalty = min(error_rate * 2.0, 0.5)
            
            if metrics.response_times:
                avg_response_time = sum(metrics.response_times) / len(metrics.response_times)
                response_factor = min(max(avg_response_time - 100, 0) / 500.0, 0.3)
            else:
                response_factor = 0.0
            
            total_load = min(active_load + error_penalty + response_factor, 1.0)
            return total_load
            
        except Exception as e:
            logger.error(f"Failed to get connection load: {e}")
            return 1.0