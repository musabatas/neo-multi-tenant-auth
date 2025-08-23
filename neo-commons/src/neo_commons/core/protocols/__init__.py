"""Protocols module - MOVED TO SHARED AND INFRASTRUCTURE.

Protocols have been moved per Clean Core architecture:

Domain Protocols (shared concerns):
- from neo_commons.core.shared import TenantContextProtocol, UserIdentityProtocol, etc.

Infrastructure Protocols:
- from neo_commons.infrastructure.protocols import DatabaseConnectionProtocol, CacheProtocol, etc.

This prevents circular dependencies and enforces proper separation of concerns.
"""

# Core protocols directory is intentionally empty per Clean Core pattern