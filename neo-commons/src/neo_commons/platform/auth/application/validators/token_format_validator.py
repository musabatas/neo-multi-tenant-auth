"""Token format validation."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import base64
import json
from ...core.value_objects import AccessToken
from ...core.exceptions import InvalidSignature


@dataclass
class TokenFormatValidationResult:
    """Result of token format validation."""
    
    is_valid: bool
    failure_reason: Optional[str] = None
    failure_details: Dict[str, Any] = None
    
    # Format analysis
    has_three_parts: bool = False
    header_valid: bool = False
    payload_valid: bool = False
    signature_present: bool = False
    
    # Extracted information (if valid)
    header: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize result after creation."""
        if self.failure_details is None:
            object.__setattr__(self, 'failure_details', {})


class TokenFormatValidator:
    """Validator for JWT token format following maximum separation principle.
    
    Handles ONLY JWT format validation concerns.
    Does not handle signature verification, expiration, or claims validation.
    """
    
    def __init__(self):
        """Initialize token format validator."""
        pass
    
    def validate(self, access_token: AccessToken) -> TokenFormatValidationResult:
        """Validate JWT token format.
        
        Args:
            access_token: Access token to validate format
            
        Returns:
            Token format validation result with details
        """
        token_value = str(access_token.value)
        
        # Step 1: Check for three parts separated by dots
        parts = token_value.split('.')
        has_three_parts = len(parts) == 3
        
        if not has_three_parts:
            return TokenFormatValidationResult(
                is_valid=False,
                failure_reason="invalid_token_structure",
                failure_details={
                    "parts_count": len(parts),
                    "expected_parts": 3,
                    "token_length": len(token_value)
                },
                has_three_parts=False
            )
        
        header_part, payload_part, signature_part = parts
        
        # Step 2: Validate header part
        header_valid, header_data, header_error = self._validate_jwt_part(
            header_part, "header"
        )
        
        # Step 3: Validate payload part
        payload_valid, payload_data, payload_error = self._validate_jwt_part(
            payload_part, "payload"
        )
        
        # Step 4: Check signature part presence
        signature_present = len(signature_part) > 0
        
        # Step 5: Validate JWT header requirements
        header_validation_error = None
        if header_valid and header_data:
            header_validation_error = self._validate_jwt_header(header_data)
        
        # Step 6: Determine overall validity
        is_valid = (
            has_three_parts and 
            header_valid and 
            payload_valid and 
            signature_present and
            header_validation_error is None
        )
        
        # Step 7: Prepare failure details
        failure_reason = None
        failure_details = {}
        
        if not is_valid:
            if not header_valid:
                failure_reason = "invalid_header"
                failure_details["header_error"] = header_error
            elif not payload_valid:
                failure_reason = "invalid_payload" 
                failure_details["payload_error"] = payload_error
            elif not signature_present:
                failure_reason = "missing_signature"
                failure_details["signature_length"] = len(signature_part)
            elif header_validation_error:
                failure_reason = "invalid_jwt_header"
                failure_details["header_validation_error"] = header_validation_error
        
        return TokenFormatValidationResult(
            is_valid=is_valid,
            failure_reason=failure_reason,
            failure_details=failure_details,
            has_three_parts=has_three_parts,
            header_valid=header_valid,
            payload_valid=payload_valid,
            signature_present=signature_present,
            header=header_data if header_valid else None,
            payload=payload_data if payload_valid else None
        )
    
    def _validate_jwt_part(self, part: str, part_name: str) -> tuple[bool, Optional[Dict], Optional[str]]:
        """Validate a JWT part (header or payload).
        
        Args:
            part: JWT part to validate
            part_name: Name of the part for error messages
            
        Returns:
            Tuple of (is_valid, decoded_data, error_message)
        """
        if not part:
            return False, None, f"Empty {part_name} part"
        
        try:
            # Add padding if needed for base64 decoding
            padded_part = self._add_base64_padding(part)
            
            # Decode base64
            decoded_bytes = base64.urlsafe_b64decode(padded_part)
            
            # Parse JSON
            decoded_data = json.loads(decoded_bytes.decode('utf-8'))
            
            if not isinstance(decoded_data, dict):
                return False, None, f"{part_name} is not a JSON object"
            
            return True, decoded_data, None
            
        except (ValueError, json.JSONDecodeError) as e:
            return False, None, f"Invalid {part_name} encoding: {str(e)}"
        except Exception as e:
            return False, None, f"Failed to decode {part_name}: {str(e)}"
    
    def _add_base64_padding(self, data: str) -> str:
        """Add proper padding to base64 string.
        
        Args:
            data: Base64 string that may need padding
            
        Returns:
            Properly padded base64 string
        """
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return data
    
    def _validate_jwt_header(self, header: Dict[str, Any]) -> Optional[str]:
        """Validate JWT header requirements.
        
        Args:
            header: Decoded JWT header
            
        Returns:
            Error message if invalid, None if valid
        """
        # Check for required 'alg' field
        if 'alg' not in header:
            return "Missing required 'alg' field in header"
        
        alg = header['alg']
        if not isinstance(alg, str):
            return "'alg' field must be a string"
        
        # Check for supported algorithms
        supported_algorithms = {
            'HS256', 'HS384', 'HS512',  # HMAC
            'RS256', 'RS384', 'RS512',  # RSA
            'ES256', 'ES384', 'ES512',  # ECDSA
            'PS256', 'PS384', 'PS512'   # RSA-PSS
        }
        
        if alg not in supported_algorithms:
            return f"Unsupported algorithm: {alg}"
        
        # Reject 'none' algorithm for security
        if alg == 'none':
            return "Algorithm 'none' is not allowed"
        
        # Check 'typ' field if present
        if 'typ' in header:
            typ = header['typ']
            if not isinstance(typ, str):
                return "'typ' field must be a string"
            
            # Common JWT type values
            if typ.upper() not in ['JWT', 'JWS', 'JWE']:
                return f"Unexpected token type: {typ}"
        
        return None