"""
Core protocols and contracts for the NeoMultiTenant platform.

This module defines foundational protocols that establish contracts between
different modules and layers of the application. These protocols enable
clean architecture principles and dependency injection.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ValueObjectProtocol(Protocol):
    """
    Protocol for value objects in the domain model.
    
    Value objects are immutable objects that represent conceptual values
    and are compared by their attributes rather than identity.
    """
    
    def __eq__(self, other: Any) -> bool:
        """Value objects are equal if all their attributes are equal."""
        ...
    
    def __hash__(self) -> int:
        """Value objects must be hashable since they're immutable."""
        ...


@runtime_checkable
class EntityProtocol(Protocol):
    """
    Protocol for domain entities.
    
    Entities have identity and are compared by their unique identifier
    rather than their attributes.
    """
    
    @property
    @abstractmethod
    def id(self) -> Any:
        """The unique identifier of the entity."""
        ...
    
    def __eq__(self, other: Any) -> bool:
        """Entities are equal if they have the same type and ID."""
        ...


@runtime_checkable
class AggregateRootProtocol(EntityProtocol, Protocol):
    """
    Protocol for aggregate roots in domain-driven design.
    
    Aggregate roots are entities that serve as entry points to aggregates
    and are responsible for maintaining consistency within the aggregate.
    """
    
    @property
    @abstractmethod
    def version(self) -> int:
        """Version number for optimistic concurrency control."""
        ...
    
    @property
    @abstractmethod
    def domain_events(self) -> List["DomainEventProtocol"]:
        """List of domain events raised by this aggregate."""
        ...
    
    @abstractmethod
    def clear_domain_events(self) -> None:
        """Clear the list of domain events after they've been published."""
        ...


@runtime_checkable
class DomainEventProtocol(Protocol):
    """
    Protocol for domain events.
    
    Domain events represent something important that happened in the domain
    and are used to trigger side effects or notify other bounded contexts.
    """
    
    @property
    @abstractmethod
    def event_id(self) -> str:
        """Unique identifier for this event."""
        ...
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Type of the event (e.g., 'UserCreated', 'TenantActivated')."""
        ...
    
    @property
    @abstractmethod
    def aggregate_id(self) -> str:
        """ID of the aggregate that raised this event."""
        ...
    
    @property
    @abstractmethod
    def aggregate_type(self) -> str:
        """Type of the aggregate that raised this event."""
        ...
    
    @property
    @abstractmethod
    def occurred_on(self) -> datetime:
        """When the event occurred."""
        ...
    
    @property
    @abstractmethod
    def event_data(self) -> Dict[str, Any]:
        """Event-specific data payload."""
        ...


@runtime_checkable
class DomainServiceProtocol(Protocol):
    """
    Protocol for domain services.
    
    Domain services encapsulate domain logic that doesn't naturally fit
    within a single entity or value object.
    """
    pass


@runtime_checkable
class RepositoryProtocol(Protocol):
    """
    Protocol for repositories in the domain layer.
    
    Repositories provide a collection-like interface for accessing
    domain objects, abstracting away persistence concerns.
    """
    
    @abstractmethod
    async def find_by_id(self, entity_id: Any) -> Optional[Any]:
        """Find an entity by its unique identifier."""
        ...
    
    @abstractmethod
    async def save(self, entity: Any) -> Any:
        """Save an entity to the repository."""
        ...
    
    @abstractmethod
    async def delete(self, entity: Any) -> None:
        """Delete an entity from the repository."""
        ...


@runtime_checkable
class UnitOfWorkProtocol(Protocol):
    """
    Protocol for unit of work pattern.
    
    Unit of work maintains a list of objects affected by a business transaction
    and coordinates writing out changes and resolving concurrency problems.
    """
    
    @abstractmethod
    async def __aenter__(self) -> "UnitOfWorkProtocol":
        """Enter the unit of work context."""
        ...
    
    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the unit of work context, committing or rolling back."""
        ...
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit all changes in this unit of work."""
        ...
    
    @abstractmethod
    async def rollback(self) -> None:
        """Roll back all changes in this unit of work."""
        ...


@runtime_checkable
class EventPublisherProtocol(Protocol):
    """
    Protocol for publishing domain events.
    
    Event publishers are responsible for dispatching domain events to
    appropriate handlers, either synchronously or asynchronously.
    """
    
    @abstractmethod
    async def publish(self, event: DomainEventProtocol) -> None:
        """Publish a single domain event."""
        ...
    
    @abstractmethod
    async def publish_many(self, events: List[DomainEventProtocol]) -> None:
        """Publish multiple domain events."""
        ...


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """
    Protocol for domain event handlers.
    
    Event handlers process domain events and implement side effects or
    cross-aggregate consistency.
    """
    
    @property
    @abstractmethod
    def handles_event_types(self) -> List[str]:
        """List of event types this handler can process."""
        ...
    
    @abstractmethod
    async def handle(self, event: DomainEventProtocol) -> None:
        """Handle a domain event."""
        ...


@runtime_checkable
class SpecificationProtocol(Protocol):
    """
    Protocol for specifications in domain-driven design.
    
    Specifications encapsulate business rules and can be used for validation,
    querying, and in-memory filtering.
    """
    
    @abstractmethod
    def is_satisfied_by(self, candidate: Any) -> bool:
        """Check if the candidate satisfies this specification."""
        ...
    
    def and_(self, other: "SpecificationProtocol") -> "SpecificationProtocol":
        """Combine this specification with another using AND logic."""
        return AndSpecification(self, other)
    
    def or_(self, other: "SpecificationProtocol") -> "SpecificationProtocol":
        """Combine this specification with another using OR logic."""
        return OrSpecification(self, other)
    
    def not_(self) -> "SpecificationProtocol":
        """Negate this specification."""
        return NotSpecification(self)


class AndSpecification:
    """Combines two specifications with AND logic."""
    
    def __init__(self, left: SpecificationProtocol, right: SpecificationProtocol):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate: Any) -> bool:
        return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)


class OrSpecification:
    """Combines two specifications with OR logic."""
    
    def __init__(self, left: SpecificationProtocol, right: SpecificationProtocol):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate: Any) -> bool:
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)


class NotSpecification:
    """Negates a specification."""
    
    def __init__(self, spec: SpecificationProtocol):
        self.spec = spec
    
    def is_satisfied_by(self, candidate: Any) -> bool:
        return not self.spec.is_satisfied_by(candidate)