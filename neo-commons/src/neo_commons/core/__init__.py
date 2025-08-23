"""Core module for neo-commons.

Clean Core - Only exports exceptions and value objects.
Entities are accessed through features/, protocols through shared/.
"""

# Import from sub-modules - Clean Core approach
from .exceptions import *
from .value_objects import *

__all__ = [
    # Base Exception
    "NeoCommonsError",
    
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
    
    # Utility Functions
    "HTTP_STATUS_MAP",
    "get_http_status_code",
    "create_error_response",
    
    # Value Objects (Clean Core - these are immutable identifiers)
    "UserId",
    "TenantId", 
    "OrganizationId",
    "PermissionCode",
    "RoleCode",
]