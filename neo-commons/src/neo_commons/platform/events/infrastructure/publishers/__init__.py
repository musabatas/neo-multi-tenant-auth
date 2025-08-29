"""Event publisher implementations.

This module contains concrete implementations of event publishers
following the Maximum Separation Architecture principle.
"""

from .redis_event_publisher import RedisEventPublisher

__all__ = [
    "RedisEventPublisher",
]