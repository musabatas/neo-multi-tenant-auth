"""Authentication application layer.

Application layer for authentication platform following maximum separation.
Each component handles exactly one use case with clean dependencies.

Components:
- commands: Write operations (authentication, logout, token operations)
- queries: Read operations (validation, context retrieval, session checks)
- validators: Focused validation logic for specific concerns
- handlers: Event handlers for authentication lifecycle
- services: Orchestration services for complex workflows
- protocols: Application-level contracts for infrastructure dependencies

Architecture:
- Command/Query separation
- Single responsibility per file
- Protocol-based dependencies
- Event-driven workflows
"""

# Application components exports
from .commands import (
    AuthenticateUser,
    LogoutUser,
    RefreshTokenCommand,
    RevokeToken,
    InvalidateSession,
)

from .queries import (
    ValidateToken,
    GetUserContext,
    CheckSessionActive,
    GetTokenMetadata,
    ListUserSessions,
)

from .validators import (
    TokenFormatValidator,
    SignatureValidator,
    ExpirationValidator,
    AudienceValidator,
    FreshnessValidator,
)

__all__ = [
    # Commands
    "AuthenticateUser",
    "LogoutUser",
    "RefreshTokenCommand", 
    "RevokeToken",
    "InvalidateSession",
    
    # Queries
    "ValidateToken",
    "GetUserContext",
    "CheckSessionActive",
    "GetTokenMetadata",
    "ListUserSessions",
    
    # Validators
    "TokenFormatValidator",
    "SignatureValidator",
    "ExpirationValidator",
    "AudienceValidator", 
    "FreshnessValidator",
]