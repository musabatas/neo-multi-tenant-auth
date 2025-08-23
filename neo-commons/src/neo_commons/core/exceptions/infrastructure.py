"""Infrastructure-specific exceptions for neo-commons.

This module defines exceptions related to external systems,
infrastructure components, and technical concerns.
"""

from .base import NeoCommonsError


# Cache Errors
class CacheError(NeoCommonsError):
    """Base class for cache-related errors."""
    pass


class CacheConnectionError(CacheError):
    """Raised when cache connection fails."""
    pass


class CacheKeyError(CacheError):
    """Raised when cache key is invalid."""
    pass


class CacheSerializationError(CacheError):
    """Raised when cache value serialization/deserialization fails."""
    pass


class CacheTimeoutError(CacheError):
    """Raised when cache operation times out."""
    pass


# Keycloak/External Auth Errors
class ExternalAuthError(NeoCommonsError):
    """Base class for external authentication provider errors."""
    pass


class KeycloakError(ExternalAuthError):
    """Base class for Keycloak-related errors."""
    pass


class KeycloakConnectionError(KeycloakError):
    """Raised when Keycloak connection fails."""
    pass


class KeycloakConfigurationError(KeycloakError):
    """Raised when Keycloak configuration is invalid."""
    pass


class RealmNotFoundError(KeycloakError):
    """Raised when Keycloak realm is not found."""
    pass


class KeycloakTokenError(KeycloakError):
    """Raised when Keycloak token operation fails."""
    pass


# Validation Errors
class ValidationError(NeoCommonsError):
    """Raised when input validation fails."""
    pass


class RequiredFieldError(ValidationError):
    """Raised when required field is missing."""
    pass


class InvalidFormatError(ValidationError):
    """Raised when field format is invalid."""
    pass


class ValueOutOfRangeError(ValidationError):
    """Raised when value is outside allowed range."""
    pass


class InvalidEnumValueError(ValidationError):
    """Raised when enum value is invalid."""
    pass


# Rate Limiting Errors
class RateLimitError(NeoCommonsError):
    """Raised when rate limit is exceeded."""
    pass


class RateLimitExceededError(RateLimitError):
    """Raised when rate limit is exceeded."""
    pass


class APIRateLimitError(RateLimitError):
    """Raised when API rate limit is exceeded."""
    pass


class DatabaseRateLimitError(RateLimitError):
    """Raised when database rate limit is exceeded."""
    pass


# Health Check Errors
class HealthCheckError(NeoCommonsError):
    """Raised when health check fails."""
    pass


class ServiceUnavailableError(HealthCheckError):
    """Raised when service is unavailable."""
    pass


class DependencyUnavailableError(HealthCheckError):
    """Raised when external dependency is unavailable."""
    pass


# Metrics and Monitoring Errors
class MetricsError(NeoCommonsError):
    """Raised when metrics collection fails."""
    pass


class MonitoringError(NeoCommonsError):
    """Raised when monitoring operation fails."""
    pass


# Encryption/Security Errors
class SecurityError(NeoCommonsError):
    """Base class for security-related errors."""
    pass


class EncryptionError(SecurityError):
    """Raised when encryption/decryption fails."""
    pass


class HashingError(SecurityError):
    """Raised when password hashing fails."""
    pass


class CryptographicError(SecurityError):
    """Raised when cryptographic operation fails."""
    pass


# API Errors
class APIError(NeoCommonsError):
    """Base class for API-related errors."""
    pass


class UnsupportedAPIVersionError(APIError):
    """Raised when API version is not supported."""
    pass


class InvalidRequestError(APIError):
    """Raised when request format is invalid."""
    pass


class RequestTimeoutError(APIError):
    """Raised when request times out."""
    pass


# Event/Messaging Errors
class EventError(NeoCommonsError):
    """Raised when event publishing/handling fails."""
    pass


class EventPublishingError(EventError):
    """Raised when event publishing fails."""
    pass


class EventHandlingError(EventError):
    """Raised when event handling fails."""
    pass


# Migration Errors
class MigrationError(NeoCommonsError):
    """Raised when migration operation fails."""
    pass


class MigrationLockError(MigrationError):
    """Raised when migration lock cannot be acquired."""
    pass


class MigrationRollbackError(MigrationError):
    """Raised when migration rollback fails."""
    pass