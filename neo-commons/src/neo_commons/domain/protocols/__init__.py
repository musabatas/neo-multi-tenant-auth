"""
Domain Protocols - Interface Contracts

Protocol definitions that establish contracts between layers while maintaining
dependency inversion. All protocols are @runtime_checkable for dynamic
type checking and dependency injection.
"""

from neo_commons.domain.protocols.auth_protocols import (
    AuthServiceProtocol,
    PermissionServiceProtocol
)

__all__ = [
    "AuthServiceProtocol",
    "PermissionServiceProtocol"
]