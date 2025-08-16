"""
Domain Layer - Enterprise Business Rules

This layer contains the most general and high-level rules. These are the rules
that would be used by many different applications, even if the databases,
UIs, or frameworks change completely.

Contains:
- Entities: Core business objects that embody enterprise-wide business rules
- Value Objects: Immutable objects that are defined by their attributes
- Protocols: Interface contracts that define domain boundaries

Note: Protocols will be added as components are migrated in future phases.
"""

# No exports yet - protocols will be added as they're migrated
__all__ = []