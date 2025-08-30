"""JWT signature validation."""

from dataclasses import dataclass
from typing import Optional, List, Set
import jwt
from jwt.exceptions import (
    InvalidSignatureError, 
    InvalidKeyError, 
    DecodeError,
    InvalidTokenError
)
from ...core.value_objects import AccessToken, PublicKey
from ...core.exceptions import InvalidSignature


@dataclass
class SignatureValidationResult:
    """Result of JWT signature validation."""
    
    is_valid: bool
    failure_reason: Optional[str] = None
    algorithm_used: Optional[str] = None
    key_id_used: Optional[str] = None
    
    # Detailed validation info
    signature_verified: bool = False
    algorithm_supported: bool = False
    key_format_valid: bool = False
    
    def __post_init__(self):
        """Initialize result after creation."""
        if not self.is_valid and not self.failure_reason:
            object.__setattr__(self, 'failure_reason', 'unknown_validation_failure')


class SignatureValidator:
    """JWT signature validator following maximum separation principle.
    
    Handles ONLY JWT signature verification concerns.
    Does not handle token format, expiration, audience, or other validations.
    """
    
    def __init__(self, supported_algorithms: Optional[Set[str]] = None):
        """Initialize signature validator.
        
        Args:
            supported_algorithms: Set of supported JWT algorithms.
                                Defaults to common secure algorithms.
        """
        self._supported_algorithms = supported_algorithms or {
            'RS256', 'RS384', 'RS512',  # RSA with SHA
            'ES256', 'ES384', 'ES512',  # ECDSA with SHA  
            'PS256', 'PS384', 'PS512',  # RSA-PSS with SHA
        }
    
    def validate(
        self, 
        access_token: AccessToken, 
        public_key: PublicKey,
        algorithm: Optional[str] = None
    ) -> SignatureValidationResult:
        """Validate JWT token signature.
        
        Args:
            access_token: JWT token to validate
            public_key: Public key for signature verification
            algorithm: Specific algorithm to use (optional)
            
        Returns:
            Signature validation result with details
        """
        # Step 1: Determine algorithm(s) to use
        algorithms_to_try = self._determine_algorithms(algorithm, public_key)
        
        if not algorithms_to_try:
            return SignatureValidationResult(
                is_valid=False,
                failure_reason="no_supported_algorithms",
                algorithm_supported=False,
                key_format_valid=True,
                signature_verified=False
            )
        
        # Step 2: Validate public key format
        key_validation_result = self._validate_key_format(public_key)
        if not key_validation_result['is_valid']:
            return SignatureValidationResult(
                is_valid=False,
                failure_reason=key_validation_result['reason'],
                algorithm_supported=True,
                key_format_valid=False,
                signature_verified=False
            )
        
        # Step 3: Attempt signature verification with each algorithm
        for algo in algorithms_to_try:
            try:
                result = self._verify_with_algorithm(access_token, public_key, algo)
                if result.is_valid:
                    return result
                    
            except Exception as e:
                # Continue with next algorithm
                continue
        
        # Step 4: All algorithms failed
        return SignatureValidationResult(
            is_valid=False,
            failure_reason="signature_verification_failed",
            algorithm_supported=True,
            key_format_valid=True,
            signature_verified=False
        )
    
    def _determine_algorithms(
        self, 
        specified_algorithm: Optional[str], 
        public_key: PublicKey
    ) -> List[str]:
        """Determine which algorithms to try for verification.
        
        Args:
            specified_algorithm: Algorithm specified by caller
            public_key: Public key to determine compatible algorithms
            
        Returns:
            List of algorithms to try in order of preference
        """
        # If algorithm specified, use only that one (if supported)
        if specified_algorithm:
            if specified_algorithm in self._supported_algorithms:
                return [specified_algorithm]
            else:
                return []
        
        # If public key specifies algorithm, prefer that
        if public_key.algorithm and public_key.algorithm in self._supported_algorithms:
            return [public_key.algorithm]
        
        # Determine algorithms based on key type
        if public_key.is_rsa_key:
            return [
                algo for algo in ['RS256', 'RS384', 'RS512', 'PS256', 'PS384', 'PS512']
                if algo in self._supported_algorithms
            ]
        elif public_key.is_ec_key:
            return [
                algo for algo in ['ES256', 'ES384', 'ES512']
                if algo in self._supported_algorithms
            ]
        
        # Default to all supported algorithms
        return sorted(list(self._supported_algorithms))
    
    def _validate_key_format(self, public_key: PublicKey) -> dict:
        """Validate public key format for JWT verification.
        
        Args:
            public_key: Public key to validate
            
        Returns:
            Dictionary with validation result and reason
        """
        try:
            # Basic format validation is done in PublicKey constructor
            # Additional JWT-specific validation here
            
            if not public_key.key_data.strip():
                return {
                    'is_valid': False,
                    'reason': 'empty_key_data'
                }
            
            # Validate that key data looks like PEM format
            if not any(marker in public_key.key_data for marker in [
                'BEGIN PUBLIC KEY',
                'BEGIN RSA PUBLIC KEY', 
                'BEGIN EC PUBLIC KEY',
                'BEGIN CERTIFICATE'
            ]):
                return {
                    'is_valid': False,
                    'reason': 'invalid_pem_format'
                }
            
            return {
                'is_valid': True,
                'reason': None
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'reason': f'key_validation_error: {str(e)}'
            }
    
    def _verify_with_algorithm(
        self,
        access_token: AccessToken, 
        public_key: PublicKey,
        algorithm: str
    ) -> SignatureValidationResult:
        """Verify signature using specific algorithm.
        
        Args:
            access_token: JWT token to verify
            public_key: Public key for verification
            algorithm: Algorithm to use
            
        Returns:
            Signature validation result
        """
        try:
            # Verify signature by decoding token with signature verification enabled
            # Disable other validations (exp, aud, etc.) as those are handled by other validators
            jwt.decode(
                str(access_token.value),
                key=public_key.key_data,
                algorithms=[algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': False,
                    'verify_nbf': False,
                    'verify_iat': False,
                    'verify_aud': False
                }
            )
            
            # If we reach here, signature is valid
            return SignatureValidationResult(
                is_valid=True,
                failure_reason=None,
                algorithm_used=algorithm,
                key_id_used=public_key.key_id,
                algorithm_supported=True,
                key_format_valid=True,
                signature_verified=True
            )
            
        except InvalidSignatureError:
            return SignatureValidationResult(
                is_valid=False,
                failure_reason="invalid_signature",
                algorithm_used=algorithm,
                key_id_used=public_key.key_id,
                algorithm_supported=True,
                key_format_valid=True,
                signature_verified=False
            )
            
        except InvalidKeyError:
            return SignatureValidationResult(
                is_valid=False,
                failure_reason="invalid_key",
                algorithm_used=algorithm,
                key_id_used=public_key.key_id,
                algorithm_supported=True,
                key_format_valid=False,
                signature_verified=False
            )
            
        except DecodeError as e:
            # Could be token format issue, but we only report signature concerns
            return SignatureValidationResult(
                is_valid=False,
                failure_reason=f"decode_error: {str(e)}",
                algorithm_used=algorithm,
                key_id_used=public_key.key_id,
                algorithm_supported=True,
                key_format_valid=True,
                signature_verified=False
            )
            
        except InvalidTokenError as e:
            return SignatureValidationResult(
                is_valid=False,
                failure_reason=f"token_error: {str(e)}",
                algorithm_used=algorithm,
                key_id_used=public_key.key_id,
                algorithm_supported=True,
                key_format_valid=True,
                signature_verified=False
            )
            
        except Exception as e:
            return SignatureValidationResult(
                is_valid=False,
                failure_reason=f"unexpected_error: {str(e)}",
                algorithm_used=algorithm,
                key_id_used=public_key.key_id,
                algorithm_supported=False,
                key_format_valid=False,
                signature_verified=False
            )
    
    def validate_algorithm_support(self, algorithm: str) -> bool:
        """Check if algorithm is supported.
        
        Args:
            algorithm: JWT algorithm to check
            
        Returns:
            True if algorithm is supported, False otherwise
        """
        return algorithm in self._supported_algorithms
    
    def get_supported_algorithms(self) -> Set[str]:
        """Get set of supported algorithms.
        
        Returns:
            Set of supported JWT algorithms
        """
        return self._supported_algorithms.copy()
    
    def add_supported_algorithm(self, algorithm: str) -> None:
        """Add algorithm to supported list.
        
        Args:
            algorithm: Algorithm to add
        """
        self._supported_algorithms.add(algorithm)
    
    def remove_supported_algorithm(self, algorithm: str) -> None:
        """Remove algorithm from supported list.
        
        Args:
            algorithm: Algorithm to remove
        """
        self._supported_algorithms.discard(algorithm)