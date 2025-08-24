"""Performance metrics persistence with async background storage.

Provides optional database persistence for performance metrics without impacting
the performance of monitored operations through async background processing.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Protocol
from datetime import datetime

from .performance import PerformanceMetric, PerformanceStats, PerformanceLevel


logger = logging.getLogger(__name__)


class PerformanceStorage(Protocol):
    """Protocol for performance metrics storage backends."""
    
    async def store_metrics(self, metrics: List[PerformanceMetric]) -> bool:
        """Store metrics to persistent storage."""
        ...
    
    async def store_stats(self, stats: Dict[str, PerformanceStats]) -> bool:
        """Store aggregated statistics to persistent storage."""
        ...
    
    async def get_metrics(
        self, 
        operation_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """Retrieve metrics from storage."""
        ...
    
    async def cleanup_old_metrics(self, older_than_days: int = 30) -> int:
        """Clean up old metrics and return count of deleted records."""
        ...


class DatabasePerformanceStorage:
    """Database storage implementation for performance metrics."""
    
    def __init__(self, database_service, schema: str = "admin"):
        """Initialize with database service and schema."""
        self.database_service = database_service
        self.schema = schema
        self._initialized = False
    
    async def _ensure_tables(self) -> None:
        """Ensure performance metrics tables exist."""
        if self._initialized:
            return
        
        create_metrics_table = f"""
        CREATE TABLE IF NOT EXISTS {self.schema}.performance_metrics (
            id SERIAL PRIMARY KEY,
            operation_name VARCHAR(255) NOT NULL,
            execution_time_ms DECIMAL(10,3) NOT NULL,
            level VARCHAR(20) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB DEFAULT '{{}}',
            exceeded_threshold BOOLEAN DEFAULT FALSE,
            error_occurred BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation 
            ON {self.schema}.performance_metrics(operation_name);
        CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp 
            ON {self.schema}.performance_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_performance_metrics_level 
            ON {self.schema}.performance_metrics(level);
        CREATE INDEX IF NOT EXISTS idx_performance_metrics_threshold 
            ON {self.schema}.performance_metrics(exceeded_threshold) WHERE exceeded_threshold = TRUE;
        """
        
        create_stats_table = f"""
        CREATE TABLE IF NOT EXISTS {self.schema}.performance_stats (
            operation_name VARCHAR(255) PRIMARY KEY,
            call_count INTEGER NOT NULL DEFAULT 0,
            total_time_ms DECIMAL(12,3) NOT NULL DEFAULT 0,
            avg_time_ms DECIMAL(10,3) NOT NULL DEFAULT 0,
            min_time_ms DECIMAL(10,3) NOT NULL DEFAULT 0,
            max_time_ms DECIMAL(10,3) NOT NULL DEFAULT 0,
            threshold_violations INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            last_updated TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_performance_stats_avg_time 
            ON {self.schema}.performance_stats(avg_time_ms DESC);
        """
        
        try:
            async with self.database_service.get_connection("admin") as conn:
                await conn.execute(create_metrics_table)
                await conn.execute(create_stats_table)
            
            self._initialized = True
            logger.info(f"Performance metrics tables ensured in schema {self.schema}")
            
        except Exception as e:
            logger.error(f"Failed to create performance metrics tables: {e}")
            raise
    
    async def store_metrics(self, metrics: List[PerformanceMetric]) -> bool:
        """Store metrics to database with batch insert."""
        if not metrics:
            return True
            
        await self._ensure_tables()
        
        try:
            insert_query = f"""
            INSERT INTO {self.schema}.performance_metrics 
            (operation_name, execution_time_ms, level, timestamp, metadata, exceeded_threshold, error_occurred)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            async with self.database_service.get_connection("admin") as conn:
                for metric in metrics:
                    await conn.execute(
                        insert_query,
                        metric.operation_name,
                        metric.execution_time_ms,
                        metric.level.value,
                        metric.timestamp,
                        metric.metadata,
                        metric.exceeded_threshold,
                        metric.error_occurred
                    )
            
            logger.debug(f"Stored {len(metrics)} performance metrics to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {e}")
            return False
    
    async def store_stats(self, stats: Dict[str, PerformanceStats]) -> bool:
        """Store aggregated statistics with upsert."""
        if not stats:
            return True
            
        await self._ensure_tables()
        
        try:
            upsert_query = f"""
            INSERT INTO {self.schema}.performance_stats 
            (operation_name, call_count, total_time_ms, avg_time_ms, min_time_ms, 
             max_time_ms, threshold_violations, error_count, last_updated)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT (operation_name) DO UPDATE SET
                call_count = EXCLUDED.call_count,
                total_time_ms = EXCLUDED.total_time_ms,
                avg_time_ms = EXCLUDED.avg_time_ms,
                min_time_ms = LEAST(performance_stats.min_time_ms, EXCLUDED.min_time_ms),
                max_time_ms = GREATEST(performance_stats.max_time_ms, EXCLUDED.max_time_ms),
                threshold_violations = EXCLUDED.threshold_violations,
                error_count = EXCLUDED.error_count,
                last_updated = NOW()
            """
            
            async with self.database_service.get_connection("admin") as conn:
                for stat in stats.values():
                    await conn.execute(
                        upsert_query,
                        stat.operation_name,
                        stat.call_count,
                        stat.total_time_ms,
                        stat.avg_time_ms,
                        stat.min_time_ms,
                        stat.max_time_ms,
                        stat.threshold_violations,
                        stat.error_count
                    )
            
            logger.debug(f"Stored {len(stats)} performance statistics to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store performance statistics: {e}")
            return False
    
    async def get_metrics(
        self, 
        operation_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """Retrieve metrics from database."""
        await self._ensure_tables()
        
        try:
            conditions = []
            params = []
            param_count = 0
            
            if operation_name:
                param_count += 1
                conditions.append(f"operation_name = ${param_count}")
                params.append(operation_name)
            
            if start_time:
                param_count += 1
                conditions.append(f"timestamp >= ${param_count}")
                params.append(start_time)
            
            if end_time:
                param_count += 1
                conditions.append(f"timestamp <= ${param_count}")
                params.append(end_time)
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            param_count += 1
            
            query = f"""
            SELECT operation_name, execution_time_ms, level, timestamp, metadata, 
                   exceeded_threshold, error_occurred
            FROM {self.schema}.performance_metrics
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_count}
            """
            params.append(limit)
            
            async with self.database_service.get_connection("admin") as conn:
                rows = await conn.fetch(query, *params)
                
                metrics = []
                for row in rows:
                    metrics.append(PerformanceMetric(
                        operation_name=row['operation_name'],
                        execution_time_ms=float(row['execution_time_ms']),
                        level=PerformanceLevel(row['level']),
                        timestamp=row['timestamp'],
                        metadata=row['metadata'] or {},
                        exceeded_threshold=row['exceeded_threshold'],
                        error_occurred=row['error_occurred']
                    ))
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to retrieve performance metrics: {e}")
            return []
    
    async def cleanup_old_metrics(self, older_than_days: int = 30) -> int:
        """Clean up old metrics and return count of deleted records."""
        await self._ensure_tables()
        
        try:
            cleanup_query = f"""
            DELETE FROM {self.schema}.performance_metrics
            WHERE timestamp < NOW() - INTERVAL '{older_than_days} days'
            """
            
            async with self.database_service.get_connection("admin") as conn:
                result = await conn.execute(cleanup_query)
                # Extract count from result (e.g., "DELETE 123" -> 123)
                deleted_count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old performance metrics (older than {older_than_days} days)")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old performance metrics: {e}")
            return 0


class BackgroundMetricsPersister:
    """Background processor for async metrics persistence."""
    
    def __init__(self, storage: PerformanceStorage, batch_size: int = 100, flush_interval: float = 30.0):
        """Initialize background persister with storage backend."""
        self.storage = storage
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._metrics_queue: asyncio.Queue = asyncio.Queue()
        self._stats_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._logger = logging.getLogger(f"{__name__}.BackgroundMetricsPersister")
    
    def start(self) -> None:
        """Start background persistence task."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._persistence_loop())
        self._logger.info("Started background metrics persistence")
    
    async def stop(self) -> None:
        """Stop background persistence and flush remaining metrics."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            await self._task
        
        # Flush any remaining metrics
        await self._flush_all()
        self._logger.info("Stopped background metrics persistence")
    
    def queue_metric(self, metric: PerformanceMetric) -> None:
        """Queue metric for background persistence (non-blocking)."""
        if not self._running:
            return
        
        try:
            self._metrics_queue.put_nowait(metric)
        except asyncio.QueueFull:
            self._logger.warning("Metrics queue full, dropping metric")
    
    def queue_stats(self, stats: Dict[str, PerformanceStats]) -> None:
        """Queue stats for background persistence (non-blocking)."""
        if not self._running:
            return
        
        try:
            self._stats_queue.put_nowait(stats.copy())
        except asyncio.QueueFull:
            self._logger.warning("Stats queue full, dropping stats")
    
    async def _persistence_loop(self) -> None:
        """Main background persistence loop."""
        try:
            while self._running:
                await asyncio.sleep(self.flush_interval)
                await self._flush_all()
        except Exception as e:
            self._logger.error(f"Persistence loop error: {e}")
    
    async def _flush_all(self) -> None:
        """Flush all queued metrics and stats."""
        # Flush metrics
        metrics_batch = []
        try:
            while len(metrics_batch) < self.batch_size:
                metric = self._metrics_queue.get_nowait()
                metrics_batch.append(metric)
        except asyncio.QueueEmpty:
            pass
        
        if metrics_batch:
            try:
                await self.storage.store_metrics(metrics_batch)
            except Exception as e:
                self._logger.error(f"Failed to flush metrics batch: {e}")
        
        # Flush stats (latest stats override previous)
        latest_stats = None
        try:
            while True:
                latest_stats = self._stats_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        
        if latest_stats:
            try:
                await self.storage.store_stats(latest_stats)
            except Exception as e:
                self._logger.error(f"Failed to flush stats: {e}")