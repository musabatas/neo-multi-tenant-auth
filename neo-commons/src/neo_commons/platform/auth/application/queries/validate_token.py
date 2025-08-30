"""Token validation query."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import AccessToken, TokenClaims, RealmIdentifier
from ...core.entities import UserContext, TokenMetadata
from ...core.exceptions import TokenExpired, InvalidSignature, AuthenticationFailed


@dataclass
class ValidateTokenRequest:
    """Request to validate a token."""
    
    access_token: AccessToken
    realm_id: Optional[RealmIdentifier] = None
    
    # Validation options
    validate_expiration: bool = True
    validate_signature: bool = True
    validate_audience: bool = True
    validate_issuer: bool = True
    
    # Context for validation
    expected_audience: Optional[str] = None
    expected_issuer: Optional[str] = None
    clock_skew_seconds: int = 30


@dataclass
class ValidateTokenResponse:
    """Response from token validation."""
    
    is_valid: bool
    token_claims: Optional[TokenClaims] = None
    user_context: Optional[UserContext] = None
    token_metadata: Optional[TokenMetadata] = None
    validation_timestamp: datetime = None
    
    # Validation details
    signature_valid: bool = False
    expiration_valid: bool = False
    audience_valid: bool = False
    issuer_valid: bool = False
    
    # Failure information
    failure_reason: Optional[str] = None
    failure_details: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize response after creation."""
        if self.validation_timestamp is None:
            object.__setattr__(self, 'validation_timestamp', datetime.now(timezone.utc))
        
        if self.failure_details is None:
            object.__setattr__(self, 'failure_details', {})


@runtime_checkable
class TokenParser(Protocol):
    """Protocol for token parsing operations."""
    
    async def parse_token(self, access_token: AccessToken) -> TokenClaims:
        """Parse token and extract claims without validation."""
        ...


@runtime_checkable
class SignatureValidator(Protocol):
    """Protocol for signature validation operations."""
    
    async def validate_signature(
        self,
        access_token: AccessToken,
        realm_id: Optional[RealmIdentifier] = None
    ) -> bool:
        """Validate token signature."""
        ...


@runtime_checkable
class UserContextLoader(Protocol):
    """Protocol for user context loading operations."""
    
    async def load_user_context(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId],
        realm_id: Optional[RealmIdentifier]
    ) -> UserContext:
        """Load user context from user ID."""
        ...


@runtime_checkable
class TokenMetadataLoader(Protocol):
    """Protocol for token metadata loading operations."""
    
    async def load_token_metadata(
        self,
        access_token: AccessToken,
        token_claims: TokenClaims
    ) -> TokenMetadata:
        """Load or create token metadata."""
        ...


class ValidateToken:
    """Query to validate tokens following maximum separation principle.
    
    Handles ONLY token validation workflow orchestration.
    Does not handle token parsing, signature validation, or user loading.
    """
    
    def __init__(
        self,
        token_parser: TokenParser,
        signature_validator: SignatureValidator,
        user_context_loader: UserContextLoader,
        token_metadata_loader: TokenMetadataLoader
    ):
        """Initialize query with protocol dependencies."""
        self._token_parser = token_parser
        self._signature_validator = signature_validator
        self._user_context_loader = user_context_loader
        self._token_metadata_loader = token_metadata_loader
    
    async def execute(self, request: ValidateTokenRequest) -> ValidateTokenResponse:
        """Execute token validation query.
        
        Args:
            request: Token validation request with token and options
            
        Returns:
            Token validation response with validation results
        """
        validation_start = datetime.now(timezone.utc)
        
        # Initialize response with defaults
        response = ValidateTokenResponse(
            is_valid=False,
            validation_timestamp=validation_start
        )
        
        try:
            # Step 1: Parse token claims
            try:
                token_claims = await self._token_parser.parse_token(request.access_token)
                response.token_claims = token_claims
            except Exception as e:
                response.failure_reason = "token_parse_error"
                response.failure_details = {"error": str(e)}
                return response
            
            # Step 2: Validate signature if required
            if request.validate_signature:
                try:
                    signature_valid = await self._signature_validator.validate_signature(
                        access_token=request.access_token,
                        realm_id=request.realm_id
                    )
                    response.signature_valid = signature_valid
                    
                    if not signature_valid:
                        response.failure_reason = "invalid_signature"
                        response.failure_details = {"signature_check": "failed"}
                        return response
                        
                except Exception as e:
                    response.failure_reason = "signature_validation_error"
                    response.failure_details = {"error": str(e)}
                    return response
            else:
                response.signature_valid = True
            
            # Step 3: Validate expiration if required
            if request.validate_expiration:
                expiration_valid = self._validate_expiration(
                    token_claims, 
                    request.clock_skew_seconds
                )
                response.expiration_valid = expiration_valid
                
                if not expiration_valid:
                    response.failure_reason = "token_expired"
                    response.failure_details = {
                        "expires_at": token_claims.expiration.isoformat() if token_claims.expiration else None,
                        "current_time": validation_start.isoformat()
                    }
                    return response
            else:
                response.expiration_valid = True
            
            # Step 4: Validate audience if required
            if request.validate_audience:
                audience_valid = self._validate_audience(
                    token_claims,
                    request.expected_audience
                )
                response.audience_valid = audience_valid
                
                if not audience_valid:
                    response.failure_reason = "invalid_audience"
                    response.failure_details = {
                        "token_audience": token_claims.audience,
                        "expected_audience": request.expected_audience
                    }
                    return response
            else:
                response.audience_valid = True
            
            # Step 5: Validate issuer if required
            if request.validate_issuer:
                issuer_valid = self._validate_issuer(
                    token_claims,
                    request.expected_issuer
                )
                response.issuer_valid = issuer_valid
                
                if not issuer_valid:
                    response.failure_reason = "invalid_issuer"
                    response.failure_details = {
                        "token_issuer": token_claims.issuer,
                        "expected_issuer": request.expected_issuer
                    }
                    return response
            else:
                response.issuer_valid = True
            
            # Step 6: Load user context if validation successful
            if token_claims.subject:
                try:
                    user_id = UserId(token_claims.subject)
                    tenant_id = TenantId(token_claims.get_claim('tenant_id')) if token_claims.get_claim('tenant_id') else None
                    
                    user_context = await self._user_context_loader.load_user_context(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        realm_id=request.realm_id
                    )
                    response.user_context = user_context
                    
                except Exception as e:
                    # User loading failure doesn't invalidate token but limits functionality
                    response.failure_details["user_context_error"] = str(e)
            
            # Step 7: Load token metadata
            try:
                token_metadata = await self._token_metadata_loader.load_token_metadata(
                    access_token=request.access_token,
                    token_claims=token_claims
                )
                response.token_metadata = token_metadata
                
            except Exception as e:
                # Metadata loading failure doesn't invalidate token
                response.failure_details["metadata_error"] = str(e)
            
            # Step 8: Mark validation as successful
            response.is_valid = True
            return response
            
        except Exception as e:
            # Unexpected error during validation
            response.failure_reason = "validation_error"
            response.failure_details = {"error": str(e)}
            return response
    
    def _validate_expiration(
        self, 
        token_claims: TokenClaims, 
        clock_skew_seconds: int
    ) -> bool:
        """Validate token expiration with clock skew tolerance.
        
        Args:
            token_claims: Token claims to validate
            clock_skew_seconds: Clock skew tolerance in seconds
            
        Returns:
            True if token is not expired (with tolerance)
        """
        if not token_claims.expiration:
            # No expiration claim - consider valid
            return True
        
        current_time = datetime.now(timezone.utc)
        # Add clock skew tolerance
        expiration_with_skew = token_claims.expiration.timestamp() + clock_skew_seconds
        
        return current_time.timestamp() <= expiration_with_skew
    
    def _validate_audience(
        self, 
        token_claims: TokenClaims, 
        expected_audience: Optional[str]
    ) -> bool:
        """Validate token audience.
        
        Args:
            token_claims: Token claims to validate
            expected_audience: Expected audience value
            
        Returns:
            True if audience is valid
        """
        if not expected_audience:
            # No expected audience - consider valid
            return True
        
        token_audience = token_claims.audience
        if not token_audience:
            # No audience in token
            return False
        
        # Handle both string and list audiences
        if isinstance(token_audience, str):
            return token_audience == expected_audience
        elif isinstance(token_audience, list):
            return expected_audience in token_audience
        else:
            return False
    
    def _validate_issuer(
        self, 
        token_claims: TokenClaims, 
        expected_issuer: Optional[str]
    ) -> bool:
        """Validate token issuer.
        
        Args:
            token_claims: Token claims to validate
            expected_issuer: Expected issuer value
            
        Returns:
            True if issuer is valid
        """
        if not expected_issuer:
            # No expected issuer - consider valid
            return True
        
        return token_claims.issuer == expected_issuer