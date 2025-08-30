"""Action handler registry for dynamic loading and validation."""

import importlib
import inspect
import traceback
from typing import Dict, Type, Optional, List
from dataclasses import dataclass
from datetime import datetime

from ...application.handlers.action_handler import ActionHandler


@dataclass
class HandlerValidationResult:
    """Result of handler validation."""
    
    is_valid: bool
    handler_class: Optional[Type[ActionHandler]]
    error_message: Optional[str] = None
    validation_details: Optional[Dict] = None


class HandlerRegistry:
    """Registry for dynamic loading and validation of action handlers."""
    
    def __init__(self):
        self._handler_cache: Dict[str, Type[ActionHandler]] = {}
        self._validation_cache: Dict[str, HandlerValidationResult] = {}
    
    async def get_handler(self, handler_class_path: str) -> ActionHandler:
        """
        Load and instantiate a handler by class path.
        
        Args:
            handler_class_path: Full path to handler class (e.g., 'module.ClassName')
            
        Returns:
            Instance of the handler
            
        Raises:
            ImportError: If module or class cannot be imported
            ValueError: If class is not a valid ActionHandler
        """
        # Check cache first
        if handler_class_path in self._handler_cache:
            handler_class = self._handler_cache[handler_class_path]
            return handler_class()
        
        # Load handler class
        handler_class = await self._load_handler_class(handler_class_path)
        
        # Cache for future use
        self._handler_cache[handler_class_path] = handler_class
        
        # Instantiate and return
        return handler_class()
    
    async def validate_handler(self, handler_class_path: str) -> HandlerValidationResult:
        """
        Validate that a handler class exists and implements the correct interface.
        
        Args:
            handler_class_path: Full path to handler class
            
        Returns:
            HandlerValidationResult with validation details
        """
        # Check cache first
        if handler_class_path in self._validation_cache:
            return self._validation_cache[handler_class_path]
        
        try:
            handler_class = await self._load_handler_class(handler_class_path)
            
            # Perform detailed validation
            validation_details = await self._perform_detailed_validation(handler_class)
            
            result = HandlerValidationResult(
                is_valid=True,
                handler_class=handler_class,
                validation_details=validation_details
            )
            
        except Exception as e:
            result = HandlerValidationResult(
                is_valid=False,
                handler_class=None,
                error_message=str(e),
                validation_details={"error_type": type(e).__name__, "traceback": traceback.format_exc()}
            )
        
        # Cache result
        self._validation_cache[handler_class_path] = result
        return result
    
    async def _load_handler_class(self, handler_class_path: str) -> Type[ActionHandler]:
        """Load a handler class by its path."""
        if '.' not in handler_class_path:
            raise ValueError(f"Handler class path must include module: {handler_class_path}")
        
        try:
            # Split module and class name
            module_path, class_name = handler_class_path.rsplit('.', 1)
            
            # Import module
            module = importlib.import_module(module_path)
            
            # Get class from module
            if not hasattr(module, class_name):
                raise ImportError(f"Class '{class_name}' not found in module '{module_path}'")
            
            handler_class = getattr(module, class_name)
            
            # Validate it's actually a class
            if not inspect.isclass(handler_class):
                raise ValueError(f"'{class_name}' is not a class")
            
            # Validate it inherits from ActionHandler
            if not issubclass(handler_class, ActionHandler):
                raise ValueError(f"Class '{class_name}' must inherit from ActionHandler")
            
            # Check if it's abstract
            if getattr(handler_class, '__abstractmethods__', None):
                raise ValueError(f"Class '{class_name}' is abstract and cannot be instantiated")
            
            return handler_class
            
        except ImportError as e:
            raise ImportError(f"Cannot import handler '{handler_class_path}': {str(e)}")
        except Exception as e:
            raise ValueError(f"Invalid handler class '{handler_class_path}': {str(e)}")
    
    async def _perform_detailed_validation(self, handler_class: Type[ActionHandler]) -> Dict:
        """Perform detailed validation of a handler class."""
        validation_details = {
            "class_name": handler_class.__name__,
            "module": handler_class.__module__,
            "mro": [cls.__name__ for cls in handler_class.__mro__],
            "methods": [],
            "properties": [],
            "instantiation_test": False,
            "interface_compliance": False
        }
        
        # Check methods
        required_methods = ['execute', 'validate_config']
        required_properties = ['handler_name', 'handler_version']
        
        for method_name in required_methods:
            if hasattr(handler_class, method_name):
                method = getattr(handler_class, method_name)
                validation_details["methods"].append({
                    "name": method_name,
                    "exists": True,
                    "callable": callable(method),
                    "signature": str(inspect.signature(method)) if callable(method) else None
                })
            else:
                validation_details["methods"].append({
                    "name": method_name,
                    "exists": False,
                    "callable": False
                })
        
        # Check properties
        for prop_name in required_properties:
            validation_details["properties"].append({
                "name": prop_name,
                "exists": hasattr(handler_class, prop_name)
            })
        
        # Test instantiation
        try:
            instance = handler_class()
            validation_details["instantiation_test"] = True
            
            # Test interface compliance
            try:
                # Test handler name and version properties
                handler_name = instance.handler_name
                handler_version = instance.handler_version
                
                validation_details["interface_compliance"] = (
                    isinstance(handler_name, str) and 
                    isinstance(handler_version, str) and
                    handler_name.strip() != "" and 
                    handler_version.strip() != ""
                )
                
                validation_details["handler_info"] = {
                    "name": handler_name,
                    "version": handler_version,
                    "supported_types": getattr(instance, 'supported_action_types', [])
                }
                
            except Exception as e:
                validation_details["interface_compliance"] = False
                validation_details["interface_error"] = str(e)
                
        except Exception as e:
            validation_details["instantiation_test"] = False
            validation_details["instantiation_error"] = str(e)
        
        return validation_details
    
    def get_cached_handlers(self) -> List[str]:
        """Get list of cached handler class paths."""
        return list(self._handler_cache.keys())
    
    def clear_cache(self, handler_class_path: Optional[str] = None):
        """Clear handler cache."""
        if handler_class_path:
            self._handler_cache.pop(handler_class_path, None)
            self._validation_cache.pop(handler_class_path, None)
        else:
            self._handler_cache.clear()
            self._validation_cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cached_handlers": len(self._handler_cache),
            "cached_validations": len(self._validation_cache),
            "handler_paths": list(self._handler_cache.keys())
        }


# Singleton instance
_handler_registry: Optional[HandlerRegistry] = None


def get_handler_registry() -> HandlerRegistry:
    """Get the global handler registry instance."""
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = HandlerRegistry()
    return _handler_registry