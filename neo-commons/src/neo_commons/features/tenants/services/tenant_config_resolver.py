"""Tenant configuration resolver using existing configuration infrastructure.

Integrates with existing neo-commons configuration system to provide
tenant-specific configuration resolution without duplication.
"""

import logging
from typing import Any, Dict, Optional

from ....core.value_objects import TenantId
from ....infrastructure.configuration.entities.protocols import ConfigurationProvider
from ....infrastructure.configuration.entities.config import ConfigKey, ConfigScope
from ..entities.protocols import TenantConfigResolver


logger = logging.getLogger(__name__)


class TenantConfigurationResolver:
    """Tenant configuration resolver using existing configuration infrastructure.
    
    Provides tenant-specific configuration resolution by integrating with
    the existing configuration provider without duplicating logic.
    """
    
    def __init__(self, config_provider: ConfigurationProvider, tenant_table: str = "tenant_configs"):
        """Initialize with existing configuration provider.
        
        Args:
            config_provider: Existing configuration provider from infrastructure
            tenant_table: Name of tenant config table (can be in any schema)
        """
        self._config_provider = config_provider
        self._tenant_table = tenant_table
    
    async def get_config(self, tenant_id: TenantId, key: str, default: Any = None) -> Any:
        """Get tenant-specific configuration value."""
        try:
            # Try tenant-specific config first
            tenant_key = ConfigKey(f"tenant:{tenant_id.value}:{key}", ConfigScope.TENANT)
            tenant_config = await self._config_provider.get_config(tenant_key)
            
            if tenant_config:
                return tenant_config.get_typed_value()
            
            # Fall back to global config
            global_key = ConfigKey(key, ConfigScope.GLOBAL)
            global_config = await self._config_provider.get_config(global_key)
            
            if global_config:
                return global_config.get_typed_value()
            
            return default
            
        except Exception as e:
            logger.error(f"Failed to get config {key} for tenant {tenant_id}: {e}")
            return default
    
    async def get_configs(self, tenant_id: TenantId, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get all tenant configurations, optionally filtered by namespace."""
        try:
            # Get tenant-specific configs
            tenant_configs = await self._config_provider.get_configs_by_scope(ConfigScope.TENANT)
            
            # Filter for this tenant and namespace
            result = {}
            tenant_prefix = f"tenant:{tenant_id.value}:"
            
            for config in tenant_configs:
                if config.key.value.startswith(tenant_prefix):
                    # Extract the actual config key (remove tenant prefix)
                    actual_key = config.key.value[len(tenant_prefix):]
                    
                    # Apply namespace filter if specified
                    if namespace and not actual_key.startswith(f"{namespace}."):
                        continue
                    
                    result[actual_key] = config.get_typed_value()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get configs for tenant {tenant_id}: {e}")
            return {}
    
    async def set_config(self, tenant_id: TenantId, key: str, value: Any) -> bool:
        """Set tenant-specific configuration."""
        try:
            from ....infrastructure.configuration.entities.config import ConfigValue, ConfigType, ConfigSource
            
            # Determine config type
            config_type = ConfigType.STRING
            if isinstance(value, bool):
                config_type = ConfigType.BOOLEAN
            elif isinstance(value, int):
                config_type = ConfigType.INTEGER
            elif isinstance(value, float):
                config_type = ConfigType.FLOAT
            elif isinstance(value, (dict, list)):
                config_type = ConfigType.JSON
            
            # Create tenant-specific config
            tenant_key = ConfigKey(f"tenant:{tenant_id.value}:{key}", ConfigScope.TENANT)
            config_value = ConfigValue(
                key=tenant_key,
                value=value,
                config_type=config_type,
                source=ConfigSource.DATABASE
            )
            
            # Save using existing config provider
            return await self._config_provider.set_config(config_value)
            
        except Exception as e:
            logger.error(f"Failed to set config {key} for tenant {tenant_id}: {e}")
            return False
    
    async def delete_config(self, tenant_id: TenantId, key: str) -> bool:
        """Delete tenant-specific configuration."""
        try:
            tenant_key = ConfigKey(f"tenant:{tenant_id.value}:{key}", ConfigScope.TENANT)
            return await self._config_provider.delete_config(tenant_key)
            
        except Exception as e:
            logger.error(f"Failed to delete config {key} for tenant {tenant_id}: {e}")
            return False