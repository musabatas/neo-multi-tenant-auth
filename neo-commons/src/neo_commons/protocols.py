"""
Central protocol interfaces for the NeoMultiTenant platform.

This module provides a centralized access point to all protocol-based interfaces
across the neo-commons library, enabling maximum flexibility and dependency injection
for platform services.
"""

# Utility protocols
from .utils.protocols import (
    TimestampProtocol,
    UUIDProtocol,
    EncryptionProtocol,
    MetadataProtocol
)

# Model protocols
from .models.protocols import (
    BaseModelProtocol,
    APIResponseProtocol,
    PaginationProtocol,
    PaginatedResponseProtocol,
    FilterableModelProtocol
)

# Exception protocols
from .exceptions.protocols import (
    ExceptionProtocol,
    DomainExceptionProtocol,
    ServiceExceptionProtocol,
    ExceptionHandlerProtocol,
    ValidationExceptionProtocol,
    ErrorReporterProtocol
)

# Service protocols
from .services.protocols import (
    BaseServiceProtocol,
    CRUDServiceProtocol,
    FilterableServiceProtocol,
    CacheableServiceProtocol,
    AuditableServiceProtocol,
    TenantAwareServiceProtocol,
    BatchServiceProtocol
)

# Repository protocols
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

# Domain protocols (authentication-specific, already exists)
from .domain.protocols.auth_protocols import (
    AuthServiceProtocol,
    PermissionServiceProtocol
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
    
    # Domain protocols
    "AuthServiceProtocol",
    "PermissionServiceProtocol"
]