"""Token validation protocol contract."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
from ..value_objects import AccessToken, TokenClaims


@runtime_checkable
class TokenValidator(Protocol):
    """Protocol for token validation operations.
    
    Defines ONLY the contract for token validation.
    Implementations handle specific validation logic (JWT, custom tokens, etc.).
    """
    
    async def validate_token(self, token: AccessToken) -> TokenClaims:
        """Validate token and return claims.
        
        Args:
            token: Access token to validate
            
        Returns:
            Validated token claims
            
        Raises:
            TokenExpired: If token has expired
            InvalidSignature: If token signature is invalid
            AuthenticationFailed: If token validation fails
        """
        ...
    
    async def validate_token_format(self, token: AccessToken) -> bool:
        """Validate token format without cryptographic verification.
        
        Args:
            token: Access token to check
            
        Returns:
            True if format is valid, False otherwise
        """
        ...
    
    async def extract_claims_unsafe(self, token: AccessToken) -> TokenClaims:
        """Extract claims without signature validation (for debugging).
        
        Args:
            token: Access token to parse
            
        Returns:
            Token claims (unverified)
            
        Note:
            This method should only be used for debugging or logging.
            Never use unverified claims for authorization decisions.
        """
        ...