"""
Event plugin interface and implementations.

ONLY handles event-specific plugin contracts and lifecycle.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ....core.value_objects import EventId, TenantId, EventType


class EventPluginCapability(Enum):
    """Event plugin capabilities."""
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    ENRICHMENT = "enrichment"
    FILTERING = "filtering"
    ROUTING = "routing"
    MONITORING = "monitoring"
    ARCHIVING = "archiving"


@dataclass
class EventPluginContext:
    """Context provided to event plugins."""
    event_id: EventId
    tenant_id: TenantId
    event_type: EventType
    event_data: Dict[str, Any]
    metadata: Dict[str, Any]
    plugin_config: Dict[str, Any]
    processing_stage: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id.value,
            "tenant_id": self.tenant_id.value,
            "event_type": self.event_type.value,
            "event_data": self.event_data,
            "metadata": self.metadata,
            "plugin_config": self.plugin_config,
            "processing_stage": self.processing_stage,
        }


@dataclass
class EventPluginResult:
    """Result from event plugin processing."""
    success: bool = True
    continue_processing: bool = True
    modified_event_data: Optional[Dict[str, Any]] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "continue_processing": self.continue_processing,
            "modified_event_data": self.modified_event_data,
            "additional_metadata": self.additional_metadata,
            "error_message": self.error_message,
        }


class EventPlugin(ABC):
    """
    Abstract base class for event processing plugins.
    
    Provides pluggable event processing capabilities.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name for identification."""
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass
        
    @property
    @abstractmethod
    def capabilities(self) -> List[EventPluginCapability]:
        """List of plugin capabilities."""
        pass
        
    @property
    @abstractmethod
    def supported_event_types(self) -> List[str]:
        """List of supported event types (empty list means all types)."""
        pass
        
    @property
    def priority(self) -> int:
        """
        Plugin priority (lower numbers run first).
        
        Returns:
            Priority value (0-1000, default 500)
        """
        return 500
        
    @property
    def enabled(self) -> bool:
        """Whether this plugin is enabled."""
        return True
        
    @abstractmethod
    async def process_event(
        self,
        context: EventPluginContext
    ) -> EventPluginResult:
        """
        Process an event.
        
        Args:
            context: Event processing context
            
        Returns:
            EventPluginResult indicating processing outcome
        """
        pass
        
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.
        
        Args:
            config: Plugin configuration
            
        Returns:
            True if configuration is valid
        """
        return True
        
    async def initialize(
        self,
        config: Dict[str, Any],
        tenant_id: Optional[TenantId] = None
    ) -> None:
        """
        Initialize the plugin with configuration.
        
        Args:
            config: Plugin configuration
            tenant_id: Optional tenant context
        """
        pass
        
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass
        
    def supports_event_type(self, event_type: str) -> bool:
        """
        Check if plugin supports a specific event type.
        
        Args:
            event_type: Event type to check
            
        Returns:
            True if event type is supported
        """
        if not self.supported_event_types:
            return True  # Empty list means all types supported
            
        return event_type in self.supported_event_types
        
    def has_capability(self, capability: EventPluginCapability) -> bool:
        """
        Check if plugin has a specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            True if plugin has the capability
        """
        return capability in self.capabilities
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": [cap.value for cap in self.capabilities],
            "supported_event_types": self.supported_event_types,
            "priority": self.priority,
            "enabled": self.enabled,
        }


class EventValidationPlugin(EventPlugin):
    """
    Specialized plugin for event validation.
    
    Validates event structure and content.
    """
    
    @property
    def capabilities(self) -> List[EventPluginCapability]:
        """Validation plugins have validation capability."""
        return [EventPluginCapability.VALIDATION]
        
    @abstractmethod
    async def validate_event_structure(
        self,
        event_data: Dict[str, Any],
        event_type: EventType
    ) -> List[str]:
        """
        Validate event structure.
        
        Args:
            event_data: Event data to validate
            event_type: Type of event
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
        
    async def process_event(
        self,
        context: EventPluginContext
    ) -> EventPluginResult:
        """Process event using validation logic."""
        try:
            validation_errors = await self.validate_event_structure(
                context.event_data,
                context.event_type
            )
            
            if validation_errors:
                return EventPluginResult(
                    success=False,
                    continue_processing=False,
                    error_message=f"Validation failed: {'; '.join(validation_errors)}"
                )
                
            return EventPluginResult(
                success=True,
                continue_processing=True,
                additional_metadata={"validated_by": self.name}
            )
            
        except Exception as e:
            return EventPluginResult(
                success=False,
                continue_processing=True,  # Continue despite plugin failure
                error_message=f"Validation plugin error: {str(e)}"
            )


class EventTransformationPlugin(EventPlugin):
    """
    Specialized plugin for event transformation.
    
    Transforms event data before processing.
    """
    
    @property
    def capabilities(self) -> List[EventPluginCapability]:
        """Transformation plugins have transformation capability."""
        return [EventPluginCapability.TRANSFORMATION]
        
    @abstractmethod
    async def transform_event_data(
        self,
        event_data: Dict[str, Any],
        event_type: EventType,
        tenant_id: TenantId
    ) -> Dict[str, Any]:
        """
        Transform event data.
        
        Args:
            event_data: Original event data
            event_type: Type of event
            tenant_id: Tenant context
            
        Returns:
            Transformed event data
        """
        pass
        
    async def process_event(
        self,
        context: EventPluginContext
    ) -> EventPluginResult:
        """Process event using transformation logic."""
        try:
            transformed_data = await self.transform_event_data(
                context.event_data,
                context.event_type,
                context.tenant_id
            )
            
            return EventPluginResult(
                success=True,
                continue_processing=True,
                modified_event_data=transformed_data,
                additional_metadata={"transformed_by": self.name}
            )
            
        except Exception as e:
            return EventPluginResult(
                success=False,
                continue_processing=True,  # Continue with original data
                error_message=f"Transformation plugin error: {str(e)}"
            )


class EventEnrichmentPlugin(EventPlugin):
    """
    Specialized plugin for event enrichment.
    
    Adds additional data to events.
    """
    
    @property
    def capabilities(self) -> List[EventPluginCapability]:
        """Enrichment plugins have enrichment capability."""
        return [EventPluginCapability.ENRICHMENT]
        
    @abstractmethod
    async def enrich_event_data(
        self,
        event_data: Dict[str, Any],
        event_type: EventType,
        tenant_id: TenantId
    ) -> Dict[str, Any]:
        """
        Enrich event data with additional information.
        
        Args:
            event_data: Original event data
            event_type: Type of event
            tenant_id: Tenant context
            
        Returns:
            Additional data to merge with event
        """
        pass
        
    async def process_event(
        self,
        context: EventPluginContext
    ) -> EventPluginResult:
        """Process event using enrichment logic."""
        try:
            enrichment_data = await self.enrich_event_data(
                context.event_data,
                context.event_type,
                context.tenant_id
            )
            
            # Merge enrichment data with original event data
            enriched_data = context.event_data.copy()
            enriched_data.update(enrichment_data)
            
            return EventPluginResult(
                success=True,
                continue_processing=True,
                modified_event_data=enriched_data,
                additional_metadata={"enriched_by": self.name}
            )
            
        except Exception as e:
            return EventPluginResult(
                success=False,
                continue_processing=True,  # Continue with original data
                error_message=f"Enrichment plugin error: {str(e)}"
            )


class EventFilteringPlugin(EventPlugin):
    """
    Specialized plugin for event filtering.
    
    Filters events based on conditions.
    """
    
    @property
    def capabilities(self) -> List[EventPluginCapability]:
        """Filtering plugins have filtering capability."""
        return [EventPluginCapability.FILTERING]
        
    @abstractmethod
    async def should_process_event(
        self,
        event_data: Dict[str, Any],
        event_type: EventType,
        tenant_id: TenantId
    ) -> bool:
        """
        Determine if event should be processed.
        
        Args:
            event_data: Event data
            event_type: Type of event
            tenant_id: Tenant context
            
        Returns:
            True if event should be processed
        """
        pass
        
    async def get_filter_reason(
        self,
        event_data: Dict[str, Any],
        event_type: EventType,
        tenant_id: TenantId
    ) -> Optional[str]:
        """
        Get reason why event was filtered.
        
        Args:
            event_data: Event data
            event_type: Type of event
            tenant_id: Tenant context
            
        Returns:
            Filter reason or None
        """
        return None
        
    async def process_event(
        self,
        context: EventPluginContext
    ) -> EventPluginResult:
        """Process event using filtering logic."""
        try:
            should_process = await self.should_process_event(
                context.event_data,
                context.event_type,
                context.tenant_id
            )
            
            if not should_process:
                reason = await self.get_filter_reason(
                    context.event_data,
                    context.event_type,
                    context.tenant_id
                )
                
                return EventPluginResult(
                    success=True,
                    continue_processing=False,
                    error_message=f"Event filtered: {reason or 'No reason provided'}",
                    additional_metadata={"filtered_by": self.name}
                )
                
            return EventPluginResult(
                success=True,
                continue_processing=True,
                additional_metadata={"filter_passed": True, "filtered_by": self.name}
            )
            
        except Exception as e:
            return EventPluginResult(
                success=False,
                continue_processing=True,  # Continue processing despite plugin error
                error_message=f"Filtering plugin error: {str(e)}"
            )