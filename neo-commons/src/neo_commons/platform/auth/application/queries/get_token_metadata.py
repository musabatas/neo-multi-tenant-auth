"""Get token metadata query."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import AccessToken, TokenClaims, SessionId
from ...core.entities import TokenMetadata
from ...core.exceptions import AuthenticationFailed, InvalidSignature


@dataclass
class GetTokenMetadataRequest:
    """Request to get token metadata."""
    
    access_token: AccessToken
    
    # Metadata options
    include_usage_stats: bool = True
    include_security_info: bool = True
    include_claims_analysis: bool = True
    track_access: bool = False
    
    # Context information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class GetTokenMetadataResponse:
    """Response from get token metadata query."""
    
    token_metadata: TokenMetadata
    retrieved_timestamp: datetime
    
    # Additional analysis
    token_age_seconds: Optional[int] = None
    time_until_expiry_seconds: Optional[int] = None
    usage_frequency: Optional[str] = None  # high, medium, low, first_use
    security_risk_level: Optional[str] = None  # low, medium, high, critical
    
    # Retrieval information
    retrieved_from_cache: bool = False
    metadata_complete: bool = True
    
    def __post_init__(self):
        """Initialize response after creation."""
        if self.retrieved_timestamp is None:
            object.__setattr__(self, 'retrieved_timestamp', datetime.now(timezone.utc))


@runtime_checkable
class TokenParser(Protocol):
    """Protocol for token parsing operations."""
    
    async def parse_token_claims(self, access_token: AccessToken) -> TokenClaims:
        """Parse token and extract claims."""
        ...


@runtime_checkable
class TokenMetadataProvider(Protocol):
    """Protocol for token metadata operations."""
    
    async def get_token_metadata(
        self,
        access_token: AccessToken,
        token_claims: Optional[TokenClaims] = None
    ) -> Optional[TokenMetadata]:
        """Get existing token metadata."""
        ...
    
    async def create_token_metadata(
        self,
        access_token: AccessToken,
        token_claims: TokenClaims,
        usage_context: Dict[str, Any] = None
    ) -> TokenMetadata:
        """Create new token metadata."""
        ...


@runtime_checkable
class TokenAnalyzer(Protocol):
    """Protocol for token analysis operations."""
    
    async def analyze_token_usage(
        self,
        token_metadata: TokenMetadata
    ) -> Dict[str, Any]:
        """Analyze token usage patterns."""
        ...
    
    async def assess_token_security(
        self,
        token_metadata: TokenMetadata,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assess token security risk."""
        ...


@runtime_checkable
class TokenTracker(Protocol):
    """Protocol for token usage tracking operations."""
    
    async def record_token_access(
        self,
        access_token: AccessToken,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        access_type: str = "metadata_query"
    ) -> bool:
        """Record token access for tracking."""
        ...


class GetTokenMetadata:
    """Query to get token metadata following maximum separation principle.
    
    Handles ONLY token metadata retrieval workflow orchestration.
    Does not handle token parsing, metadata storage, or security analysis.
    """
    
    def __init__(
        self,
        token_parser: TokenParser,
        token_metadata_provider: TokenMetadataProvider,
        token_analyzer: Optional[TokenAnalyzer] = None,
        token_tracker: Optional[TokenTracker] = None
    ):
        """Initialize query with protocol dependencies."""
        self._token_parser = token_parser
        self._token_metadata_provider = token_metadata_provider
        self._token_analyzer = token_analyzer
        self._token_tracker = token_tracker
    
    async def execute(self, request: GetTokenMetadataRequest) -> GetTokenMetadataResponse:
        """Execute get token metadata query.
        
        Args:
            request: Token metadata request with token and options
            
        Returns:
            Token metadata response with metadata and analysis
            
        Raises:
            AuthenticationFailed: When token metadata cannot be retrieved
            InvalidSignature: When token is malformed
        """
        retrieval_time = datetime.now(timezone.utc)
        
        try:
            # Step 1: Parse token claims
            try:
                token_claims = await self._token_parser.parse_token_claims(request.access_token)
            except Exception as e:
                raise InvalidSignature(
                    "Cannot parse token for metadata extraction",
                    token=str(request.access_token.value)[:20] + "...",
                    details=str(e)
                )
            
            # Step 2: Try to get existing metadata
            token_metadata = await self._token_metadata_provider.get_token_metadata(
                access_token=request.access_token,
                token_claims=token_claims
            )
            
            retrieved_from_cache = token_metadata is not None
            
            # Step 3: Create metadata if not found
            if not token_metadata:
                usage_context = {}
                if request.ip_address:
                    usage_context['ip_address'] = request.ip_address
                if request.user_agent:
                    usage_context['user_agent'] = request.user_agent
                
                token_metadata = await self._token_metadata_provider.create_token_metadata(
                    access_token=request.access_token,
                    token_claims=token_claims,
                    usage_context=usage_context
                )
            
            # Step 4: Record token access if tracking is enabled
            if request.track_access and self._token_tracker:
                try:
                    await self._token_tracker.record_token_access(
                        access_token=request.access_token,
                        ip_address=request.ip_address,
                        user_agent=request.user_agent,
                        access_type="metadata_query"
                    )
                    # Update metadata with new access
                    token_metadata.record_usage(
                        ip_address=request.ip_address,
                        user_agent=request.user_agent
                    )
                except Exception:
                    pass  # Tracking failure doesn't affect metadata retrieval
            
            # Step 5: Perform additional analysis if requested and analyzer available
            usage_analysis = {}
            security_analysis = {}
            
            if self._token_analyzer:
                if request.include_usage_stats:
                    try:
                        usage_analysis = await self._token_analyzer.analyze_token_usage(token_metadata)
                    except Exception:
                        pass  # Analysis failure doesn't affect core functionality
                
                if request.include_security_info:
                    try:
                        security_analysis = await self._token_analyzer.assess_token_security(
                            token_metadata=token_metadata,
                            ip_address=request.ip_address,
                            user_agent=request.user_agent
                        )
                    except Exception:
                        pass  # Analysis failure doesn't affect core functionality
            
            # Step 6: Calculate additional metrics
            token_age_seconds = token_metadata.age_in_seconds
            time_until_expiry_seconds = token_metadata.seconds_until_expiry
            
            # Determine usage frequency
            usage_frequency = self._determine_usage_frequency(
                token_metadata, usage_analysis
            )
            
            # Determine security risk level
            security_risk_level = self._determine_security_risk_level(
                token_metadata, security_analysis
            )
            
            # Step 7: Return metadata response
            return GetTokenMetadataResponse(
                token_metadata=token_metadata,
                retrieved_timestamp=retrieval_time,
                token_age_seconds=token_age_seconds,
                time_until_expiry_seconds=time_until_expiry_seconds,
                usage_frequency=usage_frequency,
                security_risk_level=security_risk_level,
                retrieved_from_cache=retrieved_from_cache,
                metadata_complete=True
            )
            
        except (InvalidSignature, AuthenticationFailed):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            raise AuthenticationFailed(
                "Failed to retrieve token metadata",
                reason="metadata_retrieval_error",
                context={
                    "token": str(request.access_token.value)[:20] + "...",
                    "error": str(e)
                }
            ) from e
    
    def _determine_usage_frequency(
        self, 
        token_metadata: TokenMetadata, 
        usage_analysis: Dict[str, Any]
    ) -> str:
        """Determine token usage frequency category.
        
        Args:
            token_metadata: Token metadata
            usage_analysis: Usage analysis results
            
        Returns:
            Usage frequency category
        """
        if token_metadata.usage_count == 0:
            return "first_use"
        elif token_metadata.usage_count == 1:
            return "second_use"
        
        # Use analysis if available
        if usage_analysis.get('frequency_category'):
            return usage_analysis['frequency_category']
        
        # Calculate based on usage count and age
        if token_metadata.age_in_seconds and token_metadata.age_in_seconds > 0:
            usage_per_minute = token_metadata.usage_count / (token_metadata.age_in_seconds / 60)
            
            if usage_per_minute > 10:
                return "high"
            elif usage_per_minute > 1:
                return "medium"
            else:
                return "low"
        
        # Fallback based on raw count
        if token_metadata.usage_count > 100:
            return "high"
        elif token_metadata.usage_count > 10:
            return "medium"
        else:
            return "low"
    
    def _determine_security_risk_level(
        self, 
        token_metadata: TokenMetadata, 
        security_analysis: Dict[str, Any]
    ) -> str:
        """Determine token security risk level.
        
        Args:
            token_metadata: Token metadata
            security_analysis: Security analysis results
            
        Returns:
            Security risk level
        """
        # Use analysis if available
        if security_analysis.get('risk_level'):
            return security_analysis['risk_level']
        
        # Calculate based on risk indicators
        risk_count = len(token_metadata.risk_indicators)
        
        if risk_count >= 3:
            return "critical"
        elif risk_count >= 2:
            return "high"
        elif risk_count >= 1:
            return "medium"
        else:
            return "low"