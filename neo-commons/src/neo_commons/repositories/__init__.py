"""
Neo Commons Repositories Package

This package contains reusable repository patterns for data access
in the NeoMultiTenant platform.

Components:
- Base: Abstract base repository with common database operations
"""

from .base import BaseRepository

__all__ = [
    "BaseRepository"
]