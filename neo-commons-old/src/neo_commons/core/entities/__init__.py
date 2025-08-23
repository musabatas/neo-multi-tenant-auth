"""
Core domain entities for the NeoMultiTenant platform.

This module provides immutable domain entities that represent the core
business concepts shared across all services. These entities enforce
business rules and maintain consistency across the platform.

Design Principles:
- Immutable by default (frozen dataclasses)
- Type-safe with value objects
- Self-validating with clear error messages
- Rich domain behavior methods
"""

from .user import User
from .tenant import Tenant
from .organization import Organization

__all__ = [
    "User",
    "Tenant", 
    "Organization",
]