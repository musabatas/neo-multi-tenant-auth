"""
Plugin manager for loading and managing plugins.

ONLY handles plugin lifecycle, registration, and coordination.
"""

import asyncio
import importlib
import logging
from typing import Dict, List, Optional, Any, Type, Callable, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .event_plugin import EventPlugin
from .action_plugin import ActionPlugin
from ....core.value_objects import TenantId


class PluginStatus(Enum):
    """Plugin status states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """Plugin information and metadata."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    module_path: str
    class_name: str
    config_schema: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "config_schema": self.config_schema,
            "dependencies": self.dependencies or [],
        }


@dataclass
class LoadedPlugin:
    """Loaded plugin instance and metadata."""
    info: PluginInfo
    instance: Any  # EventPlugin or ActionPlugin
    status: PluginStatus
    config: Dict[str, Any]
    load_time: float
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "info": self.info.to_dict(),
            "status": self.status.value,
            "config": self.config,
            "load_time": self.load_time,
            "error_message": self.error_message,
        }


class PluginManager:
    """
    Manager for loading, configuring, and coordinating plugins.
    
    Handles plugin discovery, loading, dependency resolution, and lifecycle.
    """
    
    def __init__(self, plugin_directories: Optional[List[str]] = None):
        self._plugin_directories = plugin_directories or []
        self._plugins: Dict[str, LoadedPlugin] = {}
        self._plugin_registry: Dict[str, PluginInfo] = {}
        self._loading_plugins: Set[str] = set()
        self._logger = logging.getLogger(__name__)
        
    async def discover_plugins(self, plugin_directory: Optional[str] = None) -> List[PluginInfo]:
        """
        Discover plugins in specified directory or registered directories.
        
        Args:
            plugin_directory: Specific directory to search, or None for all
            
        Returns:
            List of discovered plugin information
        """
        discovered_plugins = []
        directories_to_search = [plugin_directory] if plugin_directory else self._plugin_directories
        
        for directory in directories_to_search:
            directory_path = Path(directory)
            if not directory_path.exists():
                self._logger.warning(f"Plugin directory does not exist: {directory}")
                continue
                
            # Look for plugin manifest files
            for manifest_file in directory_path.glob("**/plugin.json"):
                try:
                    plugin_info = await self._load_plugin_manifest(manifest_file)
                    discovered_plugins.append(plugin_info)
                    self._plugin_registry[plugin_info.name] = plugin_info
                    self._logger.info(f"Discovered plugin: {plugin_info.name}")
                    
                except Exception as e:
                    self._logger.error(f"Failed to load plugin manifest {manifest_file}: {e}")
                    
        return discovered_plugins
        
    async def load_plugin(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[TenantId] = None
    ) -> bool:
        """
        Load and initialize a plugin.
        
        Args:
            plugin_name: Name of plugin to load
            config: Plugin configuration
            tenant_id: Optional tenant context for tenant-specific plugins
            
        Returns:
            True if plugin was loaded successfully
        """
        if plugin_name in self._loading_plugins:
            self._logger.warning(f"Plugin {plugin_name} is already being loaded")
            return False
            
        if plugin_name in self._plugins:
            self._logger.warning(f"Plugin {plugin_name} is already loaded")
            return True
            
        if plugin_name not in self._plugin_registry:
            self._logger.error(f"Plugin {plugin_name} not found in registry")
            return False
            
        self._loading_plugins.add(plugin_name)
        
        try:
            plugin_info = self._plugin_registry[plugin_name]
            
            # Load dependencies first
            if plugin_info.dependencies:
                for dependency in plugin_info.dependencies:
                    if dependency not in self._plugins:
                        self._logger.info(f"Loading dependency {dependency} for {plugin_name}")
                        if not await self.load_plugin(dependency):
                            self._logger.error(f"Failed to load dependency {dependency}")
                            return False
                            
            # Load the plugin class
            plugin_class = await self._import_plugin_class(plugin_info)
            if not plugin_class:
                return False
                
            # Create plugin instance
            plugin_instance = plugin_class()
            plugin_config = config or {}
            
            # Validate configuration
            if hasattr(plugin_instance, 'validate_configuration'):
                if not await plugin_instance.validate_configuration(plugin_config):
                    self._logger.error(f"Plugin {plugin_name} configuration validation failed")
                    return False
                    
            # Initialize plugin
            loaded_plugin = LoadedPlugin(
                info=plugin_info,
                instance=plugin_instance,
                status=PluginStatus.INITIALIZING,
                config=plugin_config,
                load_time=asyncio.get_event_loop().time()
            )
            
            self._plugins[plugin_name] = loaded_plugin
            
            # Initialize the plugin
            if hasattr(plugin_instance, 'initialize'):
                await plugin_instance.initialize(plugin_config, tenant_id)
                
            loaded_plugin.status = PluginStatus.ACTIVE
            self._logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to load plugin {plugin_name}: {e}", exc_info=True)
            
            # Update plugin status if it was created
            if plugin_name in self._plugins:
                self._plugins[plugin_name].status = PluginStatus.ERROR
                self._plugins[plugin_name].error_message = str(e)
                
            return False
            
        finally:
            self._loading_plugins.discard(plugin_name)
            
    async def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin and clean up resources.
        
        Args:
            plugin_name: Name of plugin to unload
            
        Returns:
            True if plugin was unloaded successfully
        """
        if plugin_name not in self._plugins:
            self._logger.warning(f"Plugin {plugin_name} is not loaded")
            return True
            
        try:
            loaded_plugin = self._plugins[plugin_name]
            
            # Check if other plugins depend on this one
            dependents = await self._find_dependent_plugins(plugin_name)
            if dependents:
                self._logger.error(f"Cannot unload {plugin_name}, required by: {dependents}")
                return False
                
            # Cleanup plugin
            if hasattr(loaded_plugin.instance, 'cleanup'):
                await loaded_plugin.instance.cleanup()
                
            # Remove from loaded plugins
            del self._plugins[plugin_name]
            self._logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to unload plugin {plugin_name}: {e}", exc_info=True)
            return False
            
    async def reload_plugin(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Reload a plugin with new configuration.
        
        Args:
            plugin_name: Name of plugin to reload
            config: New plugin configuration
            
        Returns:
            True if plugin was reloaded successfully
        """
        # Unload first
        if not await self.unload_plugin(plugin_name):
            return False
            
        # Load with new configuration
        return await self.load_plugin(plugin_name, config)
        
    async def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a disabled plugin.
        
        Args:
            plugin_name: Name of plugin to enable
            
        Returns:
            True if plugin was enabled successfully
        """
        if plugin_name not in self._plugins:
            return await self.load_plugin(plugin_name)
            
        loaded_plugin = self._plugins[plugin_name]
        if loaded_plugin.status == PluginStatus.DISABLED:
            loaded_plugin.status = PluginStatus.ACTIVE
            self._logger.info(f"Enabled plugin: {plugin_name}")
            
        return True
        
    async def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin without unloading it.
        
        Args:
            plugin_name: Name of plugin to disable
            
        Returns:
            True if plugin was disabled successfully
        """
        if plugin_name not in self._plugins:
            self._logger.warning(f"Plugin {plugin_name} is not loaded")
            return True
            
        loaded_plugin = self._plugins[plugin_name]
        loaded_plugin.status = PluginStatus.DISABLED
        self._logger.info(f"Disabled plugin: {plugin_name}")
        return True
        
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """
        Get loaded plugin instance.
        
        Args:
            plugin_name: Name of plugin
            
        Returns:
            Plugin instance or None if not loaded
        """
        if plugin_name in self._plugins:
            loaded_plugin = self._plugins[plugin_name]
            if loaded_plugin.status == PluginStatus.ACTIVE:
                return loaded_plugin.instance
                
        return None
        
    def get_plugins_by_type(self, plugin_type: str) -> List[Any]:
        """
        Get all loaded plugins of specified type.
        
        Args:
            plugin_type: Type of plugins to retrieve
            
        Returns:
            List of plugin instances
        """
        plugins = []
        for loaded_plugin in self._plugins.values():
            if (loaded_plugin.status == PluginStatus.ACTIVE and
                loaded_plugin.info.plugin_type == plugin_type):
                plugins.append(loaded_plugin.instance)
                
        return plugins
        
    def list_plugins(self, status_filter: Optional[PluginStatus] = None) -> List[Dict[str, Any]]:
        """
        List loaded plugins with their status.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            List of plugin information
        """
        plugins = []
        for loaded_plugin in self._plugins.values():
            if not status_filter or loaded_plugin.status == status_filter:
                plugins.append(loaded_plugin.to_dict())
                
        return plugins
        
    def get_plugin_stats(self) -> Dict[str, Any]:
        """
        Get plugin manager statistics.
        
        Returns:
            Plugin statistics
        """
        status_counts = {}
        for loaded_plugin in self._plugins.values():
            status = loaded_plugin.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
        return {
            "total_plugins": len(self._plugins),
            "registered_plugins": len(self._plugin_registry),
            "status_counts": status_counts,
            "plugin_directories": self._plugin_directories,
        }
        
    async def _load_plugin_manifest(self, manifest_path: Path) -> PluginInfo:
        """Load plugin information from manifest file."""
        import json
        
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
            
        return PluginInfo(
            name=manifest_data["name"],
            version=manifest_data["version"],
            description=manifest_data["description"],
            author=manifest_data["author"],
            plugin_type=manifest_data["plugin_type"],
            module_path=manifest_data["module_path"],
            class_name=manifest_data["class_name"],
            config_schema=manifest_data.get("config_schema"),
            dependencies=manifest_data.get("dependencies")
        )
        
    async def _import_plugin_class(self, plugin_info: PluginInfo) -> Optional[Type]:
        """Import plugin class from module."""
        try:
            module = importlib.import_module(plugin_info.module_path)
            plugin_class = getattr(module, plugin_info.class_name)
            return plugin_class
            
        except Exception as e:
            self._logger.error(f"Failed to import plugin class {plugin_info.class_name}: {e}")
            return None
            
    async def _find_dependent_plugins(self, plugin_name: str) -> List[str]:
        """Find plugins that depend on the specified plugin."""
        dependents = []
        for name, loaded_plugin in self._plugins.items():
            if (loaded_plugin.info.dependencies and
                plugin_name in loaded_plugin.info.dependencies):
                dependents.append(name)
                
        return dependents