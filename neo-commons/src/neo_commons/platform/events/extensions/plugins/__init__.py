"""
Plugin system exports.

ONLY handles plugin management and lifecycle.
"""

from .plugin_manager import PluginManager
from .event_plugin import EventPlugin

__all__ = [
    "PluginManager",
    "EventPlugin",
]