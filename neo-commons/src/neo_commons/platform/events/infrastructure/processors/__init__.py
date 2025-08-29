"""Event processor implementations.

This module contains concrete implementations of event processors
for consuming and handling events from message queues.
"""

from .redis_event_processor import RedisEventProcessor

__all__ = [
    "RedisEventProcessor",
]