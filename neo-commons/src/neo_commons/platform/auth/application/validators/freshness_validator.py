"""Token freshness validation."""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import json
import base64
from ...core.value_objects import AccessToken


@dataclass
class FreshnessValidationResult:
    """Result of token freshness validation."""
    
    is_valid: bool
    failure_reason: Optional[str] = None
    
    # Freshness details
    issued_at: Optional[datetime] = None
    current_time: datetime = None
    max_age_seconds: Optional[int] = None
    
    # Age calculations
    token_age_seconds: Optional[int] = None
    remaining_freshness_seconds: Optional[int] = None
    is_fresh: bool = False
    is_stale: bool = False
    
    def __post_init__(self):
        """Initialize result after creation."""
        if self.current_time is None:
            object.__setattr__(self, 'current_time', datetime.now(timezone.utc))
        
        # Calculate age-based flags and durations
        if self.issued_at and self.current_time:
            age_seconds = int((self.current_time - self.issued_at).total_seconds())
            object.__setattr__(self, 'token_age_seconds', age_seconds)
            
            if self.max_age_seconds is not None:
                remaining = self.max_age_seconds - age_seconds
                object.__setattr__(self, 'remaining_freshness_seconds', remaining)
                object.__setattr__(self, 'is_fresh', age_seconds <= self.max_age_seconds)
                object.__setattr__(self, 'is_stale', age_seconds > self.max_age_seconds)


class FreshnessValidator:
    """Token freshness validator following maximum separation principle.
    
    Handles ONLY JWT token freshness validation concerns.
    Does not handle token format, signature, expiration, or audience validations.
    
    Freshness validation ensures tokens haven't been issued too long ago,
    which is important for sensitive operations that require recent authentication.
    """
    
    def __init__(self, default_max_age_seconds: int = 300):
        """Initialize freshness validator.
        
        Args:
            default_max_age_seconds: Default maximum token age in seconds.
                                   Defaults to 5 minutes (300 seconds).
        """
        if default_max_age_seconds <= 0:
            raise ValueError("Default max age must be positive")
        
        self._default_max_age_seconds = default_max_age_seconds
    
    def validate(
        self, 
        access_token: AccessToken,
        max_age_seconds: Optional[int] = None,
        require_issued_at: bool = True
    ) -> FreshnessValidationResult:
        """Validate JWT token freshness based on issued-at time.
        
        Args:
            access_token: JWT token to validate
            max_age_seconds: Maximum allowed age in seconds. If None, uses default.
            require_issued_at: Whether 'iat' claim is required
            
        Returns:
            Freshness validation result with details
        """
        current_time = datetime.now(timezone.utc)
        max_age = max_age_seconds if max_age_seconds is not None else self._default_max_age_seconds
        
        # Validate max_age parameter
        if max_age <= 0:
            return FreshnessValidationResult(
                is_valid=False,
                failure_reason="invalid_max_age_parameter",
                current_time=current_time,
                max_age_seconds=max_age
            )
        
        # Step 1: Extract token claims
        try:
            claims = self._extract_payload_claims(access_token)
        except Exception as e:
            return FreshnessValidationResult(
                is_valid=False,
                failure_reason=f"token_decode_error: {str(e)}",
                current_time=current_time,
                max_age_seconds=max_age
            )
        
        # Step 2: Extract issued-at claim
        iat_timestamp = claims.get('iat')
        
        # Step 3: Check if issued-at is required
        if require_issued_at and iat_timestamp is None:
            return FreshnessValidationResult(
                is_valid=False,
                failure_reason="missing_iat_claim",
                current_time=current_time,
                max_age_seconds=max_age
            )
        
        # Step 4: If no issued-at claim and not required, skip freshness validation
        if iat_timestamp is None:
            return FreshnessValidationResult(
                is_valid=True,
                failure_reason=None,
                current_time=current_time,
                max_age_seconds=max_age,
                token_age_seconds=0,  # Unknown age, assume fresh
                remaining_freshness_seconds=max_age,
                is_fresh=True,
                is_stale=False
            )
        
        # Step 5: Convert timestamp to datetime
        try:
            issued_at = self._timestamp_to_datetime(iat_timestamp)
        except ValueError as e:
            return FreshnessValidationResult(
                is_valid=False,
                failure_reason=f"invalid_iat_timestamp: {str(e)}",
                current_time=current_time,
                max_age_seconds=max_age
            )
        
        # Step 6: Calculate token age
        age_timedelta = current_time - issued_at
        age_seconds = int(age_timedelta.total_seconds())
        
        # Step 7: Validate that token wasn't issued in the future
        if age_seconds < 0:
            return FreshnessValidationResult(
                is_valid=False,
                failure_reason="token_issued_in_future",
                issued_at=issued_at,
                current_time=current_time,
                max_age_seconds=max_age,
                token_age_seconds=age_seconds
            )
        
        # Step 8: Check freshness
        is_fresh = age_seconds <= max_age
        
        return FreshnessValidationResult(
            is_valid=is_fresh,
            failure_reason=None if is_fresh else "token_too_old",
            issued_at=issued_at,
            current_time=current_time,
            max_age_seconds=max_age
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
    
    def is_token_fresh(
        self, 
        access_token: AccessToken, 
        max_age_seconds: Optional[int] = None
    ) -> bool:
        """Quick check if token is fresh enough.
        
        Args:
            access_token: JWT token to check
            max_age_seconds: Maximum allowed age in seconds. If None, uses default.
            
        Returns:
            True if token is fresh, False otherwise
        """
        try:
            result = self.validate(
                access_token=access_token,
                max_age_seconds=max_age_seconds,
                require_issued_at=False
            )
            return result.is_valid
            
        except Exception:
            # If we can't determine freshness, consider it stale for safety
            return False
    
    def get_token_age_seconds(self, access_token: AccessToken) -> Optional[int]:
        """Get token age in seconds.
        
        Args:
            access_token: JWT token to check
            
        Returns:
            Token age in seconds, None if cannot be determined
        """
        try:
            result = self.validate(
                access_token=access_token,
                max_age_seconds=self._default_max_age_seconds,
                require_issued_at=False
            )
            return result.token_age_seconds
            
        except Exception:
            return None
    
    def get_freshness_expiry_time(
        self, 
        access_token: AccessToken, 
        max_age_seconds: Optional[int] = None
    ) -> Optional[datetime]:
        """Get the time when token freshness expires.
        
        Args:
            access_token: JWT token to check
            max_age_seconds: Maximum allowed age in seconds. If None, uses default.
            
        Returns:
            Datetime when freshness expires, None if cannot be determined
        """
        try:
            result = self.validate(
                access_token=access_token,
                max_age_seconds=max_age_seconds,
                require_issued_at=False
            )
            
            if result.issued_at and result.max_age_seconds:
                return result.issued_at + timedelta(seconds=result.max_age_seconds)
            
            return None
            
        except Exception:
            return None
    
    def get_default_max_age_seconds(self) -> int:
        """Get default maximum age for freshness validation.
        
        Returns:
            Default maximum age in seconds
        """
        return self._default_max_age_seconds
    
    def set_default_max_age_seconds(self, seconds: int) -> None:
        """Set default maximum age for freshness validation.
        
        Args:
            seconds: Maximum age in seconds (must be positive)
        """
        if seconds <= 0:
            raise ValueError("Max age must be positive")
        self._default_max_age_seconds = seconds