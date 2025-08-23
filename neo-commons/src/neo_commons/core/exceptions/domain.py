"""Domain-specific exceptions for neo-commons.

This module defines domain-specific exceptions that relate to
business logic and domain concepts.
"""

from .base import NeoCommonsError


# Configuration Errors
class ConfigurationError(NeoCommonsError):
    """Raised when there's a configuration issue."""
    pass


class EnvironmentError(ConfigurationError):
    """Raised when environment variables are missing or invalid."""
    pass


class ServiceConfigurationError(ConfigurationError):
    """Raised when service-specific configuration is invalid."""
    pass


# Database Errors
class DatabaseError(NeoCommonsError):
    """Base class for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class ConnectionNotFoundError(DatabaseError):
    """Raised when a database connection configuration is not found."""
    pass


class ConnectionUnhealthyError(DatabaseError):
    """Raised when attempting to use an unhealthy database connection."""
    pass


class ConnectionPoolExhaustedError(DatabaseError):
    """Raised when database connection pool is exhausted."""
    pass


class QueryError(DatabaseError):
    """Raised when database query execution fails."""
    pass


class TransactionError(DatabaseError):
    """Raised when database transaction fails."""
    pass


# Schema Errors
class SchemaError(DatabaseError):
    """Base class for schema-related errors."""
    pass


class SchemaNotFoundError(SchemaError):
    """Raised when a database schema is not found."""
    pass


class SchemaResolutionError(SchemaError):
    """Raised when schema resolution fails."""
    pass


class InvalidSchemaError(SchemaError):
    """Raised when schema name is invalid or potentially dangerous."""
    pass


class SchemaCreationError(SchemaError):
    """Raised when schema creation fails."""
    pass


# Authentication Errors
class AuthenticationError(NeoCommonsError):
    """Base class for authentication-related errors."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid."""
    pass


class UserNotFoundError(AuthenticationError):
    """Raised when user is not found."""
    pass


class UserInactiveError(AuthenticationError):
    """Raised when user account is inactive."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    pass


class TokenMalformedError(AuthenticationError):
    """Raised when JWT token is malformed."""
    pass


class MFARequiredError(AuthenticationError):
    """Raised when multi-factor authentication is required."""
    pass


class MFAInvalidError(AuthenticationError):
    """Raised when MFA code is invalid."""
    pass


# Authorization Errors
class AuthorizationError(NeoCommonsError):
    """Base class for authorization-related errors."""
    pass


class PermissionDeniedError(AuthorizationError):
    """Raised when user lacks required permissions."""
    pass


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user has some but not all required permissions."""
    pass


class RoleNotFoundError(AuthorizationError):
    """Raised when role is not found."""
    pass


class RoleAssignmentError(AuthorizationError):
    """Raised when role assignment fails."""
    pass


class PermissionNotFoundError(AuthorizationError):
    """Raised when permission is not found."""
    pass


# Tenant Errors
class TenantError(NeoCommonsError):
    """Base class for tenant-related errors."""
    pass


class TenantNotFoundError(TenantError):
    """Raised when tenant is not found."""
    pass


class TenantInactiveError(TenantError):
    """Raised when tenant is inactive."""
    pass


class TenantSuspendedError(TenantError):
    """Raised when tenant is suspended."""
    pass


class TenantProvisioningError(TenantError):
    """Raised when tenant is still being provisioned."""
    pass


class TenantLimitExceededError(TenantError):
    """Raised when tenant has exceeded their limits."""
    pass


class TenantConfigurationError(TenantError):
    """Raised when tenant configuration is invalid."""
    pass


# Organization Errors
class OrganizationError(NeoCommonsError):
    """Base class for organization-related errors."""
    pass


class OrganizationNotFoundError(OrganizationError):
    """Raised when organization is not found."""
    pass


class OrganizationInactiveError(OrganizationError):
    """Raised when organization is inactive."""
    pass


# Team Errors
class TeamError(NeoCommonsError):
    """Base class for team-related errors."""
    pass


class TeamNotFoundError(TeamError):
    """Raised when team is not found."""
    pass


class TeamMembershipError(TeamError):
    """Raised when team membership operation fails."""
    pass


# Business Logic Errors
class BusinessLogicError(NeoCommonsError):
    """Raised when business logic validation fails."""
    pass


class DuplicateResourceError(BusinessLogicError):
    """Raised when attempting to create duplicate resource."""
    pass


class ResourceNotFoundError(BusinessLogicError):
    """Raised when required resource is not found."""
    pass


class InvalidStateError(BusinessLogicError):
    """Raised when operation is invalid in current state."""
    pass


class ConflictError(BusinessLogicError):
    """Raised when operation conflicts with existing data."""
    pass