"""Platform events infrastructure queues.

Message queue implementations for event processing and delivery.
Each queue provides different characteristics (reliability, persistence, performance).

Maximum separation architecture:
- redis_queue.py: ONLY Redis-backed queue (persistent, distributed)
- memory_queue.py: ONLY In-memory queue (fast, non-persistent) 
- priority_queue.py: ONLY Priority-based queue (ordered processing)

Pure platform infrastructure - used by all business features.
"""

# Redis Queue
from .redis_queue import (
    RedisEventQueue,
    create_redis_queue
)

# Memory Queue  
from .memory_queue import (
    MemoryEventQueue,
    create_memory_queue
)

# Priority Queue
from .priority_queue import (
    PriorityEventQueue,
    create_priority_queue
)

__all__ = [
    # Redis Queue
    "RedisEventQueue",
    "create_redis_queue",
    
    # Memory Queue
    "MemoryEventQueue", 
    "create_memory_queue",
    
    # Priority Queue
    "PriorityEventQueue",
    "create_priority_queue",
]