"""HTTP status code mapping for exceptions.

This module defines the mapping between exception types and
HTTP status codes for API responses.
"""

from .domain import *
from .infrastructure import *
from .database import *


# HTTP Status Code mapping for exceptions
HTTP_STATUS_MAP = {
    # 400 Bad Request
    RequiredFieldError: 400,
    InvalidFormatError: 400,
    ValueOutOfRangeError: 400,
    InvalidEnumValueError: 400,
    DatabaseValidationError: 400,
    InvalidSchemaError: 400,
    CacheKeyError: 400,
    InvalidRequestError: 400,
    UnsupportedAPIVersionError: 400,
    BusinessLogicError: 400,
    InvalidStateError: 400,
    
    # 401 Unauthorized
    AuthenticationError: 401,
    InvalidCredentialsError: 401,
    UserNotFoundError: 401,
    InvalidTokenError: 401,
    TokenExpiredError: 401,
    TokenMalformedError: 401,
    MFAInvalidError: 401,
    
    # 403 Forbidden
    AuthorizationError: 403,
    PermissionDeniedError: 403,
    InsufficientPermissionsError: 403,
    UserInactiveError: 403,
    TenantInactiveError: 403,
    TenantSuspendedError: 403,
    OrganizationInactiveError: 403,
    MFARequiredError: 403,
    
    # 404 Not Found
    ConnectionNotFoundError: 404,
    SchemaNotFoundError: 404,
    TenantNotFoundError: 404,
    OrganizationNotFoundError: 404,
    TeamNotFoundError: 404,
    RoleNotFoundError: 404,
    PermissionNotFoundError: 404,
    RealmNotFoundError: 404,
    ResourceNotFoundError: 404,
    
    # 409 Conflict
    ConflictError: 409,
    DuplicateResourceError: 409,
    
    # 422 Unprocessable Entity
    TenantProvisioningError: 422,
    
    # 429 Too Many Requests
    RateLimitError: 429,
    APIRateLimitError: 429,
    DatabaseRateLimitError: 429,
    TenantLimitExceededError: 429,
    
    # 500 Internal Server Error
    DatabaseError: 500,
    ConnectionError: 500,
    ConnectionUnhealthyError: 500,
    ConnectionPoolExhaustedError: 500,
    QueryError: 500,
    TransactionError: 500,
    SchemaError: 500,
    SchemaResolutionError: 500,
    SchemaCreationError: 500,
    CacheError: 500,
    CacheConnectionError: 500,
    CacheSerializationError: 500,
    CacheTimeoutError: 500,
    ExternalAuthError: 500,
    KeycloakError: 500,
    KeycloakConnectionError: 500,
    KeycloakConfigurationError: 500,
    KeycloakTokenError: 500,
    HealthCheckError: 500,
    MetricsError: 500,
    MonitoringError: 500,
    EncryptionError: 500,
    HashingError: 500,
    CryptographicError: 500,
    APIError: 500,
    RequestTimeoutError: 500,
    EventError: 500,
    EventPublishingError: 500,
    EventHandlingError: 500,
    MigrationError: 500,
    MigrationLockError: 500,
    MigrationRollbackError: 500,
    TenantConfigurationError: 500,
    DatabaseConfigurationError: 500,
    RoleAssignmentError: 500,
    TeamMembershipError: 500,
    EnvironmentError: 500,
    ServiceConfigurationError: 500,
    
    # 503 Service Unavailable
    ServiceUnavailableError: 503,
    DependencyUnavailableError: 503,
    
    # Default for NeoCommonsError
    NeoCommonsError: 500,
}