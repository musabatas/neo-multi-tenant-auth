"""
Event processing extension interface.

ONLY handles event extension contracts and customization points.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass

from ....core.value_objects import EventId, TenantId, EventType


@dataclass
class EventExtensionContext:
    """Context provided to event extensions."""
    event_id: EventId
    tenant_id: TenantId
    event_type: EventType
    event_data: Dict[str, Any]
    metadata: Dict[str, Any]
    processing_stage: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id.value,
            "tenant_id": self.tenant_id.value,
            "event_type": self.event_type.value,
            "event_data": self.event_data,
            "metadata": self.metadata,
            "processing_stage": self.processing_stage,
        }


@dataclass
class EventExtensionResult:
    """Result from event extension processing."""
    continue_processing: bool = True
    modified_data: Optional[Dict[str, Any]] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "continue_processing": self.continue_processing,
            "modified_data": self.modified_data,
            "additional_metadata": self.additional_metadata,
            "error_message": self.error_message,
        }


class EventExtension(ABC):
    """
    Abstract base class for event processing extensions.
    
    Extensions can modify, validate, or react to event processing.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Extension name."""
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        """Extension version."""
        pass
        
    @property
    @abstractmethod
    def supported_event_types(self) -> List[str]:
        """List of supported event types (empty list means all types)."""
        pass
        
    @property
    @abstractmethod
    def processing_stages(self) -> List[str]:
        """List of processing stages this extension handles."""
        pass
        
    @property
    def priority(self) -> int:
        """
        Extension priority (lower numbers run first).
        
        Returns:
            Priority value (0-1000, default 500)
        """
        return 500
        
    @property
    def enabled(self) -> bool:
        """Whether this extension is enabled."""
        return True
        
    @abstractmethod
    async def process_event(
        self,
        context: EventExtensionContext
    ) -> EventExtensionResult:
        """
        Process an event at a specific stage.
        
        Args:
            context: Event processing context
            
        Returns:
            EventExtensionResult indicating processing outcome
        """
        pass
        
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate extension configuration.
        
        Args:
            config: Extension configuration
            
        Returns:
            True if configuration is valid
        """
        return True
        
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the extension with configuration.
        
        Args:
            config: Extension configuration
        """
        pass
        
    async def cleanup(self) -> None:
        """Clean up extension resources."""
        pass
        
    def supports_event_type(self, event_type: str) -> bool:
        """
        Check if extension supports a specific event type.
        
        Args:
            event_type: Event type to check
            
        Returns:
            True if event type is supported
        """
        if not self.supported_event_types:
            return True  # Empty list means all types supported
            
        return event_type in self.supported_event_types
        
    def supports_processing_stage(self, stage: str) -> bool:
        """
        Check if extension supports a specific processing stage.
        
        Args:
            stage: Processing stage to check
            
        Returns:
            True if stage is supported
        """
        return stage in self.processing_stages
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get extension metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "supported_event_types": self.supported_event_types,
            "processing_stages": self.processing_stages,
            "priority": self.priority,
            "enabled": self.enabled,
        }


class EventValidationExtension(EventExtension):
    """
    Specialized extension for event validation.
    
    Provides additional validation-specific methods.
    """
    
    @property
    def processing_stages(self) -> List[str]:
        """Validation extensions run at pre_validation and post_validation stages."""
        return ["pre_validation", "post_validation"]
        
    @abstractmethod
    async def validate_event_data(
        self,
        event_type: EventType,
        event_data: Dict[str, Any],
        tenant_id: TenantId
    ) -> List[str]:
        """
        Validate event data and return list of validation errors.
        
        Args:
            event_type: Type of event
            event_data: Event payload data
            tenant_id: Tenant context
            
        Returns:
            List of validation error messages (empty if valid)
        """
        pass
        
    async def process_event(
        self,
        context: EventExtensionContext
    ) -> EventExtensionResult:
        """Process event using validation logic."""
        errors = await self.validate_event_data(
            context.event_type,
            context.event_data,
            context.tenant_id
        )
        
        if errors:
            return EventExtensionResult(
                continue_processing=False,
                error_message="; ".join(errors)
            )
            
        return EventExtensionResult(continue_processing=True)


class EventTransformationExtension(EventExtension):
    """
    Specialized extension for event data transformation.
    
    Provides transformation-specific methods.
    """
    
    @property
    def processing_stages(self) -> List[str]:
        """Transformation extensions run at pre_processing and post_processing stages."""
        return ["pre_processing", "post_processing"]
        
    @abstractmethod
    async def transform_event_data(
        self,
        event_type: EventType,
        event_data: Dict[str, Any],
        tenant_id: TenantId
    ) -> Dict[str, Any]:
        """
        Transform event data.
        
        Args:
            event_type: Type of event
            event_data: Original event data
            tenant_id: Tenant context
            
        Returns:
            Transformed event data
        """
        pass
        
    async def process_event(
        self,
        context: EventExtensionContext
    ) -> EventExtensionResult:
        """Process event using transformation logic."""
        try:
            transformed_data = await self.transform_event_data(
                context.event_type,
                context.event_data,
                context.tenant_id
            )
            
            return EventExtensionResult(
                continue_processing=True,
                modified_data=transformed_data
            )
            
        except Exception as e:
            return EventExtensionResult(
                continue_processing=False,
                error_message=f"Transformation failed: {str(e)}"
            )


class EventEnrichmentExtension(EventExtension):
    """
    Specialized extension for event data enrichment.
    
    Adds additional data or metadata to events.
    """
    
    @property
    def processing_stages(self) -> List[str]:
        """Enrichment extensions run at enrichment stage."""
        return ["enrichment"]
        
    @abstractmethod
    async def enrich_event_data(
        self,
        context: EventExtensionContext
    ) -> Dict[str, Any]:
        """
        Enrich event with additional data.
        
        Args:
            context: Event processing context
            
        Returns:
            Additional data to merge with event
        """
        pass
        
    async def process_event(
        self,
        context: EventExtensionContext
    ) -> EventExtensionResult:
        """Process event using enrichment logic."""
        try:
            enrichment_data = await self.enrich_event_data(context)
            
            # Merge enrichment data with existing event data
            enriched_data = context.event_data.copy()
            enriched_data.update(enrichment_data)
            
            return EventExtensionResult(
                continue_processing=True,
                modified_data=enriched_data
            )
            
        except Exception as e:
            return EventExtensionResult(
                continue_processing=False,
                error_message=f"Enrichment failed: {str(e)}"
            )


# Protocol for event extension factories
class EventExtensionFactory(Protocol):
    """Protocol for creating event extensions."""
    
    def create_extension(
        self,
        extension_type: str,
        config: Dict[str, Any]
    ) -> EventExtension:
        """Create an extension instance."""
        ...
        
    def list_available_extensions(self) -> List[Dict[str, Any]]:
        """List available extension types."""
        ...