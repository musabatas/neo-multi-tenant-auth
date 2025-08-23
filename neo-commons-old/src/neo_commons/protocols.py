"""
Central protocol interfaces for the NeoMultiTenant platform.

This module provides a centralized access point to all protocol-based interfaces
across the neo-commons library, enabling maximum flexibility and dependency injection
for platform services.

Protocol Organization:
    ============ Authentication & Authorization ============
    - AuthenticationProvider: Token validation and user authentication
    - PermissionChecker: Permission validation with caching
    - TokenValidator: JWT token parsing and validation
    - RealmProvider: Multi-tenant realm management

    ============ Caching & Performance ============  
    - CacheProvider: Generic caching interface
    - TenantAwareCache: Multi-tenant cache isolation
    - CacheManager: High-level cache orchestration

    ============ Data Persistence ============
    - Repository: Data access patterns
    - ConnectionProvider: Database connection management
    - SchemaProvider: Dynamic schema configuration

    ============ Service Layer ============
    - BaseService: Common service functionality
    - CRUDService: Create, read, update, delete operations
    - AuditableService: Change tracking and audit logs

    ============ Domain & Business Logic ============
    - Entity: Domain entity contracts
    - ValueObject: Immutable value types
    - DomainEvent: Event-driven architecture

Usage Patterns:
    # Dependency injection with protocols
    from neo_commons.protocols import PermissionChecker
    
    class UserService:
        def __init__(self, permission_checker: PermissionChecker):
            self._permission_checker = permission_checker
    
    # Runtime checking
    from neo_commons.protocols import CacheProvider
    
    def setup_cache(cache: CacheProvider):
        assert isinstance(cache, CacheProvider)
        return cache

Protocol Benefits:
    - Type safety with runtime checking
    - Easy testing with mock implementations
    - Flexible dependency injection
    - Clear architectural boundaries
    - Support for multiple implementations
"""

# ============ Utility Protocols ============
from .utils.protocols import (
    TimestampProtocol,
    UUIDProtocol,
    EncryptionProtocol,
    MetadataProtocol
)

# ============ Model Protocols ============
from .models.protocols import (
    BaseModelProtocol,
    APIResponseProtocol,
    PaginationProtocol,
    PaginatedResponseProtocol,
    FilterableModelProtocol
)

# ============ Exception Protocols ============
from .exceptions.protocols import (
    ExceptionProtocol,
    DomainExceptionProtocol,
    ServiceExceptionProtocol,
    ExceptionHandlerProtocol,
    ValidationExceptionProtocol,
    ErrorReporterProtocol
)

# ============ Service Protocols ============
from .services.protocols import (
    BaseServiceProtocol,
    CRUDServiceProtocol,
    FilterableServiceProtocol,
    CacheableServiceProtocol,
    AuditableServiceProtocol,
    TenantAwareServiceProtocol,
    BatchServiceProtocol
)

# ============ Repository Protocols ============
from .repositories.protocols import (
    RepositoryProtocol,
    SchemaProvider,
    ConnectionProvider,
    CacheableRepositoryProtocol,
    AuditableRepositoryProtocol,
    TenantAwareRepositoryProtocol,
    CRUDRepositoryProtocol,
    FilterableRepositoryProtocol
)

__all__ = [
    # Utility protocols
    "TimestampProtocol",
    "UUIDProtocol", 
    "EncryptionProtocol",
    "MetadataProtocol",
    
    # Model protocols
    "BaseModelProtocol",
    "APIResponseProtocol",
    "PaginationProtocol",
    "PaginatedResponseProtocol",
    "FilterableModelProtocol",
    
    # Exception protocols
    "ExceptionProtocol",
    "DomainExceptionProtocol",
    "ServiceExceptionProtocol",
    "ExceptionHandlerProtocol",
    "ValidationExceptionProtocol",
    "ErrorReporterProtocol",
    
    # Service protocols
    "BaseServiceProtocol",
    "CRUDServiceProtocol",
    "FilterableServiceProtocol",
    "CacheableServiceProtocol",
    "AuditableServiceProtocol",
    "TenantAwareServiceProtocol",
    "BatchServiceProtocol",
    
    # Repository protocols
    "RepositoryProtocol",
    "SchemaProvider",
    "ConnectionProvider",
    "CacheableRepositoryProtocol",
    "AuditableRepositoryProtocol",
    "TenantAwareRepositoryProtocol",
    "CRUDRepositoryProtocol",
    "FilterableRepositoryProtocol",
]