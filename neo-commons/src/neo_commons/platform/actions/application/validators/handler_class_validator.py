"""Handler class validator."""

import importlib
import inspect
from typing import List, Optional, Type
from dataclasses import dataclass

from ...application.handlers.action_handler import ActionHandler


@dataclass
class HandlerValidationResult:
    """Result of handler class validation."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    handler_class: Optional[Type] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class HandlerClassValidator:
    """Validator for action handler class paths."""
    
    def validate_handler_class(self, handler_class_path: str, validate_import: bool = True) -> HandlerValidationResult:
        """
        Validate a handler class path.
        
        Args:
            handler_class_path: Full path to handler class (e.g., 'module.submodule.ClassName')
            validate_import: Whether to actually import and validate the class
            
        Returns:
            HandlerValidationResult with validation details
        """
        errors = []
        warnings = []
        handler_class = None
        
        # Basic validation
        if not handler_class_path:
            errors.append("Handler class path cannot be empty")
            return HandlerValidationResult(False, errors, warnings)
        
        if not isinstance(handler_class_path, str):
            errors.append("Handler class path must be a string")
            return HandlerValidationResult(False, errors, warnings)
        
        # Validate path format
        self._validate_path_format(handler_class_path, errors, warnings)
        
        if errors:
            return HandlerValidationResult(False, errors, warnings, handler_class)
        
        # Import and validate class if requested
        if validate_import:
            handler_class = self._validate_import_and_interface(handler_class_path, errors, warnings)
        
        return HandlerValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            handler_class=handler_class
        )
    
    def _validate_path_format(self, handler_class_path: str, errors: List[str], warnings: List[str]):
        """Validate the format of the handler class path."""
        # Length check
        if len(handler_class_path) > 500:
            errors.append("Handler class path too long (max 500 characters)")
            return
        
        # Basic format check
        if not handler_class_path.replace('_', '').replace('.', '').isalnum():
            errors.append("Handler class path contains invalid characters")
            return
        
        # Must contain at least one dot (module.class)
        if '.' not in handler_class_path:
            errors.append("Handler class path must include module path (e.g., 'module.ClassName')")
            return
        
        # Split into module and class parts
        try:
            module_path, class_name = handler_class_path.rsplit('.', 1)
        except ValueError:
            errors.append("Invalid handler class path format")
            return
        
        # Validate module path
        if not module_path:
            errors.append("Module path cannot be empty")
            return
        
        # Validate class name
        if not class_name:
            errors.append("Class name cannot be empty")
            return
        
        # Class name should start with uppercase (Python convention)
        if not class_name[0].isupper():
            warnings.append("Class name should start with uppercase letter (Python convention)")
        
        # Check for reserved words
        python_keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'exec', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'with', 'yield'
        ]
        
        module_parts = module_path.split('.')
        for part in module_parts + [class_name]:
            if part in python_keywords:
                errors.append(f"'{part}' is a Python keyword and cannot be used")
        
        # Validate each module part
        for part in module_parts:
            if not part.isidentifier():
                errors.append(f"Invalid module name: '{part}'")
        
        # Validate class name
        if not class_name.isidentifier():
            errors.append(f"Invalid class name: '{class_name}'")
        
        # Check for common patterns
        if 'handler' not in handler_class_path.lower():
            warnings.append("Handler class path should typically contain 'handler' for clarity")
    
    def _validate_import_and_interface(
        self, 
        handler_class_path: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> Optional[Type]:
        """Import and validate the handler class implements the correct interface."""
        try:
            # Split path
            module_path, class_name = handler_class_path.rsplit('.', 1)
            
            # Import module
            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                errors.append(f"Cannot import module '{module_path}': {str(e)}")
                return None
            
            # Get class
            try:
                handler_class = getattr(module, class_name)
            except AttributeError:
                errors.append(f"Class '{class_name}' not found in module '{module_path}'")
                return None
            
            # Validate it's actually a class
            if not inspect.isclass(handler_class):
                errors.append(f"'{class_name}' is not a class")
                return None
            
            # Check if it inherits from ActionHandler
            if not issubclass(handler_class, ActionHandler):
                errors.append(f"Class '{class_name}' must inherit from ActionHandler")
                return None
            
            # Check if it's abstract
            if getattr(handler_class, '__abstractmethods__', None):
                errors.append(f"Class '{class_name}' is abstract and cannot be instantiated")
                return None
            
            # Try to instantiate (basic check)
            try:
                instance = handler_class()
                
                # Check required methods exist and are callable
                required_methods = ['execute', 'validate_config', 'handler_name', 'handler_version']
                for method_name in required_methods:
                    if not hasattr(instance, method_name):
                        errors.append(f"Handler missing required method: {method_name}")
                    elif method_name not in ['handler_name', 'handler_version'] and not callable(getattr(instance, method_name)):
                        errors.append(f"Handler method '{method_name}' is not callable")
                
                # Check properties
                try:
                    handler_name = instance.handler_name
                    if not isinstance(handler_name, str) or not handler_name.strip():
                        warnings.append("handler_name should return a non-empty string")
                except Exception as e:
                    warnings.append(f"Error getting handler_name: {str(e)}")
                
                try:
                    handler_version = instance.handler_version
                    if not isinstance(handler_version, str) or not handler_version.strip():
                        warnings.append("handler_version should return a non-empty string")
                except Exception as e:
                    warnings.append(f"Error getting handler_version: {str(e)}")
                
            except Exception as e:
                errors.append(f"Cannot instantiate handler class: {str(e)}")
                return None
            
            return handler_class
            
        except Exception as e:
            errors.append(f"Unexpected error validating handler: {str(e)}")
            return None
    
    def get_handler_info(self, handler_class_path: str) -> Optional[dict]:
        """
        Get information about a handler class.
        
        Args:
            handler_class_path: Full path to handler class
            
        Returns:
            Dictionary with handler information or None if invalid
        """
        result = self.validate_handler_class(handler_class_path, validate_import=True)
        
        if not result.is_valid or not result.handler_class:
            return None
        
        try:
            instance = result.handler_class()
            
            return {
                'class_path': handler_class_path,
                'class_name': result.handler_class.__name__,
                'module': result.handler_class.__module__,
                'handler_name': instance.handler_name,
                'handler_version': instance.handler_version,
                'supported_action_types': getattr(instance, 'supported_action_types', []),
                'doc_string': result.handler_class.__doc__ or '',
                'methods': [method for method in dir(instance) if not method.startswith('_')],
            }
            
        except Exception as e:
            return {
                'class_path': handler_class_path,
                'error': str(e)
            }