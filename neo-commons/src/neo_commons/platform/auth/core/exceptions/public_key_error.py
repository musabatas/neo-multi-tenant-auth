"""Public key retrieval and parsing error exception."""

from typing import Optional, Dict, Any
from ....core.exceptions.base import DomainException


class PublicKeyError(DomainException):
    """Exception raised when public key operations fail.
    
    Handles ONLY public key error representation with context.
    Does not perform public key operations - that's handled by providers.
    """
    
    def __init__(
        self,
        message: str = "Public key operation failed",
        *,
        key_id: Optional[str] = None,
        issuer: Optional[str] = None,
        realm: Optional[str] = None,
        operation: Optional[str] = None,
        underlying_error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize public key error exception.
        
        Args:
            message: Human-readable error message
            key_id: Key identifier that caused the error
            issuer: Token issuer associated with the key
            realm: Realm where key was requested
            operation: Specific operation that failed (fetch, parse, validate, cache)
            underlying_error: Underlying system error message
            context: Additional context for debugging
        """
        super().__init__(message)
        
        self.key_id = key_id
        self.issuer = issuer
        self.realm = realm
        self.operation = operation
        self.underlying_error = underlying_error
        self.context = context or {}
        
        # Add structured data for logging and monitoring
        self.details = {
            'key_id': self.key_id,
            'issuer': self.issuer,
            'realm': self.realm,
            'operation': self.operation,
            'underlying_error': self.underlying_error,
            **self.context
        }
    
    @property
    def is_network_error(self) -> bool:
        """Check if error is due to network connectivity."""
        if not self.underlying_error:
            return False
        
        network_error_keywords = [
            'connection', 'timeout', 'network', 'unreachable',
            'dns', 'ssl', 'tls', 'certificate'
        ]
        
        return any(
            keyword in self.underlying_error.lower()
            for keyword in network_error_keywords
        )
    
    @property
    def is_parsing_error(self) -> bool:
        """Check if error is due to key parsing/format issues."""
        if not self.underlying_error:
            return False
        
        parsing_error_keywords = [
            'parse', 'format', 'decode', 'invalid',
            'malformed', 'pem', 'jwk', 'x509'
        ]
        
        return any(
            keyword in self.underlying_error.lower()
            for keyword in parsing_error_keywords
        )
    
    @property
    def is_not_found_error(self) -> bool:
        """Check if error is due to key not found."""
        return self.operation == 'fetch' and (
            'not found' in (self.underlying_error or '').lower() or
            'key not found' in self.message.lower()
        )
    
    @property
    def is_cache_error(self) -> bool:
        """Check if error is related to caching operations."""
        return self.operation == 'cache' or (
            self.underlying_error and 'cache' in self.underlying_error.lower()
        )
    
    @classmethod
    def fetch_failed(
        cls,
        issuer: str,
        key_id: Optional[str] = None,
        underlying_error: Optional[str] = None
    ) -> 'PublicKeyError':
        """Create exception for public key fetch failure."""
        message = f"Failed to fetch public key from issuer '{issuer}'"
        if key_id:
            message += f" (key ID: {key_id})"
        
        return cls(
            message=message,
            key_id=key_id,
            issuer=issuer,
            operation="fetch",
            underlying_error=underlying_error
        )
    
    @classmethod
    def parse_failed(
        cls,
        key_format: str,
        underlying_error: Optional[str] = None,
        key_id: Optional[str] = None
    ) -> 'PublicKeyError':
        """Create exception for public key parsing failure."""
        message = f"Failed to parse {key_format} public key"
        if key_id:
            message += f" (key ID: {key_id})"
        
        return cls(
            message=message,
            key_id=key_id,
            operation="parse",
            underlying_error=underlying_error,
            context={'key_format': key_format}
        )
    
    @classmethod
    def cache_failed(
        cls,
        operation: str,  # 'store', 'retrieve', 'invalidate'
        key_id: Optional[str] = None,
        underlying_error: Optional[str] = None
    ) -> 'PublicKeyError':
        """Create exception for public key cache operation failure."""
        message = f"Failed to {operation} public key in cache"
        if key_id:
            message += f" (key ID: {key_id})"
        
        return cls(
            message=message,
            key_id=key_id,
            operation="cache",
            underlying_error=underlying_error,
            context={'cache_operation': operation}
        )
    
    @classmethod
    def jwks_endpoint_failed(
        cls,
        endpoint_url: str,
        underlying_error: Optional[str] = None
    ) -> 'PublicKeyError':
        """Create exception for JWKS endpoint failure."""
        return cls(
            message=f"Failed to retrieve JWKS from endpoint: {endpoint_url}",
            operation="fetch",
            underlying_error=underlying_error,
            context={'jwks_endpoint': endpoint_url}
        )
    
    @classmethod
    def key_not_in_jwks(
        cls,
        key_id: str,
        issuer: str,
        available_keys: Optional[list] = None
    ) -> 'PublicKeyError':
        """Create exception for key not found in JWKS."""
        message = f"Key ID '{key_id}' not found in JWKS from issuer '{issuer}'"
        if available_keys:
            message += f". Available keys: {', '.join(available_keys)}"
        
        return cls(
            message=message,
            key_id=key_id,
            issuer=issuer,
            operation="fetch",
            context={'available_keys': available_keys}
        )
    
    @classmethod
    def expired_jwks(
        cls,
        issuer: str,
        cache_age_seconds: int,
        max_age_seconds: int
    ) -> 'PublicKeyError':
        """Create exception for expired JWKS cache."""
        return cls(
            message=f"JWKS cache expired for issuer '{issuer}' (age: {cache_age_seconds}s, max: {max_age_seconds}s)",
            issuer=issuer,
            operation="cache",
            context={
                'cache_age_seconds': cache_age_seconds,
                'max_age_seconds': max_age_seconds
            }
        )
    
    def __str__(self) -> str:
        """String representation with key context."""
        base_msg = super().__str__()
        
        context_parts = []
        if self.key_id:
            context_parts.append(f"key_id={self.key_id}")
        if self.issuer:
            context_parts.append(f"issuer={self.issuer}")
        if self.realm:
            context_parts.append(f"realm={self.realm}")
        if self.operation:
            context_parts.append(f"operation={self.operation}")
        
        if context_parts:
            return f"{base_msg} ({', '.join(context_parts)})"
        
        return base_msg