"""Platform events infrastructure implementations.

Infrastructure layer provides external implementations for platform events system.
Following maximum separation architecture patterns.

Each implementation file has single responsibility:
- repositories/: Data access implementations (PostgreSQL, Redis, etc.)
- adapters/: External service integrations (HTTP, email, etc.)
- handlers/: Platform action handler implementations
- queues/: Message queue implementations
"""

# Infrastructure implementations will be imported as they are created