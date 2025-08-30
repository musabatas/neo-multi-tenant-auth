"""Check session active query."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, Dict, Any
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import SessionId, RealmIdentifier
from ...core.entities import AuthSession
from ...core.exceptions import SessionInvalid


@dataclass
class CheckSessionActiveRequest:
    """Request to check if session is active."""
    
    session_id: SessionId
    user_id: Optional[UserId] = None
    tenant_id: Optional[TenantId] = None
    
    # Validation options
    check_expiration: bool = True
    check_inactivity: bool = True
    update_last_activity: bool = False
    
    # Activity context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    activity_type: str = "api_call"  # api_call, page_view, action


@dataclass
class CheckSessionActiveResponse:
    """Response from session active check."""
    
    is_active: bool
    session: Optional[AuthSession] = None
    check_timestamp: datetime = None
    
    # Status details
    exists: bool = False
    is_expired: bool = False
    is_inactive: bool = False
    is_revoked: bool = False
    
    # Activity information
    seconds_until_expiry: Optional[int] = None
    seconds_since_activity: Optional[int] = None
    activity_updated: bool = False
    
    # Failure information
    failure_reason: Optional[str] = None
    failure_details: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize response after creation."""
        if self.check_timestamp is None:
            object.__setattr__(self, 'check_timestamp', datetime.now(timezone.utc))
        
        if self.failure_details is None:
            object.__setattr__(self, 'failure_details', {})


@runtime_checkable
class SessionProvider(Protocol):
    """Protocol for session data operations."""
    
    async def get_session(
        self,
        session_id: SessionId,
        user_id: Optional[UserId] = None
    ) -> Optional[AuthSession]:
        """Get session by ID."""
        ...
    
    async def update_session_activity(
        self,
        session_id: SessionId,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        activity_type: str = "api_call"
    ) -> bool:
        """Update session last activity."""
        ...


@runtime_checkable
class SessionValidator(Protocol):
    """Protocol for session validation operations."""
    
    async def is_session_expired(self, session: AuthSession) -> bool:
        """Check if session is expired."""
        ...
    
    async def is_session_inactive(
        self,
        session: AuthSession,
        inactivity_threshold_seconds: Optional[int] = None
    ) -> bool:
        """Check if session is inactive."""
        ...
    
    async def get_session_expiry_info(self, session: AuthSession) -> Dict[str, Any]:
        """Get session expiry information."""
        ...


class CheckSessionActive:
    """Query to check session active status following maximum separation principle.
    
    Handles ONLY session active checking workflow orchestration.
    Does not handle session storage, expiration calculation, or activity tracking.
    """
    
    def __init__(
        self,
        session_provider: SessionProvider,
        session_validator: SessionValidator
    ):
        """Initialize query with protocol dependencies."""
        self._session_provider = session_provider
        self._session_validator = session_validator
    
    async def execute(self, request: CheckSessionActiveRequest) -> CheckSessionActiveResponse:
        """Execute check session active query.
        
        Args:
            request: Session check request with session ID and options
            
        Returns:
            Session active response with status details
        """
        check_time = datetime.now(timezone.utc)
        
        # Initialize response with defaults
        response = CheckSessionActiveResponse(
            is_active=False,
            check_timestamp=check_time
        )
        
        try:
            # Step 1: Retrieve session
            session = await self._session_provider.get_session(
                session_id=request.session_id,
                user_id=request.user_id
            )
            
            if not session:
                response.failure_reason = "session_not_found"
                response.failure_details = {
                    "session_id": str(request.session_id.value),
                    "user_id": str(request.user_id.value) if request.user_id else None
                }
                return response
            
            response.exists = True
            response.session = session
            
            # Step 2: Check if session is revoked
            if not session.is_active or session.revoked_at:
                response.is_revoked = True
                response.failure_reason = "session_revoked"
                response.failure_details = {
                    "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
                    "revoke_reason": session.revoke_reason
                }
                return response
            
            # Step 3: Check expiration if requested
            if request.check_expiration:
                is_expired = await self._session_validator.is_session_expired(session)
                response.is_expired = is_expired
                
                if is_expired:
                    response.failure_reason = "session_expired"
                    expiry_info = await self._session_validator.get_session_expiry_info(session)
                    response.failure_details = expiry_info
                    return response
                
                # Get expiry information for active session
                expiry_info = await self._session_validator.get_session_expiry_info(session)
                response.seconds_until_expiry = expiry_info.get('seconds_until_expiry')
            
            # Step 4: Check inactivity if requested
            if request.check_inactivity:
                is_inactive = await self._session_validator.is_session_inactive(session)
                response.is_inactive = is_inactive
                response.seconds_since_activity = session.seconds_since_activity
                
                if is_inactive:
                    response.failure_reason = "session_inactive"
                    response.failure_details = {
                        "last_activity_at": session.last_activity_at.isoformat() if session.last_activity_at else None,
                        "seconds_since_activity": session.seconds_since_activity,
                        "inactivity_threshold": 1800  # Could be configurable
                    }
                    return response
            
            # Step 5: Update activity if requested
            if request.update_last_activity:
                try:
                    activity_updated = await self._session_provider.update_session_activity(
                        session_id=request.session_id,
                        ip_address=request.ip_address,
                        user_agent=request.user_agent,
                        activity_type=request.activity_type
                    )
                    response.activity_updated = activity_updated
                    
                    # Update session object for response
                    if activity_updated:
                        session.update_activity(extend_expiry=False)
                        
                except Exception as e:
                    # Activity update failure doesn't invalidate session
                    response.failure_details["activity_update_error"] = str(e)
            
            # Step 6: Validate user ownership if provided
            if request.user_id and session.user_id != request.user_id:
                response.failure_reason = "session_user_mismatch"
                response.failure_details = {
                    "session_user_id": str(session.user_id.value),
                    "request_user_id": str(request.user_id.value)
                }
                return response
            
            # Step 7: Validate tenant context if provided
            if request.tenant_id and session.tenant_id != request.tenant_id:
                response.failure_reason = "session_tenant_mismatch"
                response.failure_details = {
                    "session_tenant_id": str(session.tenant_id.value) if session.tenant_id else None,
                    "request_tenant_id": str(request.tenant_id.value)
                }
                return response
            
            # Step 8: Session is active
            response.is_active = True
            return response
            
        except Exception as e:
            # Unexpected error during session check
            response.failure_reason = "session_check_error"
            response.failure_details = {"error": str(e)}
            return response