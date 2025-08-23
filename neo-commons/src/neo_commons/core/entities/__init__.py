"""Entities module - MOVED TO FEATURES.

Entities have been moved to feature-specific modules per Clean Core architecture.
Access entities directly from their feature modules:

- User: from neo_commons.features.users.entities import User
- Organization: from neo_commons.features.organizations.entities import Organization  
- Tenant: from neo_commons.features.tenants.entities import Tenant
- Permission: from neo_commons.features.permissions.entities import Permission
- Role: from neo_commons.features.permissions.entities import Role
- Team: from neo_commons.features.teams.entities import Team

This prevents circular dependencies and enforces proper separation of concerns.
"""

# Core entities directory is intentionally empty per Clean Core pattern