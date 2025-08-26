"""Event sourcing optimization service for high-volume event store scenarios.

Provides advanced optimization techniques for event sourcing including:
- Event stream processing for memory efficiency
- Aggregate snapshot management
- Event store partitioning and sharding
- Optimized projection building
- Smart caching strategies
- Query optimization for high-volume scenarios
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, Set, Tuple
from uuid import UUID, uuid4
from enum import Enum

from ..entities.domain_event import DomainEvent
from ..repositories.domain_event_repository import DomainEventDatabaseRepository
from ....core.value_objects import EventId, UserId, EventType


logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Event sourcing optimization strategies."""
    STREAM_PROCESSING = "stream_processing"
    SNAPSHOT_MANAGEMENT = "snapshot_management" 
    PARTITIONING = "partitioning"
    CACHING = "caching"
    PROJECTION_OPTIMIZATION = "projection_optimization"
    SHARDING = "sharding"
    QUERY_OPTIMIZATION = "query_optimization"


class PartitionStrategy(Enum):
    """Event store partitioning strategies."""
    TIME_BASED = "time_based"  # Partition by time periods (daily, weekly, monthly)
    AGGREGATE_BASED = "aggregate_based"  # Partition by aggregate type
    CONTEXT_BASED = "context_based"  # Partition by context (tenant, organization)
    HYBRID = "hybrid"  # Combination of strategies


class SnapshotStrategy(Enum):
    """Aggregate snapshot creation strategies."""
    EVENT_COUNT = "event_count"  # Create snapshot every N events
    TIME_BASED = "time_based"  # Create snapshot every N time units
    SIZE_BASED = "size_based"  # Create snapshot when aggregate size exceeds threshold
    ADAPTIVE = "adaptive"  # Dynamic strategy based on access patterns


@dataclass
class EventStreamChunk:
    """A chunk of events for stream processing."""
    events: List[DomainEvent]
    chunk_id: str
    start_timestamp: datetime
    end_timestamp: datetime
    aggregate_types: Set[str]
    total_size_bytes: int
    compression_ratio: Optional[float] = None


@dataclass
class AggregateSnapshot:
    """Snapshot of an aggregate state at a specific point in time."""
    id: UUID
    aggregate_id: UUID
    aggregate_type: str
    aggregate_version: int
    snapshot_data: Dict[str, Any]
    event_count: int
    last_event_id: EventId
    created_at: datetime
    expires_at: Optional[datetime] = None
    size_bytes: int = 0
    compression_ratio: Optional[float] = None


@dataclass
class ProjectionState:
    """State of a read model projection."""
    projection_name: str
    last_processed_event_id: EventId
    last_processed_timestamp: datetime
    version: int
    event_count: int
    errors_count: int = 0
    processing_time_ms: float = 0
    throughput_events_per_second: float = 0


@dataclass
class OptimizationMetrics:
    """Metrics for event sourcing optimization."""
    strategy: OptimizationStrategy
    events_processed: int
    processing_time_seconds: float
    throughput_events_per_second: float
    memory_usage_mb: float
    cache_hit_ratio: Optional[float] = None
    compression_ratio: Optional[float] = None
    partition_efficiency: Optional[float] = None


class EventSourcingOptimizationService:
    """Service for optimizing event sourcing in high-volume scenarios."""
    
    def __init__(
        self,
        event_repository: DomainEventDatabaseRepository,
        max_chunk_size: int = 10000,
        max_memory_mb: int = 1024,
        snapshot_interval_events: int = 100,
        snapshot_interval_hours: int = 24,
        cache_size_mb: int = 256,
        thread_pool_size: int = 4
    ):
        """Initialize the optimization service.
        
        Args:
            event_repository: Domain event repository
            max_chunk_size: Maximum events per chunk for stream processing
            max_memory_mb: Maximum memory usage in MB
            snapshot_interval_events: Create snapshot every N events
            snapshot_interval_hours: Create snapshot every N hours
            cache_size_mb: Cache size limit in MB
            thread_pool_size: Number of threads for parallel processing
        """
        self._event_repository = event_repository
        self._max_chunk_size = max_chunk_size
        self._max_memory_mb = max_memory_mb
        self._snapshot_interval_events = snapshot_interval_events
        self._snapshot_interval_hours = snapshot_interval_hours
        self._cache_size_mb = cache_size_mb
        
        # Thread pool for CPU-intensive operations
        self._thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        
        # In-memory caches (in production, use Redis)
        self._event_cache: Dict[str, DomainEvent] = {}
        self._snapshot_cache: Dict[str, AggregateSnapshot] = {}
        self._projection_state_cache: Dict[str, ProjectionState] = {}
        
        # Optimization metrics
        self._metrics: List[OptimizationMetrics] = []
        
        # Active optimization tasks
        self._active_tasks: Dict[str, asyncio.Task] = {}
    
    async def stream_process_events(
        self,
        criteria: Dict[str, Any],
        processor_func: Callable[[EventStreamChunk], Any],
        chunk_size: Optional[int] = None
    ) -> AsyncGenerator[OptimizationMetrics, None]:
        """Process events in streaming fashion for memory efficiency.
        
        Args:
            criteria: Event selection criteria
            processor_func: Function to process each event chunk
            chunk_size: Events per chunk (defaults to max_chunk_size)
            
        Yields:
            OptimizationMetrics: Processing metrics for each chunk
        """
        chunk_size = chunk_size or self._max_chunk_size
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting stream processing with chunk size: {chunk_size}")
        
        try:
            async for chunk in self._create_event_stream(criteria, chunk_size):
                chunk_start = datetime.now(timezone.utc)
                
                # Process chunk (potentially in thread pool for CPU-intensive work)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self._thread_pool, processor_func, chunk)
                
                chunk_end = datetime.now(timezone.utc)
                processing_time = (chunk_end - chunk_start).total_seconds()
                
                # Calculate metrics
                metrics = OptimizationMetrics(
                    strategy=OptimizationStrategy.STREAM_PROCESSING,
                    events_processed=len(chunk.events),
                    processing_time_seconds=processing_time,
                    throughput_events_per_second=len(chunk.events) / processing_time if processing_time > 0 else 0,
                    memory_usage_mb=self._estimate_chunk_memory_usage(chunk),
                    compression_ratio=chunk.compression_ratio
                )
                
                self._metrics.append(metrics)
                yield metrics
                
                logger.debug(f"Processed chunk {chunk.chunk_id}: {len(chunk.events)} events in {processing_time:.2f}s")
        
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            raise
    
    async def create_aggregate_snapshot(
        self,
        aggregate_id: UUID,
        aggregate_type: str,
        strategy: SnapshotStrategy = SnapshotStrategy.ADAPTIVE,
        force_create: bool = False
    ) -> Optional[AggregateSnapshot]:
        """Create or update an aggregate snapshot for faster event replay.
        
        Args:
            aggregate_id: ID of the aggregate
            aggregate_type: Type of the aggregate
            strategy: Snapshot creation strategy
            force_create: Force snapshot creation regardless of strategy
            
        Returns:
            Created snapshot or None if not needed
        """
        logger.info(f"Creating snapshot for {aggregate_type}:{aggregate_id}")
        
        try:
            # Check if snapshot is needed
            if not force_create and not await self._should_create_snapshot(
                aggregate_id, aggregate_type, strategy
            ):
                return None
            
            # Get all events for the aggregate
            events = await self._event_repository.get_by_aggregate(aggregate_type, aggregate_id)
            
            if not events:
                logger.warning(f"No events found for {aggregate_type}:{aggregate_id}")
                return None
            
            # Build aggregate state from events
            aggregate_state = await self._build_aggregate_state(events)
            
            # Create snapshot
            snapshot = AggregateSnapshot(
                id=uuid4(),
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                aggregate_version=max(event.aggregate_version for event in events),
                snapshot_data=aggregate_state,
                event_count=len(events),
                last_event_id=events[-1].id,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=self._snapshot_interval_hours * 2)
            )
            
            # Calculate snapshot size
            snapshot.size_bytes = len(json.dumps(aggregate_state).encode('utf-8'))
            
            # Cache the snapshot
            cache_key = f"{aggregate_type}:{aggregate_id}"
            self._snapshot_cache[cache_key] = snapshot
            
            # In production, persist to database
            # await self._persist_snapshot(snapshot)
            
            logger.info(f"Created snapshot for {aggregate_type}:{aggregate_id} with {len(events)} events")
            return snapshot
        
        except Exception as e:
            logger.error(f"Failed to create snapshot for {aggregate_type}:{aggregate_id}: {str(e)}")
            raise
    
    async def optimize_event_queries(
        self,
        query_patterns: List[Dict[str, Any]],
        optimization_level: str = "balanced"
    ) -> Dict[str, Any]:
        """Optimize event queries for high-volume scenarios.
        
        Args:
            query_patterns: List of common query patterns to optimize
            optimization_level: Level of optimization (fast, balanced, maximum)
            
        Returns:
            Optimization results and recommendations
        """
        logger.info(f"Optimizing event queries with {optimization_level} level")
        
        start_time = datetime.now(timezone.utc)
        results = {
            "optimization_level": optimization_level,
            "patterns_analyzed": len(query_patterns),
            "recommendations": [],
            "index_suggestions": [],
            "partition_suggestions": [],
            "query_optimizations": []
        }
        
        try:
            for pattern in query_patterns:
                # Analyze query pattern
                analysis = await self._analyze_query_pattern(pattern)
                
                # Generate optimization recommendations
                if optimization_level in ["balanced", "maximum"]:
                    # Index recommendations
                    if "aggregate_id" in pattern or "aggregate_type" in pattern:
                        results["index_suggestions"].append({
                            "type": "composite_index",
                            "columns": ["aggregate_type", "aggregate_id", "aggregate_version"],
                            "reason": "Optimize aggregate event retrieval"
                        })
                    
                    if "context_id" in pattern:
                        results["index_suggestions"].append({
                            "type": "index",
                            "columns": ["context_id", "occurred_at"],
                            "reason": "Optimize context-based queries with time ordering"
                        })
                    
                    if "event_type" in pattern:
                        results["index_suggestions"].append({
                            "type": "index",
                            "columns": ["event_type", "occurred_at"],
                            "reason": "Optimize event type filtering with time ordering"
                        })
                
                if optimization_level == "maximum":
                    # Partition recommendations
                    if analysis.get("high_volume"):
                        results["partition_suggestions"].append({
                            "strategy": "time_based",
                            "interval": "monthly",
                            "reason": "High volume queries benefit from time-based partitioning"
                        })
                    
                    if analysis.get("multi_tenant"):
                        results["partition_suggestions"].append({
                            "strategy": "context_based",
                            "column": "context_id",
                            "reason": "Multi-tenant queries benefit from context partitioning"
                        })
                
                # Query optimization suggestions
                results["query_optimizations"].extend([
                    {
                        "optimization": "add_limit",
                        "suggestion": "Add LIMIT clauses to prevent large result sets",
                        "impact": "High"
                    },
                    {
                        "optimization": "selective_columns",
                        "suggestion": "Select only required columns instead of SELECT *",
                        "impact": "Medium"
                    },
                    {
                        "optimization": "prepared_statements",
                        "suggestion": "Use prepared statements for repeated queries",
                        "impact": "Medium"
                    }
                ])
            
            # General recommendations
            results["recommendations"].extend([
                "Consider implementing event archival for old events",
                "Use connection pooling for high-concurrency scenarios",
                "Implement read replicas for query-heavy workloads",
                "Monitor query performance and adjust indexes accordingly"
            ])
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            results["processing_time_seconds"] = processing_time
            
            logger.info(f"Query optimization completed in {processing_time:.2f}s")
            return results
        
        except Exception as e:
            logger.error(f"Failed to optimize queries: {str(e)}")
            raise
    
    async def manage_event_projections(
        self,
        projection_name: str,
        projection_builder: Callable[[DomainEvent], Any],
        from_event_id: Optional[EventId] = None,
        batch_size: int = 1000
    ) -> ProjectionState:
        """Efficiently build and update read model projections from events.
        
        Args:
            projection_name: Name of the projection to build
            projection_builder: Function to process events into projection
            from_event_id: Start processing from this event ID
            batch_size: Events per batch
            
        Returns:
            Final projection state
        """
        logger.info(f"Managing projection: {projection_name}")
        
        start_time = datetime.now(timezone.utc)
        events_processed = 0
        errors_count = 0
        
        # Get current projection state
        projection_state = self._projection_state_cache.get(projection_name)
        if not projection_state:
            projection_state = ProjectionState(
                projection_name=projection_name,
                last_processed_event_id=from_event_id or EventId(uuid4()),
                last_processed_timestamp=datetime.now(timezone.utc),
                version=1,
                event_count=0
            )
        
        try:
            # Process events in batches
            criteria = {
                "after_event_id": projection_state.last_processed_event_id,
                "limit": batch_size
            }
            
            async for chunk in self._create_event_stream(criteria, batch_size):
                batch_start = datetime.now(timezone.utc)
                
                for event in chunk.events:
                    try:
                        # Apply event to projection
                        await projection_builder(event)
                        projection_state.last_processed_event_id = event.id
                        projection_state.last_processed_timestamp = event.occurred_at
                        events_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing event {event.id} in projection {projection_name}: {str(e)}")
                        errors_count += 1
                
                batch_time = (datetime.now(timezone.utc) - batch_start).total_seconds()
                logger.debug(f"Processed batch of {len(chunk.events)} events in {batch_time:.2f}s")
            
            # Update final projection state
            total_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            projection_state.event_count += events_processed
            projection_state.errors_count += errors_count
            projection_state.processing_time_ms = total_time * 1000
            projection_state.throughput_events_per_second = events_processed / total_time if total_time > 0 else 0
            
            # Cache updated state
            self._projection_state_cache[projection_name] = projection_state
            
            logger.info(f"Projection {projection_name} updated: {events_processed} events, "
                       f"{errors_count} errors, {projection_state.throughput_events_per_second:.1f} events/sec")
            
            return projection_state
        
        except Exception as e:
            logger.error(f"Failed to manage projection {projection_name}: {str(e)}")
            raise
    
    async def optimize_event_storage(
        self,
        partition_strategy: PartitionStrategy = PartitionStrategy.TIME_BASED,
        shard_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Optimize event storage with partitioning and sharding strategies.
        
        Args:
            partition_strategy: Strategy for partitioning events
            shard_count: Number of shards for horizontal scaling
            
        Returns:
            Storage optimization results
        """
        logger.info(f"Optimizing event storage with {partition_strategy.value} partitioning")
        
        start_time = datetime.now(timezone.utc)
        results = {
            "partition_strategy": partition_strategy.value,
            "shard_count": shard_count,
            "partitions_created": [],
            "sharding_plan": {},
            "performance_improvement": {}
        }
        
        try:
            if partition_strategy == PartitionStrategy.TIME_BASED:
                # Create time-based partitions
                partitions = await self._create_time_partitions()
                results["partitions_created"] = partitions
                
            elif partition_strategy == PartitionStrategy.AGGREGATE_BASED:
                # Create aggregate-type-based partitions
                partitions = await self._create_aggregate_partitions()
                results["partitions_created"] = partitions
                
            elif partition_strategy == PartitionStrategy.CONTEXT_BASED:
                # Create context-based partitions (tenant/org isolation)
                partitions = await self._create_context_partitions()
                results["partitions_created"] = partitions
                
            elif partition_strategy == PartitionStrategy.HYBRID:
                # Combine multiple strategies
                time_partitions = await self._create_time_partitions()
                context_partitions = await self._create_context_partitions()
                results["partitions_created"] = time_partitions + context_partitions
            
            # Plan sharding if requested
            if shard_count and shard_count > 1:
                sharding_plan = await self._plan_event_sharding(shard_count)
                results["sharding_plan"] = sharding_plan
            
            # Estimate performance improvements
            results["performance_improvement"] = await self._estimate_performance_improvement(
                partition_strategy, shard_count
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            results["optimization_time_seconds"] = processing_time
            
            logger.info(f"Storage optimization completed in {processing_time:.2f}s")
            return results
        
        except Exception as e:
            logger.error(f"Failed to optimize event storage: {str(e)}")
            raise
    
    async def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get comprehensive optimization metrics and performance statistics."""
        return {
            "total_optimizations": len(self._metrics),
            "strategies_used": list(set(m.strategy.value for m in self._metrics)),
            "total_events_processed": sum(m.events_processed for m in self._metrics),
            "avg_throughput": sum(m.throughput_events_per_second for m in self._metrics) / len(self._metrics) if self._metrics else 0,
            "cache_stats": {
                "events_cached": len(self._event_cache),
                "snapshots_cached": len(self._snapshot_cache),
                "projections_cached": len(self._projection_state_cache)
            },
            "active_tasks": len(self._active_tasks),
            "memory_efficiency": {
                "avg_memory_usage_mb": sum(m.memory_usage_mb for m in self._metrics) / len(self._metrics) if self._metrics else 0,
                "cache_size_mb": self._cache_size_mb,
                "utilization_pct": (len(self._event_cache) * 0.001)  # Rough estimate
            },
            "recent_metrics": self._metrics[-10:] if self._metrics else []
        }
    
    async def _create_event_stream(
        self, 
        criteria: Dict[str, Any], 
        chunk_size: int
    ) -> AsyncGenerator[EventStreamChunk, None]:
        """Create a stream of event chunks based on criteria."""
        processed_count = 0
        
        while True:
            # Get next batch of events
            # This is a placeholder - in reality would use database cursors/pagination
            events = await self._get_events_batch(criteria, chunk_size, processed_count)
            
            if not events:
                break
            
            # Create chunk
            chunk = EventStreamChunk(
                events=events,
                chunk_id=f"chunk_{processed_count}_{processed_count + len(events)}",
                start_timestamp=min(event.occurred_at for event in events),
                end_timestamp=max(event.occurred_at for event in events),
                aggregate_types=set(event.aggregate_type for event in events),
                total_size_bytes=sum(len(json.dumps(event.event_data).encode('utf-8')) for event in events)
            )
            
            processed_count += len(events)
            yield chunk
    
    async def _get_events_batch(
        self, 
        criteria: Dict[str, Any], 
        limit: int, 
        offset: int
    ) -> List[DomainEvent]:
        """Get a batch of events from the repository."""
        # This is a placeholder implementation
        # In reality, would build dynamic queries based on criteria
        return await self._event_repository.get_recent_events(hours=24, limit=limit)
    
    async def _should_create_snapshot(
        self,
        aggregate_id: UUID,
        aggregate_type: str,
        strategy: SnapshotStrategy
    ) -> bool:
        """Determine if a snapshot should be created based on strategy."""
        cache_key = f"{aggregate_type}:{aggregate_id}"
        existing_snapshot = self._snapshot_cache.get(cache_key)
        
        if strategy == SnapshotStrategy.EVENT_COUNT:
            # Count events since last snapshot
            events = await self._event_repository.get_by_aggregate(aggregate_type, aggregate_id)
            events_since_snapshot = len(events)
            if existing_snapshot:
                events_since_snapshot = len([e for e in events if e.aggregate_version > existing_snapshot.aggregate_version])
            return events_since_snapshot >= self._snapshot_interval_events
        
        elif strategy == SnapshotStrategy.TIME_BASED:
            if not existing_snapshot:
                return True
            time_since_snapshot = datetime.now(timezone.utc) - existing_snapshot.created_at
            return time_since_snapshot >= timedelta(hours=self._snapshot_interval_hours)
        
        elif strategy == SnapshotStrategy.ADAPTIVE:
            # Use a combination of factors
            if not existing_snapshot:
                return True
            
            events = await self._event_repository.get_by_aggregate(aggregate_type, aggregate_id)
            events_since_snapshot = len([e for e in events if e.aggregate_version > existing_snapshot.aggregate_version])
            time_since_snapshot = datetime.now(timezone.utc) - existing_snapshot.created_at
            
            # Adaptive logic: create snapshot if either condition is met
            return (events_since_snapshot >= self._snapshot_interval_events // 2 or 
                    time_since_snapshot >= timedelta(hours=self._snapshot_interval_hours // 2))
        
        return False
    
    async def _build_aggregate_state(self, events: List[DomainEvent]) -> Dict[str, Any]:
        """Build aggregate state from events (placeholder implementation)."""
        # This would contain domain-specific logic to rebuild aggregate state
        # For now, return a simple summary
        return {
            "event_count": len(events),
            "last_event_type": events[-1].event_type.value if events else None,
            "first_event_at": events[0].occurred_at.isoformat() if events else None,
            "last_event_at": events[-1].occurred_at.isoformat() if events else None,
            "aggregate_version": max(event.aggregate_version for event in events) if events else 0,
            "event_types": list(set(event.event_type.value for event in events))
        }
    
    async def _analyze_query_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a query pattern for optimization opportunities."""
        analysis = {
            "high_volume": False,
            "multi_tenant": False,
            "time_range_queries": False,
            "aggregate_queries": False
        }
        
        # Detect high volume patterns
        if pattern.get("expected_results", 0) > 10000:
            analysis["high_volume"] = True
        
        # Detect multi-tenant patterns
        if "context_id" in pattern or "tenant_id" in pattern:
            analysis["multi_tenant"] = True
        
        # Detect time-based queries
        if any(key in pattern for key in ["occurred_at", "created_at", "from_date", "to_date"]):
            analysis["time_range_queries"] = True
        
        # Detect aggregate queries
        if any(key in pattern for key in ["aggregate_id", "aggregate_type"]):
            analysis["aggregate_queries"] = True
        
        return analysis
    
    async def _create_time_partitions(self) -> List[Dict[str, Any]]:
        """Create time-based partitions (placeholder)."""
        # In reality, would create actual database partitions
        return [
            {"name": "events_2024_01", "type": "monthly", "created": True},
            {"name": "events_2024_02", "type": "monthly", "created": True},
            {"name": "events_2024_03", "type": "monthly", "created": True}
        ]
    
    async def _create_aggregate_partitions(self) -> List[Dict[str, Any]]:
        """Create aggregate-type-based partitions (placeholder)."""
        return [
            {"name": "events_user", "type": "aggregate", "created": True},
            {"name": "events_organization", "type": "aggregate", "created": True},
            {"name": "events_order", "type": "aggregate", "created": True}
        ]
    
    async def _create_context_partitions(self) -> List[Dict[str, Any]]:
        """Create context-based partitions (placeholder)."""
        return [
            {"name": "events_tenant_001", "type": "context", "created": True},
            {"name": "events_tenant_002", "type": "context", "created": True}
        ]
    
    async def _plan_event_sharding(self, shard_count: int) -> Dict[str, Any]:
        """Plan event sharding across multiple databases."""
        return {
            "shard_count": shard_count,
            "sharding_key": "context_id",
            "distribution_strategy": "consistent_hashing",
            "estimated_events_per_shard": 1000000 // shard_count,
            "shards": [
                {"id": i, "database": f"events_shard_{i}", "weight": 1.0}
                for i in range(shard_count)
            ]
        }
    
    async def _estimate_performance_improvement(
        self,
        partition_strategy: PartitionStrategy,
        shard_count: Optional[int]
    ) -> Dict[str, Any]:
        """Estimate performance improvements from optimization."""
        base_improvement = 0.0
        
        if partition_strategy == PartitionStrategy.TIME_BASED:
            base_improvement += 0.4  # 40% improvement for time-based queries
        elif partition_strategy == PartitionStrategy.AGGREGATE_BASED:
            base_improvement += 0.3  # 30% improvement for aggregate queries
        elif partition_strategy == PartitionStrategy.CONTEXT_BASED:
            base_improvement += 0.5  # 50% improvement for multi-tenant scenarios
        elif partition_strategy == PartitionStrategy.HYBRID:
            base_improvement += 0.6  # 60% improvement for hybrid approach
        
        if shard_count and shard_count > 1:
            base_improvement += min(0.3 * (shard_count - 1), 0.8)  # Up to 80% improvement
        
        return {
            "query_performance_improvement_pct": min(base_improvement * 100, 90),
            "memory_usage_reduction_pct": min(base_improvement * 50, 60),
            "storage_efficiency_improvement_pct": min(base_improvement * 30, 40),
            "concurrent_access_improvement_pct": min(base_improvement * 70, 80) if shard_count else 0
        }
    
    def _estimate_chunk_memory_usage(self, chunk: EventStreamChunk) -> float:
        """Estimate memory usage of an event chunk in MB."""
        # Rough estimation based on chunk size and event data
        return chunk.total_size_bytes / (1024 * 1024) * 1.5  # Include overhead
    
    def __del__(self):
        """Cleanup thread pool on service destruction."""
        if hasattr(self, '_thread_pool'):
            self._thread_pool.shutdown(wait=False)