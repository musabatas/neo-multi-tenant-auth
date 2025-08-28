"""
Pre-processing hook implementation.

ONLY handles pre-processing lifecycle hooks for events.
"""

import time
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .event_hook_registry import HookContext, HookResult, HookStage
from ....core.value_objects import EventId, TenantId, EventType


class PreProcessHook(ABC):
    """
    Abstract base class for pre-processing hooks.
    
    Executed before event processing begins.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Hook name for identification."""
        pass
        
    @property
    def supported_event_types(self) -> Optional[list[str]]:
        """
        List of supported event types.
        
        Returns:
            List of event type strings, or None for all types
        """
        return None
        
    @property
    def enabled(self) -> bool:
        """Whether this hook is enabled."""
        return True
        
    @abstractmethod
    async def before_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute pre-processing logic.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            event_data: Event payload
            metadata: Processing metadata
            
        Returns:
            Additional metadata to add to processing context
        """
        pass
        
    async def validate_event_data(
        self,
        event_data: Dict[str, Any],
        event_type: EventType
    ) -> Optional[str]:
        """
        Validate event data before processing.
        
        Args:
            event_data: Event payload to validate
            event_type: Type of event
            
        Returns:
            Error message if validation fails, None if valid
        """
        return None
        
    async def should_process_event(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Determine if event should be processed.
        
        Args:
            event_id: Event identifier
            tenant_id: Tenant context
            event_type: Type of event
            event_data: Event payload
            
        Returns:
            True if event should be processed
        """
        return True
        
    async def execute_hook(self, context: HookContext) -> HookResult:
        """
        Execute the pre-processing hook.
        
        This method is called by the hook registry.
        
        Args:
            context: Hook execution context
            
        Returns:
            Hook execution result
        """
        try:
            # Check if we should process this event
            should_process = await self.should_process_event(
                context.event_id,
                context.tenant_id,
                context.event_type,
                context.event_data
            )
            
            if not should_process:
                return HookResult(
                    success=True,
                    continue_processing=False,
                    error_message=f"Event filtered by {self.name}"
                )
                
            # Validate event data
            validation_error = await self.validate_event_data(
                context.event_data,
                context.event_type
            )
            
            if validation_error:
                return HookResult(
                    success=False,
                    continue_processing=False,
                    error_message=f"Validation failed: {validation_error}"
                )
                
            # Execute pre-processing
            additional_metadata = await self.before_processing(
                context.event_id,
                context.tenant_id,
                context.event_type,
                context.event_data,
                context.metadata
            )
            
            return HookResult(
                success=True,
                continue_processing=True,
                additional_metadata=additional_metadata
            )
            
        except Exception as e:
            return HookResult(
                success=False,
                continue_processing=True,  # Continue despite hook failure
                error_message=f"Pre-processing hook failed: {str(e)}"
            )


class EventValidationHook(PreProcessHook):
    """
    Pre-processing hook for event validation.
    
    Validates event structure and required fields.
    """
    
    @property
    def name(self) -> str:
        return "event_validation"
        
    @abstractmethod
    async def get_required_fields(self, event_type: EventType) -> list[str]:
        """
        Get required fields for event type.
        
        Args:
            event_type: Type of event
            
        Returns:
            List of required field names
        """
        pass
        
    @abstractmethod
    async def validate_field_value(
        self,
        field_name: str,
        field_value: Any,
        event_type: EventType
    ) -> Optional[str]:
        """
        Validate a specific field value.
        
        Args:
            field_name: Name of the field
            field_value: Value to validate
            event_type: Type of event
            
        Returns:
            Error message if invalid, None if valid
        """
        pass
        
    async def validate_event_data(
        self,
        event_data: Dict[str, Any],
        event_type: EventType
    ) -> Optional[str]:
        """Validate event data structure and fields."""
        required_fields = await self.get_required_fields(event_type)
        
        # Check required fields
        missing_fields = []
        for field in required_fields:
            if field not in event_data:
                missing_fields.append(field)
                
        if missing_fields:
            return f"Missing required fields: {', '.join(missing_fields)}"
            
        # Validate field values
        for field_name, field_value in event_data.items():
            error = await self.validate_field_value(field_name, field_value, event_type)
            if error:
                return f"Invalid field '{field_name}': {error}"
                
        return None
        
    async def before_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add validation metadata."""
        return {
            "validation_time": time.time(),
            "validated_by": self.name,
            "field_count": len(event_data),
        }


class EventEnrichmentHook(PreProcessHook):
    """
    Pre-processing hook for event enrichment.
    
    Adds additional context and data to events.
    """
    
    @property
    def name(self) -> str:
        return "event_enrichment"
        
    @abstractmethod
    async def enrich_event_data(
        self,
        event_data: Dict[str, Any],
        tenant_id: TenantId,
        event_type: EventType
    ) -> Dict[str, Any]:
        """
        Enrich event data with additional context.
        
        Args:
            event_data: Original event data
            tenant_id: Tenant context
            event_type: Type of event
            
        Returns:
            Additional data to add to event
        """
        pass
        
    async def before_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich event with additional data."""
        enrichment_data = await self.enrich_event_data(
            event_data,
            tenant_id,
            event_type
        )
        
        return {
            "enrichment_time": time.time(),
            "enriched_by": self.name,
            "enrichment_data": enrichment_data,
        }


class EventFilterHook(PreProcessHook):
    """
    Pre-processing hook for event filtering.
    
    Filters events based on conditions and rules.
    """
    
    @property
    def name(self) -> str:
        return "event_filter"
        
    @abstractmethod
    async def matches_filter_conditions(
        self,
        event_data: Dict[str, Any],
        tenant_id: TenantId,
        event_type: EventType
    ) -> bool:
        """
        Check if event matches filter conditions.
        
        Args:
            event_data: Event payload
            tenant_id: Tenant context
            event_type: Type of event
            
        Returns:
            True if event should be processed
        """
        pass
        
    async def should_process_event(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any]
    ) -> bool:
        """Filter events based on conditions."""
        return await self.matches_filter_conditions(
            event_data,
            tenant_id,
            event_type
        )
        
    async def before_processing(
        self,
        event_id: EventId,
        tenant_id: TenantId,
        event_type: EventType,
        event_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add filter metadata."""
        return {
            "filter_time": time.time(),
            "filtered_by": self.name,
            "filter_passed": True,
        }