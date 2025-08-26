"""
Platform Events Module Registration

Registers the events platform infrastructure with neo-commons, providing
event dispatching, action execution, and webhook delivery services to
all business features.
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class PlatformModule:
    """Platform module descriptor for the events infrastructure."""
    
    name: str = "events"
    version: str = "1.0.0"
    description: str = "Event dispatching and webhook delivery platform"
    
    # Platform capabilities
    capabilities: List[str] = None
    
    # Service dependencies  
    dependencies: List[str] = None
    
    def __post_init__(self):
        """Initialize default capabilities and dependencies."""
        if self.capabilities is None:
            self.capabilities = [
                "event_dispatching",
                "action_execution", 
                "webhook_delivery",
                "event_storage",
                "action_registry",
                "delivery_monitoring",
                "archival_management"
            ]
        
        if self.dependencies is None:
            self.dependencies = [
                "database",  # For event and action storage
                "cache",     # For performance optimization
                "http",      # For webhook delivery
                "queue",     # For async processing
            ]


class EventsPlatformRegistry:
    """Registry for events platform services and components."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._handlers: Dict[str, Any] = {}
        self._adapters: Dict[str, Any] = {}
        self._validators: Dict[str, Any] = {}
    
    def register_service(self, name: str, service: Any) -> None:
        """Register a platform service."""
        self._services[name] = service
    
    def register_handler(self, handler_type: str, handler: Any) -> None:
        """Register an action handler."""
        self._handlers[handler_type] = handler
    
    def register_adapter(self, adapter_type: str, adapter: Any) -> None:
        """Register an external service adapter."""
        self._adapters[adapter_type] = adapter
    
    def register_validator(self, validator_type: str, validator: Any) -> None:
        """Register a platform validator."""
        self._validators[validator_type] = validator
    
    def get_service(self, name: str) -> Any:
        """Get a registered platform service."""
        return self._services.get(name)
    
    def get_handler(self, handler_type: str) -> Any:
        """Get a registered action handler."""
        return self._handlers.get(handler_type)
    
    def get_adapter(self, adapter_type: str) -> Any:
        """Get a registered external adapter."""
        return self._adapters.get(adapter_type)
    
    def get_validator(self, validator_type: str) -> Any:
        """Get a registered validator."""
        return self._validators.get(validator_type)
    
    def list_services(self) -> List[str]:
        """List all registered services."""
        return list(self._services.keys())
    
    def list_handlers(self) -> List[str]:
        """List all registered handlers."""
        return list(self._handlers.keys())
    
    def list_adapters(self) -> List[str]:
        """List all registered adapters."""
        return list(self._adapters.keys())
    
    def list_validators(self) -> List[str]:
        """List all registered validators."""
        return list(self._validators.keys())


# Global registry instance
events_registry = EventsPlatformRegistry()

# Module descriptor
events_module = PlatformModule()


def register_events_platform() -> PlatformModule:
    """
    Register the events platform module with neo-commons.
    
    Returns:
        PlatformModule: The events platform module descriptor
    """
    return events_module


def get_events_registry() -> EventsPlatformRegistry:
    """
    Get the events platform registry.
    
    Returns:
        EventsPlatformRegistry: The global events registry
    """
    return events_registry