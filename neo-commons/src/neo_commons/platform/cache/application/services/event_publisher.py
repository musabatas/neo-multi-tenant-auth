"""Cache event publishing service.

ONLY event publishing - publishes cache domain events for monitoring,
analytics, and distributed cache coordination.

Following maximum separation architecture - one file = one purpose.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass

from ...core.events.cache_hit import CacheHit
from ...core.events.cache_miss import CacheMiss
from ...core.events.cache_invalidated import CacheInvalidated
from ...core.events.cache_expired import CacheExpired
from ...core.value_objects.cache_key import CacheKey
from ...core.entities.cache_namespace import CacheNamespace


class EventPublisher(Protocol):
    """Event publisher protocol for external event systems."""
    
    async def publish(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Publish event to external system."""
        ...


@dataclass
class EventMetrics:
    """Event publishing metrics."""
    total_published: int = 0
    successful_publishes: int = 0
    failed_publishes: int = 0
    last_publish_time: Optional[datetime] = None
    last_error: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_published == 0:
            return 0.0
        return (self.successful_publishes / self.total_published) * 100.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_published == 0:
            return 0.0
        return (self.failed_publishes / self.total_published) * 100.0


class CacheEventPublisher:
    """Cache event publishing service.
    
    Publishes cache domain events for monitoring, analytics, and distributed
    cache coordination. Handles event batching, retry logic, and metrics.
    """
    
    def __init__(
        self,
        event_publisher: Optional[EventPublisher] = None,
        batch_size: int = 100,
        flush_interval_seconds: int = 30,
        enable_metrics: bool = True
    ):
        """Initialize cache event publisher.
        
        Args:
            event_publisher: External event publisher implementation
            batch_size: Number of events to batch before publishing
            flush_interval_seconds: Interval to flush batched events
            enable_metrics: Whether to track publishing metrics
        """
        self._event_publisher = event_publisher
        self._batch_size = batch_size
        self._flush_interval = flush_interval_seconds
        self._enable_metrics = enable_metrics
        
        # Event batching
        self._event_batch: List[Dict[str, Any]] = []
        self._batch_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._metrics = EventMetrics() if enable_metrics else None
        
        # Start batch flushing if publisher is available
        if self._event_publisher and self._flush_interval > 0:
            self._start_batch_flushing()
    
    def _start_batch_flushing(self) -> None:
        """Start periodic batch flushing task."""
        if not self._flush_task or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def _periodic_flush(self) -> None:
        """Periodically flush event batch."""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self.flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._metrics:
                    self._metrics.last_error = str(e)
    
    async def publish_cache_hit(
        self,
        key: CacheKey,
        namespace: CacheNamespace,
        lookup_time_ms: float,
        value_size_bytes: int,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        entry_age_seconds: Optional[int] = None,
        access_count: Optional[int] = None,
        ttl_remaining_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish cache hit event.
        
        Args:
            key: Cache key that was hit
            namespace: Cache namespace
            lookup_time_ms: Time taken for lookup in milliseconds
            value_size_bytes: Size of cached value in bytes
            request_id: Optional request identifier
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            entry_age_seconds: Age of cache entry in seconds
            access_count: Number of times entry has been accessed
            ttl_remaining_seconds: Remaining TTL in seconds
            metadata: Additional metadata
            
        Returns:
            True if event was published successfully
        """
        event = CacheHit(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            key=key,
            namespace=namespace,
            lookup_time_ms=lookup_time_ms,
            value_size_bytes=value_size_bytes,
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            entry_age_seconds=entry_age_seconds,
            access_count=access_count,
            ttl_remaining_seconds=ttl_remaining_seconds,
            metadata=metadata
        )
        
        return await self._publish_event(event.to_dict())
    
    async def publish_cache_miss(
        self,
        key: CacheKey,
        namespace: CacheNamespace,
        lookup_time_ms: float,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        reason: str = "not_found",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish cache miss event.
        
        Args:
            key: Cache key that was missed
            namespace: Cache namespace
            lookup_time_ms: Time taken for lookup in milliseconds
            request_id: Optional request identifier
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            reason: Reason for cache miss (not_found, expired, invalid)
            metadata: Additional metadata
            
        Returns:
            True if event was published successfully
        """
        event = CacheMiss(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            key=key,
            namespace=namespace,
            lookup_time_ms=lookup_time_ms,
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            reason=reason,
            metadata=metadata
        )
        
        return await self._publish_event(event.to_dict())
    
    async def publish_cache_invalidated(
        self,
        key: CacheKey,
        namespace: CacheNamespace,
        invalidation_reason: str,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish cache invalidated event.
        
        Args:
            key: Cache key that was invalidated
            namespace: Cache namespace
            invalidation_reason: Reason for invalidation
            request_id: Optional request identifier
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            metadata: Additional metadata
            
        Returns:
            True if event was published successfully
        """
        event = CacheInvalidated(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            key=key,
            namespace=namespace,
            invalidation_reason=invalidation_reason,
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            metadata=metadata
        )
        
        return await self._publish_event(event.to_dict())
    
    async def publish_cache_expired(
        self,
        key: CacheKey,
        namespace: CacheNamespace,
        ttl_seconds: int,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish cache expired event.
        
        Args:
            key: Cache key that expired
            namespace: Cache namespace
            ttl_seconds: Original TTL in seconds
            request_id: Optional request identifier
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            metadata: Additional metadata
            
        Returns:
            True if event was published successfully
        """
        event = CacheExpired(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            key=key,
            namespace=namespace,
            ttl_seconds=ttl_seconds,
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            metadata=metadata
        )
        
        return await self._publish_event(event.to_dict())
    
    async def _publish_event(self, event_data: Dict[str, Any]) -> bool:
        """Publish individual event.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if event was published successfully
        """
        if not self._event_publisher:
            # No publisher configured - silent success
            return True
        
        try:
            # Add to batch if batching is enabled
            if self._batch_size > 1:
                async with self._batch_lock:
                    self._event_batch.append(event_data)
                    
                    # Flush batch if it's full
                    if len(self._event_batch) >= self._batch_size:
                        return await self._flush_batch_unsafe()
                
                return True
            else:
                # Publish immediately
                success = await self._event_publisher.publish(
                    event_data.get("event_type", "unknown"),
                    event_data
                )
                
                if self._metrics:
                    self._metrics.total_published += 1
                    if success:
                        self._metrics.successful_publishes += 1
                    else:
                        self._metrics.failed_publishes += 1
                    self._metrics.last_publish_time = datetime.now(timezone.utc)
                
                return success
        
        except Exception as e:
            if self._metrics:
                self._metrics.total_published += 1
                self._metrics.failed_publishes += 1
                self._metrics.last_error = str(e)
                self._metrics.last_publish_time = datetime.now(timezone.utc)
            
            return False
    
    async def flush_batch(self) -> bool:
        """Flush current event batch.
        
        Returns:
            True if batch was flushed successfully
        """
        async with self._batch_lock:
            return await self._flush_batch_unsafe()
    
    async def _flush_batch_unsafe(self) -> bool:
        """Flush batch without acquiring lock (internal use).
        
        Returns:
            True if batch was flushed successfully
        """
        if not self._event_batch or not self._event_publisher:
            return True
        
        try:
            # Publish all events in batch
            batch_events = self._event_batch.copy()
            self._event_batch.clear()
            
            success_count = 0
            for event_data in batch_events:
                success = await self._event_publisher.publish(
                    event_data.get("event_type", "unknown"),
                    event_data
                )
                if success:
                    success_count += 1
            
            # Update metrics
            if self._metrics:
                batch_size = len(batch_events)
                self._metrics.total_published += batch_size
                self._metrics.successful_publishes += success_count
                self._metrics.failed_publishes += (batch_size - success_count)
                self._metrics.last_publish_time = datetime.now(timezone.utc)
            
            return success_count == len(batch_events)
        
        except Exception as e:
            if self._metrics:
                batch_size = len(self._event_batch)
                self._metrics.total_published += batch_size
                self._metrics.failed_publishes += batch_size
                self._metrics.last_error = str(e)
                self._metrics.last_publish_time = datetime.now(timezone.utc)
            
            self._event_batch.clear()
            return False
    
    async def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get event publishing metrics.
        
        Returns:
            Metrics dictionary or None if metrics disabled
        """
        if not self._metrics:
            return None
        
        return {
            "total_published": self._metrics.total_published,
            "successful_publishes": self._metrics.successful_publishes,
            "failed_publishes": self._metrics.failed_publishes,
            "success_rate_percentage": self._metrics.success_rate,
            "failure_rate_percentage": self._metrics.failure_rate,
            "last_publish_time": self._metrics.last_publish_time.isoformat() if self._metrics.last_publish_time else None,
            "last_error": self._metrics.last_error,
            "current_batch_size": len(self._event_batch),
            "batch_size_limit": self._batch_size,
            "flush_interval_seconds": self._flush_interval
        }
    
    async def close(self) -> None:
        """Close event publisher and flush remaining events."""
        # Cancel periodic flush task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        await self.flush_batch()


# Factory function for dependency injection
def create_cache_event_publisher(
    event_publisher: Optional[EventPublisher] = None,
    batch_size: int = 100,
    flush_interval_seconds: int = 30,
    enable_metrics: bool = True
) -> CacheEventPublisher:
    """Create cache event publisher with dependencies.
    
    Args:
        event_publisher: External event publisher implementation
        batch_size: Number of events to batch before publishing
        flush_interval_seconds: Interval to flush batched events
        enable_metrics: Whether to track publishing metrics
        
    Returns:
        Configured cache event publisher instance
    """
    return CacheEventPublisher(
        event_publisher=event_publisher,
        batch_size=batch_size,
        flush_interval_seconds=flush_interval_seconds,
        enable_metrics=enable_metrics
    )