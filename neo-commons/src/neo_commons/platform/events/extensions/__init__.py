"""
Platform extension points exports.

Extension points for customizing and extending events platform functionality.
"""

# Extension Interfaces
from .interfaces import *

# Hook System
from .hooks import *

# Plugin System
from .plugins import *

# Middleware Extensions
from .middleware_extensions import *

__all__ = [
    # Extension Interfaces
    "EventExtension",
    "ActionExtension", 
    "WebhookExtension",
    "NotificationExtension",
    
    # Hook System
    "EventHookRegistry",
    "PreProcessHook",
    "PostProcessHook",
    "ErrorHook",
    
    # Plugin System
    "PluginManager",
    "EventPlugin",
    "ActionPlugin",
    
    # Middleware Extensions
    "MiddlewareExtension",
    "CustomMiddleware",
]