"""Token audience validation."""

from dataclasses import dataclass
from typing import Optional, List, Set, Union, Dict, Any
import json
import base64
from ...core.value_objects import AccessToken


@dataclass
class AudienceValidationResult:
    """Result of token audience validation."""
    
    is_valid: bool
    failure_reason: Optional[str] = None
    
    # Audience details
    token_audiences: List[str] = None
    expected_audiences: List[str] = None
    matched_audiences: List[str] = None
    
    # Validation context
    audience_required: bool = False
    allow_any_match: bool = True
    
    def __post_init__(self):
        """Initialize result after creation."""
        if self.token_audiences is None:
            object.__setattr__(self, 'token_audiences', [])
        
        if self.expected_audiences is None:
            object.__setattr__(self, 'expected_audiences', [])
        
        if self.matched_audiences is None:
            object.__setattr__(self, 'matched_audiences', [])


class AudienceValidator:
    """Token audience validator following maximum separation principle.
    
    Handles ONLY JWT token audience validation concerns.
    Does not handle token format, signature, expiration, or other validations.
    """
    
    def __init__(self, case_sensitive: bool = True):
        """Initialize audience validator.
        
        Args:
            case_sensitive: Whether audience matching is case-sensitive
        """
        self._case_sensitive = case_sensitive
    
    def validate(
        self, 
        access_token: AccessToken,
        expected_audiences: Optional[Union[str, List[str]]] = None,
        require_audience: bool = True,
        allow_any_match: bool = True
    ) -> AudienceValidationResult:
        """Validate JWT token audience claims.
        
        Args:
            access_token: JWT token to validate
            expected_audiences: Expected audience(s). Can be single string or list.
            require_audience: Whether 'aud' claim is required in token
            allow_any_match: If True, any expected audience can match.
                           If False, all expected audiences must be present.
            
        Returns:
            Audience validation result with details
        """
        # Step 1: Normalize expected audiences to list
        expected_aud_list = self._normalize_audiences(expected_audiences)
        
        # Step 2: Extract token claims
        try:
            claims = self._extract_payload_claims(access_token)
        except Exception as e:
            return AudienceValidationResult(
                is_valid=False,
                failure_reason=f"token_decode_error: {str(e)}",
                expected_audiences=expected_aud_list,
                audience_required=require_audience,
                allow_any_match=allow_any_match
            )
        
        # Step 3: Extract audience claim from token
        aud_claim = claims.get('aud')
        
        # Step 4: Check if audience claim is required
        if require_audience and aud_claim is None:
            return AudienceValidationResult(
                is_valid=False,
                failure_reason="missing_audience_claim",
                token_audiences=[],
                expected_audiences=expected_aud_list,
                audience_required=require_audience,
                allow_any_match=allow_any_match
            )
        
        # Step 5: If no audience claim and not required, pass validation
        if aud_claim is None:
            return AudienceValidationResult(
                is_valid=True,
                failure_reason=None,
                token_audiences=[],
                expected_audiences=expected_aud_list,
                audience_required=require_audience,
                allow_any_match=allow_any_match
            )
        
        # Step 6: Normalize token audiences to list
        try:
            token_aud_list = self._normalize_audiences(aud_claim)
        except Exception as e:
            return AudienceValidationResult(
                is_valid=False,
                failure_reason=f"invalid_audience_format: {str(e)}",
                token_audiences=[],
                expected_audiences=expected_aud_list,
                audience_required=require_audience,
                allow_any_match=allow_any_match
            )
        
        # Step 7: If no expected audiences provided, just validate that token has audiences
        if not expected_aud_list:
            is_valid = len(token_aud_list) > 0 if require_audience else True
            failure_reason = None if is_valid else "no_audiences_in_token"
            
            return AudienceValidationResult(
                is_valid=is_valid,
                failure_reason=failure_reason,
                token_audiences=token_aud_list,
                expected_audiences=expected_aud_list,
                matched_audiences=token_aud_list if is_valid else [],
                audience_required=require_audience,
                allow_any_match=allow_any_match
            )
        
        # Step 8: Perform audience matching
        matched_audiences = self._find_matching_audiences(token_aud_list, expected_aud_list)
        
        # Step 9: Determine validation result based on matching strategy
        if allow_any_match:
            # Pass if any expected audience matches any token audience
            is_valid = len(matched_audiences) > 0
            failure_reason = None if is_valid else "no_audience_match"
        else:
            # Pass only if all expected audiences are present in token
            is_valid = len(matched_audiences) == len(expected_aud_list)
            failure_reason = None if is_valid else "missing_required_audiences"
        
        return AudienceValidationResult(
            is_valid=is_valid,
            failure_reason=failure_reason,
            token_audiences=token_aud_list,
            expected_audiences=expected_aud_list,
            matched_audiences=matched_audiences,
            audience_required=require_audience,
            allow_any_match=allow_any_match
        )
    
    def _extract_payload_claims(self, access_token: AccessToken) -> Dict[str, Any]:
        """Extract claims from JWT payload without signature verification.
        
        Args:
            access_token: JWT token to extract claims from
            
        Returns:
            Dictionary of JWT claims
            
        Raises:
            ValueError: If token format is invalid or claims cannot be extracted
        """
        try:
            token_parts = str(access_token.value).split('.')
            if len(token_parts) != 3:
                raise ValueError("Invalid JWT format - must have 3 parts")
            
            # Extract payload (second part)
            payload_part = token_parts[1]
            
            # Add padding if needed for base64 decoding
            padding_needed = 4 - (len(payload_part) % 4)
            if padding_needed != 4:
                payload_part += '=' * padding_needed
            
            # Decode base64
            payload_bytes = base64.urlsafe_b64decode(payload_part)
            
            # Parse JSON
            claims = json.loads(payload_bytes.decode('utf-8'))
            
            if not isinstance(claims, dict):
                raise ValueError("JWT payload is not a JSON object")
            
            return claims
            
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to extract JWT claims: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error extracting claims: {str(e)}")
    
    def _normalize_audiences(self, audiences: Union[str, List[str], None]) -> List[str]:
        """Normalize audience input to list of strings.
        
        Args:
            audiences: Audience input (string, list of strings, or None)
            
        Returns:
            List of audience strings
            
        Raises:
            ValueError: If audience format is invalid
        """
        if audiences is None:
            return []
        
        if isinstance(audiences, str):
            if not audiences.strip():
                return []
            return [audiences.strip()]
        
        if isinstance(audiences, list):
            normalized = []
            for aud in audiences:
                if not isinstance(aud, str):
                    raise ValueError(f"Audience must be string, got {type(aud)}")
                aud_stripped = aud.strip()
                if aud_stripped:  # Only add non-empty audiences
                    normalized.append(aud_stripped)
            return normalized
        
        raise ValueError(f"Invalid audience type: {type(audiences)}")
    
    def _find_matching_audiences(
        self, 
        token_audiences: List[str], 
        expected_audiences: List[str]
    ) -> List[str]:
        """Find audiences that match between token and expected lists.
        
        Args:
            token_audiences: Audiences from token
            expected_audiences: Expected audiences
            
        Returns:
            List of matching audiences
        """
        matches = []
        
        for expected in expected_audiences:
            for token_aud in token_audiences:
                if self._audiences_match(token_aud, expected):
                    matches.append(expected)
                    break  # Found match for this expected audience
        
        return matches
    
    def _audiences_match(self, token_audience: str, expected_audience: str) -> bool:
        """Check if two audience strings match.
        
        Args:
            token_audience: Audience from token
            expected_audience: Expected audience
            
        Returns:
            True if audiences match, False otherwise
        """
        if self._case_sensitive:
            return token_audience == expected_audience
        else:
            return token_audience.lower() == expected_audience.lower()
    
    def has_audience(self, access_token: AccessToken, audience: str) -> bool:
        """Quick check if token has specific audience.
        
        Args:
            access_token: JWT token to check
            audience: Audience to check for
            
        Returns:
            True if token has the audience, False otherwise
        """
        try:
            result = self.validate(
                access_token=access_token,
                expected_audiences=[audience],
                require_audience=False,
                allow_any_match=True
            )
            return result.is_valid and len(result.matched_audiences) > 0
            
        except Exception:
            return False
    
    def get_token_audiences(self, access_token: AccessToken) -> List[str]:
        """Extract all audiences from token.
        
        Args:
            access_token: JWT token to extract audiences from
            
        Returns:
            List of audiences in token, empty list if none or error
        """
        try:
            result = self.validate(
                access_token=access_token,
                expected_audiences=None,
                require_audience=False,
                allow_any_match=True
            )
            return result.token_audiences
            
        except Exception:
            return []
    
    def is_case_sensitive(self) -> bool:
        """Check if audience matching is case-sensitive.
        
        Returns:
            True if case-sensitive, False otherwise
        """
        return self._case_sensitive
    
    def set_case_sensitive(self, case_sensitive: bool) -> None:
        """Set case sensitivity for audience matching.
        
        Args:
            case_sensitive: Whether to use case-sensitive matching
        """
        self._case_sensitive = case_sensitive