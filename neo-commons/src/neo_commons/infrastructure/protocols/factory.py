"""Protocol factory for runtime protocol adaptation.

This module provides a factory pattern for creating protocol implementations
dynamically at runtime based on configuration, environment, or other conditions.
Enables flexible dependency injection with fallback mechanisms.
"""

import logging
from typing import (
    Any, Dict, List, Optional, Protocol, Type, TypeVar, Union, 
    Callable, runtime_checkable
)
from dataclasses import dataclass
from enum import Enum
import importlib
from functools import lru_cache
from threading import Lock

from ...core.shared.application import ConfigurationProtocol

logger = logging.getLogger(__name__)

# Type variables for protocol factory
P = TypeVar('P')  # Protocol type
T = TypeVar('T')


class AdaptationStrategy(Enum):
    """Strategy for protocol adaptation."""
    FIRST_AVAILABLE = "first_available"  # Use first available implementation
    PRIORITY_ORDER = "priority_order"    # Use highest priority available
    LOAD_BALANCED = "load_balanced"      # Distribute across implementations
    FAILOVER = "failover"                # Primary with fallback chain


@dataclass
class ProtocolImplementation:
    """Registry entry for a protocol implementation."""
    name: str
    implementation_class: Type[Any]
    priority: int = 0
    condition: Optional[Callable[[], bool]] = None
    dependencies: Optional[Dict[str, Any]] = None
    singleton: bool = True
    description: Optional[str] = None


@runtime_checkable
class ProtocolFactory(Protocol):
    """Protocol for creating protocol implementations."""
    
    def create(self, protocol_type: Type[P], **kwargs) -> P:
        """Create implementation of the given protocol."""
        ...
    
    def register(self, 
                protocol_type: Type[P], 
                implementation: ProtocolImplementation) -> None:
        """Register an implementation for a protocol."""
        ...


class RuntimeProtocolFactory:
    """Factory for creating and managing protocol implementations at runtime.
    
    Features:
    - Dynamic protocol implementation selection
    - Configuration-driven adaptation
    - Fallback mechanisms
    - Singleton pattern support
    - Conditional implementation registration
    - Load balancing and failover strategies
    """
    
    def __init__(self, 
                 config: Optional[ConfigurationProtocol] = None,
                 strategy: AdaptationStrategy = AdaptationStrategy.PRIORITY_ORDER):
        self.config = config
        self.strategy = strategy
        self._registry: Dict[Type[Any], List[ProtocolImplementation]] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = Lock()
    
    def register(self, 
                protocol_type: Type[P], 
                implementation: ProtocolImplementation) -> None:
        """Register an implementation for a protocol type.
        
        Args:
            protocol_type: The protocol interface
            implementation: Implementation details
        """
        with self._lock:
            if protocol_type not in self._registry:
                self._registry[protocol_type] = []
            
            self._registry[protocol_type].append(implementation)
            
            # Sort by priority (highest first)
            self._registry[protocol_type].sort(key=lambda x: x.priority, reverse=True)
            
            logger.debug(
                f"Registered {implementation.name} for {protocol_type.__name__} "
                f"with priority {implementation.priority}"
            )
    
    def register_multiple(self,
                         protocol_type: Type[P],
                         implementations: List[ProtocolImplementation]) -> None:
        """Register multiple implementations for a protocol."""
        for impl in implementations:
            self.register(protocol_type, impl)
    
    def create(self, protocol_type: Type[P], **kwargs) -> P:
        """Create an implementation of the given protocol.
        
        Args:
            protocol_type: The protocol interface to implement
            **kwargs: Additional arguments for implementation constructor
        
        Returns:
            Instance implementing the protocol
        
        Raises:
            ValueError: If no suitable implementation found
        """
        implementations = self._registry.get(protocol_type, [])
        
        if not implementations:
            raise ValueError(f"No implementations registered for {protocol_type.__name__}")
        
        # Apply adaptation strategy
        if self.strategy == AdaptationStrategy.FIRST_AVAILABLE:
            return self._create_first_available(protocol_type, implementations, **kwargs)
        elif self.strategy == AdaptationStrategy.PRIORITY_ORDER:
            return self._create_priority_order(protocol_type, implementations, **kwargs)
        elif self.strategy == AdaptationStrategy.LOAD_BALANCED:
            return self._create_load_balanced(protocol_type, implementations, **kwargs)
        elif self.strategy == AdaptationStrategy.FAILOVER:
            return self._create_with_failover(protocol_type, implementations, **kwargs)
        else:
            raise ValueError(f"Unsupported adaptation strategy: {self.strategy}")
    
    def create_named(self, 
                    protocol_type: Type[P], 
                    implementation_name: str, 
                    **kwargs) -> P:
        """Create a specific named implementation.
        
        Args:
            protocol_type: The protocol interface
            implementation_name: Specific implementation to create
            **kwargs: Constructor arguments
        
        Returns:
            Named implementation instance
        """
        implementations = self._registry.get(protocol_type, [])
        
        for impl in implementations:
            if impl.name == implementation_name:
                if self._check_condition(impl):
                    return self._create_instance(impl, **kwargs)
        
        raise ValueError(
            f"Implementation '{implementation_name}' not found for {protocol_type.__name__}"
        )
    
    def get_available_implementations(self, protocol_type: Type[P]) -> List[str]:
        """Get list of available implementation names for a protocol."""
        implementations = self._registry.get(protocol_type, [])
        return [impl.name for impl in implementations if self._check_condition(impl)]
    
    def is_implementation_available(self, 
                                  protocol_type: Type[P], 
                                  implementation_name: str) -> bool:
        """Check if a specific implementation is available."""
        implementations = self._registry.get(protocol_type, [])
        
        for impl in implementations:
            if impl.name == implementation_name:
                return self._check_condition(impl)
        
        return False
    
    def _create_first_available(self, 
                               protocol_type: Type[P], 
                               implementations: List[ProtocolImplementation],
                               **kwargs) -> P:
        """Create first available implementation."""
        for impl in implementations:
            if self._check_condition(impl):
                try:
                    return self._create_instance(impl, **kwargs)
                except Exception as e:
                    logger.warning(f"Failed to create {impl.name}: {e}")
                    continue
        
        raise ValueError(f"No available implementations for {protocol_type.__name__}")
    
    def _create_priority_order(self, 
                              protocol_type: Type[P], 
                              implementations: List[ProtocolImplementation],
                              **kwargs) -> P:
        """Create highest priority available implementation."""
        # Implementations are already sorted by priority
        return self._create_first_available(protocol_type, implementations, **kwargs)
    
    def _create_load_balanced(self, 
                             protocol_type: Type[P], 
                             implementations: List[ProtocolImplementation],
                             **kwargs) -> P:
        """Create implementation using load balancing (round-robin)."""
        available = [impl for impl in implementations if self._check_condition(impl)]
        
        if not available:
            raise ValueError(f"No available implementations for {protocol_type.__name__}")
        
        # Simple round-robin based on protocol type hash
        index = abs(hash(protocol_type.__name__)) % len(available)
        impl = available[index]
        
        return self._create_instance(impl, **kwargs)
    
    def _create_with_failover(self, 
                             protocol_type: Type[P], 
                             implementations: List[ProtocolImplementation],
                             **kwargs) -> P:
        """Create implementation with failover chain."""
        last_exception = None
        
        for impl in implementations:
            if self._check_condition(impl):
                try:
                    instance = self._create_instance(impl, **kwargs)
                    logger.info(f"Created {impl.name} for {protocol_type.__name__}")
                    return instance
                except Exception as e:
                    logger.warning(f"Failover: {impl.name} failed: {e}")
                    last_exception = e
                    continue
        
        error_msg = f"All implementations failed for {protocol_type.__name__}"
        if last_exception:
            error_msg += f". Last error: {last_exception}"
        
        raise ValueError(error_msg)
    
    def _check_condition(self, impl: ProtocolImplementation) -> bool:
        """Check if implementation condition is satisfied."""
        if impl.condition is None:
            return True
        
        try:
            return impl.condition()
        except Exception as e:
            logger.warning(f"Condition check failed for {impl.name}: {e}")
            return False
    
    def _create_instance(self, impl: ProtocolImplementation, **kwargs) -> Any:
        """Create instance of implementation with singleton support."""
        if impl.singleton:
            cache_key = f"{impl.implementation_class.__name__}:{hash(str(sorted(kwargs.items())))}"
            
            if cache_key in self._instances:
                return self._instances[cache_key]
        
        # Merge dependencies with kwargs
        constructor_kwargs = {}
        if impl.dependencies:
            constructor_kwargs.update(impl.dependencies)
        constructor_kwargs.update(kwargs)
        
        # Create instance
        try:
            instance = impl.implementation_class(**constructor_kwargs)
            
            if impl.singleton:
                self._instances[cache_key] = instance
            
            return instance
        
        except Exception as e:
            raise ValueError(f"Failed to create {impl.name}: {e}")
    
    def clear_cache(self) -> None:
        """Clear singleton instance cache."""
        with self._lock:
            self._instances.clear()
    
    def get_registry_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get information about registered implementations."""
        info = {}
        
        for protocol_type, implementations in self._registry.items():
            info[protocol_type.__name__] = [
                {
                    "name": impl.name,
                    "class": impl.implementation_class.__name__,
                    "priority": impl.priority,
                    "available": self._check_condition(impl),
                    "singleton": impl.singleton,
                    "description": impl.description
                }
                for impl in implementations
            ]
        
        return info


class ProtocolRegistrar:
    """Helper class for registering protocol implementations."""
    
    def __init__(self, factory: RuntimeProtocolFactory):
        self.factory = factory
    
    def register_from_config(self, 
                            config_key: str, 
                            protocol_type: Type[P]) -> None:
        """Register implementations from configuration.
        
        Expected config format:
        {
            "implementations": [
                {
                    "name": "redis_cache",
                    "class": "neo_commons.features.cache.adapters.redis_adapter.RedisAdapter",
                    "priority": 10,
                    "dependencies": {"host": "localhost", "port": 6379},
                    "condition": "redis_available"
                }
            ]
        }
        """
        if not self.factory.config:
            logger.warning("No config provided to factory")
            return
        
        config_data = self.factory.config.get(config_key, {})
        implementations = config_data.get("implementations", [])
        
        for impl_config in implementations:
            try:
                # Load implementation class
                class_path = impl_config["class"]
                module_path, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                impl_class = getattr(module, class_name)
                
                # Create condition function if specified
                condition = None
                if "condition" in impl_config:
                    condition = self._create_condition_function(impl_config["condition"])
                
                # Create implementation entry
                impl = ProtocolImplementation(
                    name=impl_config["name"],
                    implementation_class=impl_class,
                    priority=impl_config.get("priority", 0),
                    condition=condition,
                    dependencies=impl_config.get("dependencies"),
                    singleton=impl_config.get("singleton", True),
                    description=impl_config.get("description")
                )
                
                self.factory.register(protocol_type, impl)
                
            except Exception as e:
                logger.error(f"Failed to register {impl_config.get('name', 'unknown')}: {e}")
    
    def _create_condition_function(self, condition_spec: Union[str, Dict[str, Any]]) -> Callable[[], bool]:
        """Create condition function from specification."""
        if isinstance(condition_spec, str):
            # Simple environment variable check
            return lambda: self.factory.config.get(condition_spec, False) if self.factory.config else False
        
        elif isinstance(condition_spec, dict):
            condition_type = condition_spec.get("type")
            
            if condition_type == "config_value":
                key = condition_spec["key"]
                expected = condition_spec.get("value", True)
                return lambda: self.factory.config.get(key) == expected if self.factory.config else False
            
            elif condition_type == "import_available":
                module_name = condition_spec["module"]
                return lambda: self._is_module_available(module_name)
        
        return lambda: True
    
    def _is_module_available(self, module_name: str) -> bool:
        """Check if a module is available for import."""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False


# Global factory instance
_global_factory: Optional[RuntimeProtocolFactory] = None
_factory_lock = Lock()


def get_protocol_factory(config: Optional[ConfigurationProtocol] = None) -> RuntimeProtocolFactory:
    """Get global protocol factory instance."""
    global _global_factory
    
    with _factory_lock:
        if _global_factory is None:
            _global_factory = RuntimeProtocolFactory(config=config)
        
        return _global_factory


def set_protocol_factory(factory: RuntimeProtocolFactory) -> None:
    """Set custom protocol factory (primarily for testing)."""
    global _global_factory
    
    with _factory_lock:
        _global_factory = factory


@lru_cache(maxsize=128)
def create_protocol(protocol_type: Type[P], **kwargs) -> P:
    """Convenience function to create protocol implementation."""
    factory = get_protocol_factory()
    return factory.create(protocol_type, **kwargs)


def register_implementation(protocol_type: Type[P], 
                           name: str,
                           implementation_class: Type[Any],
                           priority: int = 0,
                           condition: Optional[Callable[[], bool]] = None,
                           dependencies: Optional[Dict[str, Any]] = None,
                           singleton: bool = True,
                           description: Optional[str] = None) -> None:
    """Convenience function to register protocol implementation."""
    factory = get_protocol_factory()
    
    impl = ProtocolImplementation(
        name=name,
        implementation_class=implementation_class,
        priority=priority,
        condition=condition,
        dependencies=dependencies,
        singleton=singleton,
        description=description
    )
    
    factory.register(protocol_type, impl)


# Decorator for automatic protocol registration
def protocol_implementation(protocol_type: Type[P], 
                           name: str,
                           priority: int = 0,
                           condition: Optional[Callable[[], bool]] = None,
                           dependencies: Optional[Dict[str, Any]] = None,
                           singleton: bool = True,
                           description: Optional[str] = None):
    """Decorator for automatic protocol implementation registration."""
    def decorator(cls: Type[T]) -> Type[T]:
        register_implementation(
            protocol_type=protocol_type,
            name=name,
            implementation_class=cls,
            priority=priority,
            condition=condition,
            dependencies=dependencies,
            singleton=singleton,
            description=description
        )
        return cls
    
    return decorator