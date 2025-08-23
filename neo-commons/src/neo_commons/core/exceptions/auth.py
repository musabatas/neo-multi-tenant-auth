"""Authentication-specific exceptions for neo-commons."""

from .base import NeoCommonsError


class AuthenticationError(NeoCommonsError):
    """Base exception for authentication errors."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""
    pass


class RealmNotFoundError(AuthenticationError):
    """Raised when a Keycloak realm is not found."""
    pass


class UserMappingError(AuthenticationError):
    """Raised when user ID mapping fails."""
    pass


class KeycloakConnectionError(AuthenticationError):
    """Raised when connection to Keycloak fails."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when authentication credentials are invalid."""
    pass


class InsufficientPermissionsError(AuthenticationError):
    """Raised when user lacks required permissions."""
    pass


class RealmConfigurationError(AuthenticationError):
    """Raised when realm configuration is invalid."""
    pass


class PublicKeyError(AuthenticationError):
    """Raised when public key operations fail."""
    pass


class TokenValidationError(AuthenticationError):
    """Raised when token validation fails."""
    pass


class CacheError(AuthenticationError):
    """Cache operation error."""
    pass


class UserAlreadyExistsError(AuthenticationError):
    """User already exists error."""
    pass


class UserNotFoundError(AuthenticationError):
    """User not found error."""
    pass


class AuthorizationError(AuthenticationError):
    """Authorization error."""
    pass