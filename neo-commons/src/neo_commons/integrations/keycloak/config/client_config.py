"""
Configuration classes for Keycloak client.

Provides default implementations for token validation and HTTP client configuration.
"""
from typing import Optional
from ..protocols.client_protocols import TokenValidationConfigProtocol


class DefaultTokenValidationConfig(TokenValidationConfigProtocol):
    """Default implementation of token validation configuration."""
    
    def __init__(
        self,
        jwt_algorithm: str = "RS256",
        jwt_audience: Optional[str] = None,
        jwt_verify_audience: bool = True,
        jwt_audience_fallback: bool = True,
        jwt_debug_claims: bool = False
    ):
        self._jwt_algorithm = jwt_algorithm
        self._jwt_audience = jwt_audience
        self._jwt_verify_audience = jwt_verify_audience
        self._jwt_audience_fallback = jwt_audience_fallback
        self._jwt_debug_claims = jwt_debug_claims
    
    def get_jwt_algorithm(self) -> str:
        return self._jwt_algorithm
    
    def get_jwt_audience(self) -> Optional[str]:
        return self._jwt_audience
    
    def is_jwt_audience_verification_enabled(self) -> bool:
        return self._jwt_verify_audience
    
    def should_fallback_without_audience(self) -> bool:
        return self._jwt_audience_fallback
    
    def is_debug_claims_enabled(self) -> bool:
        return self._jwt_debug_claims