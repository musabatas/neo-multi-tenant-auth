"""
Neo-Commons: Enterprise-grade shared infrastructure library for NeoMultiTenant platform.

This package provides reusable infrastructure components implementing Clean Architecture
principles, protocol-based dependency injection, and enterprise-grade patterns.

Key Features:
- Protocol-based design with @runtime_checkable interfaces
- Sub-millisecond permission checks with intelligent caching
- Multi-tenant architecture with dynamic schema configuration
- Clean Architecture with proper layer separation
- Enterprise security with Keycloak integration
- 100% type coverage with Pydantic models
- Core domain entities and value objects
- Stable public API for consumers

Quick Start:
    # Use the public API for stable imports
    from neo_commons.public import (
        CheckPermission, CacheManager, generate_uuid_v7,
        User, Tenant, UserId, TenantId
    )
    
    # Or import directly from modules
    from neo_commons.auth.dependencies import CheckPermission
    from neo_commons.core.entities import User, Tenant
    from neo_commons.core.value_objects import UserId, TenantId, create_user_id

Architecture:
    - core/: Domain entities, value objects, and cross-cutting contracts
    - auth/: Authentication, authorization, and permission management
    - cache/: Redis-based caching with tenant isolation
    - database/: Connection management and utilities
    - middleware/: FastAPI middleware components
    - models/: Shared models and response patterns
    - services/: Base service patterns
    - repositories/: Data access patterns
    - public.py: Stable API for consumers
"""

__version__ = "0.1.0"
__author__ = "NeoMultiTenant Team"
__email__ = "dev@neomultitenant.com"

# Core domain module
from . import core

# Protocol interfaces for maximum flexibility and dependency injection
from . import protocols

# Repository patterns for data access layer
from .repositories.base import BaseRepository

# Models module exports
from .models.base import (
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
    SoftDeleteMixin,
    AuditMixin,
    StatusEnum,
    SortOrder,
    PaginationParams,
    PaginationMetadata,
    PaginatedResponse,
    APIResponse,
    HealthStatus,
    ServiceHealth,
    HealthCheckResponse,
)

# Exceptions module exports
from .exceptions.base import (
    NeoException,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    RateLimitError,
    ExternalServiceError,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    
    # Core domain module
    "core",
    
    # Protocol interfaces module
    "protocols",
    
    # Repository patterns
    "BaseRepository",
    
    # Base models
    "BaseSchema",
    "TimestampMixin",
    "UUIDMixin", 
    "SoftDeleteMixin",
    "AuditMixin",
    "StatusEnum",
    "SortOrder",
    "PaginationParams",
    "PaginationMetadata",
    "PaginatedResponse",
    "APIResponse",
    "HealthStatus",
    "ServiceHealth",
    "HealthCheckResponse",
    
    # Exceptions
    "NeoException",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "BadRequestError",
    "RateLimitError",
    "ExternalServiceError",
]