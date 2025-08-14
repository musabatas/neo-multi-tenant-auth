"""
Neo Commons Services Package

This package contains reusable service patterns for business logic
in the NeoMultiTenant platform.

Components:
- Base: Abstract base service with common business logic patterns
"""

from .base import BaseService

__all__ = [
    "BaseService"
]