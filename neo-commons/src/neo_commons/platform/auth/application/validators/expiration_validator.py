"""Token expiration validation."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json
import base64
from ...core.value_objects import AccessToken
from ...core.exceptions import TokenExpired


@dataclass
class ExpirationValidationResult:
    """Result of token expiration validation."""
    
    is_valid: bool
    failure_reason: Optional[str] = None
    
    # Expiration details
    expires_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None
    not_before: Optional[datetime] = None
    
    # Validation context
    current_time: datetime = None
    
    # Time calculations
    seconds_until_expiry: Optional[int] = None
    seconds_since_issued: Optional[int] = None
    is_expired: bool = False
    is_not_yet_valid: bool = False
    
    def __post_init__(self):
        """Initialize result after creation."""
        if self.current_time is None:
            object.__setattr__(self, 'current_time', datetime.now(timezone.utc))
        
        # Calculate time-based flags and durations
        if self.expires_at:
            seconds_diff = int((self.expires_at - self.current_time).total_seconds())
            object.__setattr__(self, 'seconds_until_expiry', seconds_diff)
            object.__setattr__(self, 'is_expired', seconds_diff <= 0)
        
        if self.issued_at:
            seconds_since = int((self.current_time - self.issued_at).total_seconds())
            object.__setattr__(self, 'seconds_since_issued', seconds_since)
        
        if self.not_before:
            object.__setattr__(self, 'is_not_yet_valid', self.current_time < self.not_before)


class ExpirationValidator:
    """Token expiration validator following maximum separation principle.
    
    Handles ONLY JWT token expiration validation concerns.
    Does not handle token format, signature, audience, or other validations.
    """
    
    def __init__(self, clock_skew_seconds: int = 60):
        """Initialize expiration validator.
        
        Args:
            clock_skew_seconds: Allowed clock skew in seconds for time comparisons.
                               Accounts for small differences in server clocks.
        """
        self._clock_skew_seconds = clock_skew_seconds
    
    def validate(
        self, 
        access_token: AccessToken,
        require_expiration: bool = True,
        require_issued_at: bool = False,
        require_not_before: bool = False
    ) -> ExpirationValidationResult:
        """Validate JWT token expiration claims.
        
        Args:
            access_token: JWT token to validate
            require_expiration: Whether 'exp' claim is required
            require_issued_at: Whether 'iat' claim is required  
            require_not_before: Whether 'nbf' claim is required
            
        Returns:
            Expiration validation result with details
        """
        current_time = datetime.now(timezone.utc)
        
        # Step 1: Extract token claims
        try:
            claims = self._extract_payload_claims(access_token)
        except Exception as e:
            return ExpirationValidationResult(
                is_valid=False,
                failure_reason=f"token_decode_error: {str(e)}",
                current_time=current_time
            )
        
        # Step 2: Extract time-related claims
        exp_timestamp = claims.get('exp')
        iat_timestamp = claims.get('iat')  
        nbf_timestamp = claims.get('nbf')
        
        # Step 3: Validate required claims presence
        validation_errors = []
        
        if require_expiration and exp_timestamp is None:
            validation_errors.append("missing_exp_claim")
        
        if require_issued_at and iat_timestamp is None:
            validation_errors.append("missing_iat_claim")
            
        if require_not_before and nbf_timestamp is None:
            validation_errors.append("missing_nbf_claim")
        
        if validation_errors:
            return ExpirationValidationResult(
                is_valid=False,
                failure_reason=f"missing_claims: {', '.join(validation_errors)}",
                current_time=current_time
            )
        
        # Step 4: Convert timestamps to datetime objects
        expires_at = None
        issued_at = None
        not_before = None
        
        try:
            if exp_timestamp is not None:
                expires_at = self._timestamp_to_datetime(exp_timestamp)
                
            if iat_timestamp is not None:
                issued_at = self._timestamp_to_datetime(iat_timestamp)
                
            if nbf_timestamp is not None:
                not_before = self._timestamp_to_datetime(nbf_timestamp)
                
        except ValueError as e:
            return ExpirationValidationResult(
                is_valid=False,
                failure_reason=f"invalid_timestamp: {str(e)}",
                current_time=current_time
            )
        
        # Step 5: Validate expiration (with clock skew)
        expiration_valid = True
        expiration_reason = None
        
        if expires_at:
            # Allow clock skew for expiration check
            effective_expiry = expires_at.timestamp() + self._clock_skew_seconds
            if current_time.timestamp() > effective_expiry:
                expiration_valid = False
                expiration_reason = "token_expired"
        
        # Step 6: Validate not-before (with clock skew)
        nbf_valid = True
        nbf_reason = None
        
        if not_before:
            # Allow clock skew for not-before check
            effective_nbf = not_before.timestamp() - self._clock_skew_seconds
            if current_time.timestamp() < effective_nbf:
                nbf_valid = False
                nbf_reason = "token_not_yet_valid"
        
        # Step 7: Validate issued-at reasonableness
        iat_valid = True
        iat_reason = None
        
        if issued_at:
            # Check if issued time is not in the future (with clock skew)
            future_threshold = current_time.timestamp() + self._clock_skew_seconds
            if issued_at.timestamp() > future_threshold:
                iat_valid = False
                iat_reason = "issued_in_future"
        
        # Step 8: Determine overall validity
        is_valid = expiration_valid and nbf_valid and iat_valid
        
        failure_reasons = [r for r in [expiration_reason, nbf_reason, iat_reason] if r]
        failure_reason = ', '.join(failure_reasons) if failure_reasons else None
        
        return ExpirationValidationResult(
            is_valid=is_valid,
            failure_reason=failure_reason,
            expires_at=expires_at,
            issued_at=issued_at,
            not_before=not_before,
            current_time=current_time
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
    
    def _timestamp_to_datetime(self, timestamp: Any) -> datetime:
        """Convert JWT timestamp to datetime object.
        
        Args:
            timestamp: JWT timestamp (should be Unix timestamp)
            
        Returns:
            Datetime object in UTC timezone
            
        Raises:
            ValueError: If timestamp is invalid
        """
        try:
            # Handle different timestamp types
            if isinstance(timestamp, str):
                timestamp = float(timestamp)
            elif isinstance(timestamp, int):
                timestamp = float(timestamp)
            elif not isinstance(timestamp, float):
                raise ValueError(f"Invalid timestamp type: {type(timestamp)}")
            
            # Validate timestamp range (reasonable dates)
            # JWT timestamps are in seconds since epoch
            min_timestamp = 946684800.0  # 2000-01-01 00:00:00 UTC
            max_timestamp = 4102444800.0  # 2100-01-01 00:00:00 UTC
            
            if timestamp < min_timestamp or timestamp > max_timestamp:
                raise ValueError(f"Timestamp out of reasonable range: {timestamp}")
            
            return datetime.fromtimestamp(timestamp, timezone.utc)
            
        except (ValueError, OverflowError, OSError) as e:
            raise ValueError(f"Invalid timestamp: {str(e)}")
    
    def is_token_expired(self, access_token: AccessToken) -> bool:
        """Quick check if token is expired.
        
        Args:
            access_token: JWT token to check
            
        Returns:
            True if token is expired, False otherwise
        """
        try:
            result = self.validate(access_token, require_expiration=False)
            return result.is_expired if result.expires_at else False
            
        except Exception:
            # If we can't determine expiration, consider it expired for safety
            return True
    
    def time_until_expiry(self, access_token: AccessToken) -> Optional[int]:
        """Get seconds until token expires.
        
        Args:
            access_token: JWT token to check
            
        Returns:
            Seconds until expiry, None if no expiration or invalid token
        """
        try:
            result = self.validate(access_token, require_expiration=False)
            return result.seconds_until_expiry
            
        except Exception:
            return None
    
    def get_clock_skew_seconds(self) -> int:
        """Get current clock skew allowance.
        
        Returns:
            Clock skew allowance in seconds
        """
        return self._clock_skew_seconds
    
    def set_clock_skew_seconds(self, seconds: int) -> None:
        """Set clock skew allowance.
        
        Args:
            seconds: Clock skew allowance in seconds (must be non-negative)
        """
        if seconds < 0:
            raise ValueError("Clock skew must be non-negative")
        self._clock_skew_seconds = seconds