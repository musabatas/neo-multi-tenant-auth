"""Exceptions module for neo-commons.

This module provides the complete exception hierarchy for neo-commons,
organized by domain concerns and infrastructure concerns.
"""

from .base import (
    NeoCommonsError,
    get_http_status_code,
    create_error_response,
)

# Aliases for backward compatibility
BaseNeoException = NeoCommonsError

from .domain import (
    # Configuration Errors
    ConfigurationError,
    EnvironmentError,
    ServiceConfigurationError,
    
    # Database Errors
    DatabaseError,
    ConnectionError,
    ConnectionNotFoundError,
    ConnectionUnhealthyError,
    ConnectionPoolExhaustedError,
    QueryError,
    TransactionError,
    
    # Schema Errors
    SchemaError,
    SchemaNotFoundError,
    SchemaResolutionError,
    InvalidSchemaError,
    SchemaCreationError,
    
    # Authentication Errors
    AuthenticationError,
    InvalidCredentialsError,
    UserNotFoundError,
    UserInactiveError,
    InvalidTokenError,
    TokenExpiredError,
    TokenMalformedError,
    MFARequiredError,
    MFAInvalidError,
    
    # Authorization Errors
    AuthorizationError,
    PermissionDeniedError,
    InsufficientPermissionsError,
    RoleNotFoundError,
    RoleAssignmentError,
    PermissionNotFoundError,
    
    # Tenant Errors
    TenantError,
    TenantNotFoundError,
    TenantInactiveError,
    TenantSuspendedError,
    TenantProvisioningError,
    TenantLimitExceededError,
    TenantConfigurationError,
    
    # Organization Errors
    OrganizationError,
    OrganizationNotFoundError,
    OrganizationInactiveError,
    
    # Team Errors
    TeamError,
    TeamNotFoundError,
    TeamMembershipError,
    
    # Business Logic Errors
    BusinessLogicError,
    DuplicateResourceError,
    ResourceNotFoundError,
    InvalidStateError,
    ConflictError,
)

from .database import (
    # Additional Database Errors
    ConnectionUnavailableError,
    ConnectionTimeoutError,
    ConnectionPoolError,
    HealthCheckFailedError,
    QueryTimeoutError,
    QuerySyntaxError,
    TransactionRollbackError,
    TransactionCommitError,
    MigrationNotFoundError,
    MigrationFailedError,
    RepositoryError,
    EntityNotFoundError,
    EntityAlreadyExistsError,
    ConcurrencyError,
    FailoverError,
    EncryptionError as DatabaseEncryptionError,
)

from .infrastructure import (
    # Cache Errors
    CacheError,
    CacheConnectionError,
    CacheKeyError,
    CacheSerializationError,
    CacheTimeoutError,
    
    # External Auth Errors
    ExternalAuthError,
    KeycloakError,
    KeycloakConnectionError,
    KeycloakConfigurationError,
    RealmNotFoundError,
    KeycloakTokenError,
    
    # Validation Errors
    ValidationError,
    RequiredFieldError,
    InvalidFormatError,
    ValueOutOfRangeError,
    InvalidEnumValueError,
    
    # Rate Limiting Errors
    RateLimitError,
    RateLimitExceededError,
    APIRateLimitError,
    DatabaseRateLimitError,
    
    # Health Check Errors
    HealthCheckError,
    ServiceUnavailableError,
    DependencyUnavailableError,
    
    # Metrics and Monitoring Errors
    MetricsError,
    MonitoringError,
    
    # Security Errors
    SecurityError,
    EncryptionError,
    HashingError,
    CryptographicError,
    
    # API Errors
    APIError,
    UnsupportedAPIVersionError,
    InvalidRequestError,
    RequestTimeoutError,
    
    # Event Errors
    EventError,
    EventPublishingError,
    EventHandlingError,
    
    # Migration Errors
    MigrationError,
    MigrationLockError,
    MigrationRollbackError,
)

from .http_mapping import HTTP_STATUS_MAP

__all__ = [
    # Base
    "NeoCommonsError",
    "BaseNeoException",  # Alias for backward compatibility
    "get_http_status_code",
    "create_error_response",
    
    # Configuration Errors
    "ConfigurationError",
    "EnvironmentError",
    "ServiceConfigurationError",
    
    # Database Errors
    "DatabaseError",
    "ConnectionError",
    "ConnectionNotFoundError",
    "ConnectionUnhealthyError",
    "ConnectionPoolExhaustedError",
    "QueryError",
    "TransactionError",
    "ConnectionUnavailableError",
    "ConnectionTimeoutError",
    "ConnectionPoolError",
    "HealthCheckFailedError",
    "QueryTimeoutError",
    "QuerySyntaxError",
    "TransactionRollbackError",
    "TransactionCommitError",
    "MigrationNotFoundError",
    "MigrationFailedError",
    "RepositoryError",
    "EntityNotFoundError",
    "EntityAlreadyExistsError",
    "ConcurrencyError",
    "FailoverError",
    "DatabaseEncryptionError",
    
    # Schema Errors
    "SchemaError",
    "SchemaNotFoundError",
    "SchemaResolutionError",
    "InvalidSchemaError",
    "SchemaCreationError",
    
    # Authentication Errors
    "AuthenticationError",
    "InvalidCredentialsError",
    "UserNotFoundError",
    "UserInactiveError",
    "InvalidTokenError",
    "TokenExpiredError",
    "TokenMalformedError",
    "MFARequiredError",
    "MFAInvalidError",
    
    # Authorization Errors
    "AuthorizationError",
    "PermissionDeniedError",
    "InsufficientPermissionsError",
    "RoleNotFoundError",
    "RoleAssignmentError",
    "PermissionNotFoundError",
    
    # Tenant Errors
    "TenantError",
    "TenantNotFoundError",
    "TenantInactiveError",
    "TenantSuspendedError",
    "TenantProvisioningError",
    "TenantLimitExceededError",
    "TenantConfigurationError",
    
    # Organization Errors
    "OrganizationError",
    "OrganizationNotFoundError",
    "OrganizationInactiveError",
    
    # Team Errors
    "TeamError",
    "TeamNotFoundError",
    "TeamMembershipError",
    
    # Cache Errors
    "CacheError",
    "CacheConnectionError",
    "CacheKeyError",
    "CacheSerializationError",
    "CacheTimeoutError",
    
    # External Auth Errors
    "ExternalAuthError",
    "KeycloakError",
    "KeycloakConnectionError",
    "KeycloakConfigurationError",
    "RealmNotFoundError",
    "KeycloakTokenError",
    
    # Validation Errors
    "ValidationError",
    "RequiredFieldError",
    "InvalidFormatError",
    "ValueOutOfRangeError",
    "InvalidEnumValueError",
    
    # Rate Limiting Errors
    "RateLimitError",
    "RateLimitExceededError",
    "APIRateLimitError",
    "DatabaseRateLimitError",
    
    # Health Check Errors
    "HealthCheckError",
    "ServiceUnavailableError",
    "DependencyUnavailableError",
    
    # Metrics and Monitoring Errors
    "MetricsError",
    "MonitoringError",
    
    # Security Errors
    "SecurityError",
    "EncryptionError",
    "HashingError",
    "CryptographicError",
    
    # Business Logic Errors
    "BusinessLogicError",
    "DuplicateResourceError",
    "ResourceNotFoundError",
    "InvalidStateError",
    "ConflictError",
    
    # API Errors
    "APIError",
    "UnsupportedAPIVersionError",
    "InvalidRequestError",
    "RequestTimeoutError",
    
    # Event Errors
    "EventError",
    "EventPublishingError",
    "EventHandlingError",
    
    # Migration Errors
    "MigrationError",
    "MigrationLockError",
    "MigrationRollbackError",
    
    # HTTP Status Mapping
    "HTTP_STATUS_MAP",
]