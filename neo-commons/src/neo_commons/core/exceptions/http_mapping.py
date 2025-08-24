"""HTTP status code mapping for exceptions.

This module provides both static and configurable HTTP status code mapping,
allowing runtime customization of exception-to-status-code mappings
via ConfigurationProtocol while maintaining backward compatibility.
"""

from typing import Any, Dict, Optional, Type
from ..shared.application import ConfigurationProtocol
from .domain import *
from .infrastructure import *
from .database import *


# Static HTTP Status Code mapping for exceptions (backward compatibility)
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


class HttpStatusMapper:
    """Configuration-driven HTTP status code mapper for exceptions.
    
    This class allows runtime customization of exception-to-status-code mappings
    through ConfigurationProtocol, while providing sensible defaults.
    """
    
    def __init__(self, config: Optional[ConfigurationProtocol] = None):
        """Initialize with optional configuration provider.
        
        Args:
            config: Optional configuration provider for custom mappings
        """
        self._config = config
        self._cache: Dict[Type[Exception], int] = {}
    
    def get_status_code(self, exception: Exception) -> int:
        """Get HTTP status code for exception with configuration override.
        
        Args:
            exception: The exception instance
            
        Returns:
            HTTP status code (cached for performance)
        """
        exception_type = type(exception)
        
        # Check cache first
        if exception_type in self._cache:
            return self._cache[exception_type]
        
        # Try configuration override
        status_code = self._get_configured_status_code(exception_type)
        
        # Fall back to default mapping
        if status_code is None:
            status_code = HTTP_STATUS_MAP.get(exception_type, 500)
        
        # Cache the result
        self._cache[exception_type] = status_code
        return status_code
    
    def _get_configured_status_code(self, exception_type: Type[Exception]) -> Optional[int]:
        """Get status code from configuration.
        
        Args:
            exception_type: The exception class
            
        Returns:
            Configured status code or None if not configured
        """
        if not self._config:
            return None
        
        try:
            # Try exact class name match
            key = f"http_status_mapping.{exception_type.__name__}"
            status_code = self._config.get(key)
            if status_code is not None:
                return int(status_code)
            
            # Try parent class matches for inheritance-based overrides
            for base_class in exception_type.__mro__[1:]:  # Skip the class itself
                if base_class == Exception:
                    break
                key = f"http_status_mapping.{base_class.__name__}"
                status_code = self._config.get(key)
                if status_code is not None:
                    return int(status_code)
                    
        except (ValueError, TypeError):
            # Invalid configuration value, fall back to default
            pass
        
        return None
    
    def clear_cache(self) -> None:
        """Clear the status code cache.
        
        Call this when configuration changes to force re-evaluation
        of status code mappings.
        """
        self._cache.clear()
    
    def get_mapping_stats(self) -> Dict[str, Any]:
        """Get statistics about current mappings.
        
        Returns:
            Dictionary with mapping statistics
        """
        return {
            "cached_mappings": len(self._cache),
            "default_mappings": len(HTTP_STATUS_MAP),
            "has_config": self._config is not None,
            "cache_entries": {
                exc_type.__name__: status_code 
                for exc_type, status_code in self._cache.items()
            }
        }


# Global mapper instance
_global_mapper: Optional[HttpStatusMapper] = None


def get_mapper() -> HttpStatusMapper:
    """Get or create the global HTTP status mapper.
    
    Returns:
        Global HttpStatusMapper instance
    """
    global _global_mapper
    if _global_mapper is None:
        _global_mapper = HttpStatusMapper()
    return _global_mapper


def set_configuration_provider(config: ConfigurationProtocol) -> None:
    """Set the configuration provider for HTTP status mapping.
    
    Args:
        config: Configuration provider instance
    """
    global _global_mapper
    _global_mapper = HttpStatusMapper(config)


def get_http_status_code(exception: Exception) -> int:
    """Get HTTP status code for exception using configurable mapping.
    
    Args:
        exception: The exception instance
        
    Returns:
        HTTP status code
    """
    mapper = get_mapper()
    return mapper.get_status_code(exception)


def clear_mapping_cache() -> None:
    """Clear the HTTP status mapping cache.
    
    Call this when configuration changes to force re-evaluation.
    """
    mapper = get_mapper()
    mapper.clear_cache()


def get_mapping_statistics() -> Dict[str, Any]:
    """Get statistics about current HTTP status mappings.
    
    Returns:
        Dictionary with mapping statistics
    """
    mapper = get_mapper()
    return mapper.get_mapping_stats()


# Backward compatibility aliases
ConfigurableHttpStatusMapper = HttpStatusMapper
get_configurable_mapper = get_mapper