"""Neo-Commons Platform Modules.

This package contains enterprise-grade platform modules that provide
core infrastructure functionality for the NeoMultiTenant platform.

Modules:
- actions: Action execution system with configurable triggers and handlers
- events: Event-driven architecture with dispatching and lifecycle management

Each module follows maximum separation architecture with:
- Clean domain entities and value objects
- Protocol-based dependency injection  
- Comprehensive application services
- Infrastructure adapters and repositories
- Role-based API components
"""

# Re-export core components from each platform module
from . import actions
from . import events

__all__ = [
    "actions",
    "events",
]