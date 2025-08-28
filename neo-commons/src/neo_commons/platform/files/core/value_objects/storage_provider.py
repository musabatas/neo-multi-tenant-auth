"""Storage provider value object.

ONLY storage provider - represents validated storage provider type with
configuration support and capabilities.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, Set

# No ValueObject base class needed - using plain dataclass


class StorageProviderType(Enum):
    """Supported storage provider types."""
    LOCAL = "local"
    S3 = "s3"


@dataclass(frozen=True)
class StorageProvider:
    """Storage provider value object.
    
    Represents a validated storage provider with type checking and
    configuration support. Used to ensure only supported providers
    are used throughout the system.
    
    Features:
    - Validates against supported provider types
    - Provides capability information
    - Configuration validation support
    - Provider-specific feature detection
    """
    
    value: str
    
    # Supported provider types
    SUPPORTED_PROVIDERS = {provider.value for provider in StorageProviderType}
    
    # Provider capabilities
    PROVIDER_CAPABILITIES = {
        StorageProviderType.LOCAL.value: {
            "chunked_upload": True,
            "resumable_upload": True,
            "multipart_upload": False,
            "versioning": False,
            "encryption_at_rest": False,
            "cdn_integration": False,
            "access_control": True,
            "virus_scanning": True,
            "thumbnail_generation": True,
            "metadata_storage": True
        },
        StorageProviderType.S3.value: {
            "chunked_upload": True,
            "resumable_upload": True,
            "multipart_upload": True,
            "versioning": True,
            "encryption_at_rest": True,
            "cdn_integration": True,
            "access_control": True,
            "virus_scanning": True,
            "thumbnail_generation": True,
            "metadata_storage": True
        }
    }
    
    # Required configuration keys per provider
    REQUIRED_CONFIG_KEYS = {
        StorageProviderType.LOCAL.value: {
            "base_path", "max_file_size", "allowed_extensions"
        },
        StorageProviderType.S3.value: {
            "bucket_name", "region", "access_key_id", "secret_access_key"
        }
    }
    
    # Optional configuration keys per provider
    OPTIONAL_CONFIG_KEYS = {
        StorageProviderType.LOCAL.value: {
            "permissions", "create_directories", "temp_directory"
        },
        StorageProviderType.S3.value: {
            "endpoint_url", "use_ssl", "signature_version", "storage_class",
            "server_side_encryption", "kms_key_id", "multipart_threshold"
        }
    }
    
    def __post_init__(self):
        """Validate storage provider type."""
        if not isinstance(self.value, str):
            raise ValueError(f"StorageProvider must be a string, got {type(self.value).__name__}")
        
        # Normalize to lowercase
        normalized = self.value.strip().lower()
        if not normalized:
            raise ValueError("Storage provider cannot be empty")
        
        # Validate against supported providers
        if normalized not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported storage provider: {self.value}. "
                f"Supported providers: {', '.join(sorted(self.SUPPORTED_PROVIDERS))}"
            )
        
        # Store normalized value
        object.__setattr__(self, 'value', normalized)
    
    @classmethod
    def local(cls) -> 'StorageProvider':
        """Create local filesystem storage provider."""
        return cls(StorageProviderType.LOCAL.value)
    
    @classmethod
    def s3(cls) -> 'StorageProvider':
        """Create Amazon S3 storage provider."""
        return cls(StorageProviderType.S3.value)
    
    def get_type(self) -> StorageProviderType:
        """Get the storage provider type enum."""
        return StorageProviderType(self.value)
    
    def is_local(self) -> bool:
        """Check if this is a local filesystem provider."""
        return self.value == StorageProviderType.LOCAL.value
    
    def is_s3(self) -> bool:
        """Check if this is an S3 provider."""
        return self.value == StorageProviderType.S3.value
    
    def is_cloud_provider(self) -> bool:
        """Check if this is a cloud-based provider."""
        return not self.is_local()
    
    def supports_capability(self, capability: str) -> bool:
        """Check if provider supports a specific capability."""
        capabilities = self.PROVIDER_CAPABILITIES.get(self.value, {})
        return capabilities.get(capability, False)
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get all capabilities for this provider."""
        return self.PROVIDER_CAPABILITIES.get(self.value, {}).copy()
    
    def get_required_config_keys(self) -> Set[str]:
        """Get required configuration keys for this provider."""
        return self.REQUIRED_CONFIG_KEYS.get(self.value, set()).copy()
    
    def get_optional_config_keys(self) -> Set[str]:
        """Get optional configuration keys for this provider."""
        return self.OPTIONAL_CONFIG_KEYS.get(self.value, set()).copy()
    
    def get_all_config_keys(self) -> Set[str]:
        """Get all configuration keys (required + optional) for this provider."""
        required = self.get_required_config_keys()
        optional = self.get_optional_config_keys()
        return required.union(optional)
    
    def validate_configuration(self, config: Dict[str, Any]) -> None:
        """Validate configuration for this provider."""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        required_keys = self.get_required_config_keys()
        config_keys = set(config.keys())
        
        # Check for missing required keys
        missing_keys = required_keys - config_keys
        if missing_keys:
            raise ValueError(
                f"Missing required configuration keys for {self.value}: "
                f"{', '.join(sorted(missing_keys))}"
            )
        
        # Check for unknown keys
        all_valid_keys = self.get_all_config_keys()
        unknown_keys = config_keys - all_valid_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown configuration keys for {self.value}: "
                f"{', '.join(sorted(unknown_keys))}"
            )
        
        # Provider-specific validation
        if self.is_s3():
            self._validate_s3_config(config)
        elif self.is_local():
            self._validate_local_config(config)
    
    def _validate_s3_config(self, config: Dict[str, Any]) -> None:
        """Validate S3-specific configuration."""
        bucket_name = config.get("bucket_name")
        if bucket_name and not isinstance(bucket_name, str):
            raise ValueError("S3 bucket_name must be a string")
        
        region = config.get("region")
        if region and not isinstance(region, str):
            raise ValueError("S3 region must be a string")
        
        # Validate boolean flags
        bool_keys = ["use_ssl"]
        for key in bool_keys:
            if key in config and not isinstance(config[key], bool):
                raise ValueError(f"S3 {key} must be a boolean")
    
    def _validate_local_config(self, config: Dict[str, Any]) -> None:
        """Validate local filesystem configuration."""
        base_path = config.get("base_path")
        if base_path and not isinstance(base_path, str):
            raise ValueError("Local base_path must be a string")
        
        max_file_size = config.get("max_file_size")
        if max_file_size is not None and not isinstance(max_file_size, int):
            raise ValueError("Local max_file_size must be an integer")
        
        # Validate boolean flags
        bool_keys = ["create_directories"]
        for key in bool_keys:
            if key in config and not isinstance(config[key], bool):
                raise ValueError(f"Local {key} must be a boolean")
    
    def __str__(self) -> str:
        """String representation for display."""
        return self.value.upper()
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"StorageProvider('{self.value}')"