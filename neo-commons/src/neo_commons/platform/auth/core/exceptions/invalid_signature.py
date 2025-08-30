"""Invalid token signature exception with validation details."""

from typing import Optional, Dict, Any
from ....core.exceptions.base import DomainException


class InvalidSignature(DomainException):
    """Exception raised when token signature validation fails.
    
    Handles ONLY signature validation failure representation.
    Does not perform signature validation - that's handled by validators.
    """
    
    def __init__(
        self,
        message: str = "Token signature is invalid",
        *,
        algorithm: Optional[str] = None,
        key_id: Optional[str] = None,
        issuer: Optional[str] = None,
        validation_error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize signature validation failure exception.
        
        Args:
            message: Human-readable error message
            algorithm: JWT algorithm that was expected/used
            key_id: Key ID (kid) from JWT header, if present
            issuer: Token issuer, if known
            validation_error: Specific validation error from cryptographic library
            context: Additional context for debugging
        """
        super().__init__(message)
        
        self.algorithm = algorithm
        self.key_id = key_id
        self.issuer = issuer
        self.validation_error = validation_error
        self.context = context or {}
        
        # Add structured data for logging and monitoring
        self.details = {
            'algorithm': self.algorithm,
            'key_id': self.key_id,
            'issuer': self.issuer,
            'validation_error': self.validation_error,
            **self.context
        }
    
    @property
    def is_algorithm_mismatch(self) -> bool:
        """Check if error is due to algorithm mismatch."""
        if not self.validation_error:
            return False
        
        algorithm_error_keywords = [
            'algorithm', 'alg', 'unsupported', 'mismatch'
        ]
        
        return any(
            keyword in self.validation_error.lower()
            for keyword in algorithm_error_keywords
        )
    
    @property
    def is_key_not_found(self) -> bool:
        """Check if error is due to key not found."""
        if not self.validation_error:
            return False
        
        key_error_keywords = [
            'key not found', 'unknown key', 'invalid key',
            'key id', 'kid', 'jwk'
        ]
        
        return any(
            keyword in self.validation_error.lower()
            for keyword in key_error_keywords
        )
    
    @property
    def is_malformed_token(self) -> bool:
        """Check if error is due to malformed token structure."""
        if not self.validation_error:
            return False
        
        malformed_error_keywords = [
            'malformed', 'invalid format', 'decode error',
            'invalid token', 'corrupt'
        ]
        
        return any(
            keyword in self.validation_error.lower()
            for keyword in malformed_error_keywords
        )
    
    @classmethod
    def algorithm_not_supported(
        cls,
        algorithm: str,
        supported_algorithms: Optional[list] = None
    ) -> 'InvalidSignature':
        """Create exception for unsupported algorithm."""
        if supported_algorithms:
            message = f"Algorithm '{algorithm}' not supported. Supported: {', '.join(supported_algorithms)}"
        else:
            message = f"Algorithm '{algorithm}' is not supported"
        
        return cls(
            message=message,
            algorithm=algorithm,
            validation_error="unsupported_algorithm",
            context={'supported_algorithms': supported_algorithms}
        )
    
    @classmethod
    def key_not_found(
        cls,
        key_id: Optional[str] = None,
        issuer: Optional[str] = None
    ) -> 'InvalidSignature':
        """Create exception for key not found."""
        if key_id:
            message = f"Public key with ID '{key_id}' not found"
        elif issuer:
            message = f"No public key found for issuer '{issuer}'"
        else:
            message = "Public key for token validation not found"
        
        return cls(
            message=message,
            key_id=key_id,
            issuer=issuer,
            validation_error="key_not_found"
        )
    
    @classmethod
    def cryptographic_validation_failed(
        cls,
        algorithm: str,
        validation_error: str,
        key_id: Optional[str] = None
    ) -> 'InvalidSignature':
        """Create exception for cryptographic validation failure."""
        return cls(
            message="Token signature cryptographic validation failed",
            algorithm=algorithm,
            key_id=key_id,
            validation_error=validation_error
        )
    
    @classmethod
    def malformed_jwt(
        cls,
        validation_error: str
    ) -> 'InvalidSignature':
        """Create exception for malformed JWT structure."""
        return cls(
            message="Token has malformed structure",
            validation_error=validation_error
        )
    
    @classmethod
    def expired_key(
        cls,
        key_id: Optional[str] = None,
        issuer: Optional[str] = None
    ) -> 'InvalidSignature':
        """Create exception for expired signing key."""
        message = "Signing key has expired"
        if key_id:
            message += f" (key ID: {key_id})"
        
        return cls(
            message=message,
            key_id=key_id,
            issuer=issuer,
            validation_error="expired_key"
        )
    
    def __str__(self) -> str:
        """String representation with validation context."""
        base_msg = super().__str__()
        
        context_parts = []
        if self.algorithm:
            context_parts.append(f"algorithm={self.algorithm}")
        if self.key_id:
            context_parts.append(f"key_id={self.key_id}")
        if self.issuer:
            context_parts.append(f"issuer={self.issuer}")
        
        if context_parts:
            return f"{base_msg} ({', '.join(context_parts)})"
        
        return base_msg