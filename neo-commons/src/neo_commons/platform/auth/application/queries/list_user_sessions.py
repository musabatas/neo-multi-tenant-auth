"""List user sessions query."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, List, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import SessionId, RealmIdentifier
from ...core.entities import AuthSession
from ...core.exceptions import AuthenticationFailed


@dataclass
class ListUserSessionsRequest:
    """Request to list user sessions."""
    
    user_id: UserId
    tenant_id: Optional[TenantId] = None
    realm_id: Optional[RealmIdentifier] = None
    
    # Filtering options
    active_only: bool = True
    include_expired: bool = False
    include_revoked: bool = False
    
    # Pagination options
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    
    # Sorting options
    sort_by: str = "last_activity_at"  # created_at, last_activity_at, expires_at
    sort_order: str = "desc"  # asc, desc
    
    # Additional data options
    include_device_info: bool = True
    include_risk_info: bool = False
    include_metadata: bool = False


@dataclass
class SessionSummary:
    """Summary information for a session."""
    
    session_id: SessionId
    created_at: datetime
    last_activity_at: datetime
    expires_at: Optional[datetime]
    
    # Status
    is_active: bool
    is_expired: bool
    is_current: bool = False
    
    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Dict[str, Any] = None
    
    # Risk information
    risk_score: Optional[float] = None
    risk_indicators: List[str] = None
    
    # Activity
    session_duration_seconds: Optional[int] = None
    seconds_since_activity: Optional[int] = None
    
    def __post_init__(self):
        """Initialize summary after creation."""
        if self.device_info is None:
            object.__setattr__(self, 'device_info', {})
        
        if self.risk_indicators is None:
            object.__setattr__(self, 'risk_indicators', [])


@dataclass
class ListUserSessionsResponse:
    """Response from list user sessions query."""
    
    user_id: UserId
    sessions: List[SessionSummary]
    retrieved_timestamp: datetime
    
    # Pagination information
    total_count: int
    returned_count: int
    has_more: bool = False
    next_offset: Optional[int] = None
    
    # Summary statistics
    active_sessions: int = 0
    expired_sessions: int = 0
    revoked_sessions: int = 0
    high_risk_sessions: int = 0
    
    def __post_init__(self):
        """Initialize response after creation."""
        if self.retrieved_timestamp is None:
            object.__setattr__(self, 'retrieved_timestamp', datetime.now(timezone.utc))


@runtime_checkable
class SessionProvider(Protocol):
    """Protocol for session data operations."""
    
    async def list_user_sessions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        active_only: bool = True,
        include_expired: bool = False,
        include_revoked: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_by: str = "last_activity_at",
        sort_order: str = "desc"
    ) -> List[AuthSession]:
        """List user sessions with filtering and pagination."""
        ...
    
    async def count_user_sessions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        active_only: bool = True,
        include_expired: bool = False,
        include_revoked: bool = False
    ) -> int:
        """Count user sessions matching criteria."""
        ...


@runtime_checkable
class SessionAnalyzer(Protocol):
    """Protocol for session analysis operations."""
    
    async def analyze_session_risk(self, session: AuthSession) -> Dict[str, Any]:
        """Analyze session risk factors."""
        ...
    
    async def determine_current_session(
        self,
        sessions: List[AuthSession],
        request_context: Dict[str, Any]
    ) -> Optional[SessionId]:
        """Determine which session is the current one."""
        ...


class ListUserSessions:
    """Query to list user sessions following maximum separation principle.
    
    Handles ONLY user session listing workflow orchestration.
    Does not handle session storage, filtering logic, or risk analysis.
    """
    
    def __init__(
        self,
        session_provider: SessionProvider,
        session_analyzer: Optional[SessionAnalyzer] = None
    ):
        """Initialize query with protocol dependencies."""
        self._session_provider = session_provider
        self._session_analyzer = session_analyzer
    
    async def execute(self, request: ListUserSessionsRequest) -> ListUserSessionsResponse:
        """Execute list user sessions query.
        
        Args:
            request: List sessions request with user ID and options
            
        Returns:
            List sessions response with session summaries
            
        Raises:
            AuthenticationFailed: When sessions cannot be retrieved
        """
        retrieval_time = datetime.now(timezone.utc)
        
        try:
            # Step 1: Get total count for pagination
            total_count = await self._session_provider.count_user_sessions(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                active_only=request.active_only,
                include_expired=request.include_expired,
                include_revoked=request.include_revoked
            )
            
            # Step 2: Retrieve sessions
            sessions = await self._session_provider.list_user_sessions(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                active_only=request.active_only,
                include_expired=request.include_expired,
                include_revoked=request.include_revoked,
                limit=request.limit,
                offset=request.offset,
                sort_by=request.sort_by,
                sort_order=request.sort_order
            )
            
            # Step 3: Determine current session if analyzer available
            current_session_id = None
            if self._session_analyzer and sessions:
                request_context = {
                    "user_id": request.user_id,
                    "tenant_id": request.tenant_id,
                    "realm_id": request.realm_id
                }
                current_session_id = await self._session_analyzer.determine_current_session(
                    sessions=sessions,
                    request_context=request_context
                )
            
            # Step 4: Convert to session summaries
            session_summaries = []
            active_count = 0
            expired_count = 0
            revoked_count = 0
            high_risk_count = 0
            
            for session in sessions:
                # Create basic summary
                summary = SessionSummary(
                    session_id=session.session_id,
                    created_at=session.created_at,
                    last_activity_at=session.last_activity_at,
                    expires_at=session.expires_at,
                    is_active=session.is_active,
                    is_expired=session.is_expired,
                    is_current=session.session_id == current_session_id,
                    session_duration_seconds=session.session_duration_seconds,
                    seconds_since_activity=session.seconds_since_activity
                )
                
                # Add device info if requested
                if request.include_device_info:
                    summary.ip_address = session.ip_address
                    summary.user_agent = session.user_agent
                    summary.device_info = session.device_info or {}
                
                # Add risk info if requested and analyzer available
                if request.include_risk_info and self._session_analyzer:
                    try:
                        risk_analysis = await self._session_analyzer.analyze_session_risk(session)
                        summary.risk_score = risk_analysis.get('risk_score', session.risk_score)
                        summary.risk_indicators = risk_analysis.get('risk_indicators', [])
                    except Exception:
                        # Risk analysis failure doesn't prevent listing
                        summary.risk_score = session.risk_score
                        summary.risk_indicators = []
                else:
                    summary.risk_score = session.risk_score
                    summary.risk_indicators = []
                
                session_summaries.append(summary)
                
                # Update statistics
                if session.is_active:
                    active_count += 1
                elif session.is_expired:
                    expired_count += 1
                elif session.revoked_at:
                    revoked_count += 1
                
                if summary.risk_score and summary.risk_score >= 0.7:
                    high_risk_count += 1
            
            # Step 5: Calculate pagination info
            returned_count = len(session_summaries)
            has_more = (request.offset or 0) + returned_count < total_count
            next_offset = None
            
            if has_more and request.limit:
                next_offset = (request.offset or 0) + returned_count
            
            # Step 6: Return response
            return ListUserSessionsResponse(
                user_id=request.user_id,
                sessions=session_summaries,
                retrieved_timestamp=retrieval_time,
                total_count=total_count,
                returned_count=returned_count,
                has_more=has_more,
                next_offset=next_offset,
                active_sessions=active_count,
                expired_sessions=expired_count,
                revoked_sessions=revoked_count,
                high_risk_sessions=high_risk_count
            )
            
        except Exception as e:
            raise AuthenticationFailed(
                "Failed to retrieve user sessions",
                reason="session_list_error",
                context={
                    "user_id": str(request.user_id.value),
                    "tenant_id": str(request.tenant_id.value) if request.tenant_id else None,
                    "error": str(e)
                }
            ) from e