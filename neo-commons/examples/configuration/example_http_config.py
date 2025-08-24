"""Example configuration for HTTP status mapping.

This module demonstrates how to configure custom HTTP status mappings
using the ConfigurationProtocol. This is typically done during application
startup or through external configuration files.
"""

from typing import Any, Dict
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from neo_commons.core.shared.application import ConfigurationProtocol


class ExampleHttpStatusConfiguration:
    """Example configuration provider for HTTP status mapping."""
    
    def __init__(self):
        """Initialize with example configuration overrides."""
        self._config = {
            # Custom overrides - make auth errors more specific
            "http_status_mapping.UserNotFoundError": 404,  # Override default 401
            "http_status_mapping.InvalidCredentialsError": 422,  # Override default 401
            
            # Make rate limiting more specific
            "http_status_mapping.DatabaseRateLimitError": 503,  # Override default 429
            
            # Custom tenant error handling
            "http_status_mapping.TenantSuspendedError": 451,  # Custom: Unavailable For Legal Reasons
            
            # Development vs Production overrides
            "http_status_mapping.environment": "development",
            
            # Parent class overrides (affects all subclasses)
            "http_status_mapping.DatabaseError": 503,  # Make all DB errors service unavailable
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config[key] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section."""
        return {
            key[len(section) + 1:]: value 
            for key, value in self._config.items() 
            if key.startswith(f"{section}.")
        }


def setup_example_configuration() -> None:
    """Example of how to set up configurable HTTP status mapping.
    
    This would typically be called during application startup.
    """
    from neo_commons.core.exceptions.http_mapping import set_configuration_provider
    
    # Create configuration provider
    config = ExampleHttpStatusConfiguration()
    
    # Set the global configuration
    set_configuration_provider(config)
    
    print("✅ HTTP Status mapping configured with custom overrides")
    print("📋 Custom mappings:")
    print("   - UserNotFoundError: 404 (was 401)")
    print("   - InvalidCredentialsError: 422 (was 401)")  
    print("   - DatabaseRateLimitError: 503 (was 429)")
    print("   - TenantSuspendedError: 451 (custom)")
    print("   - DatabaseError: 503 (was 500)")


def demonstrate_configuration_usage() -> None:
    """Demonstrate how the configurable mapping works."""
    from neo_commons.core.exceptions.http_mapping import get_http_status_code, get_mapping_statistics
    from neo_commons.core.exceptions.domain import UserNotFoundError, InvalidCredentialsError, TenantSuspendedError
    from neo_commons.core.exceptions.database import DatabaseError, QueryError
    
    # Setup configuration
    setup_example_configuration()
    
    # Test configured mappings
    print("\n🧪 Testing configured mappings:")
    
    # These should use custom configured values
    print(f"UserNotFoundError: {get_http_status_code(UserNotFoundError('Test'))}")  # 404
    print(f"InvalidCredentialsError: {get_http_status_code(InvalidCredentialsError('Test'))}")  # 422
    print(f"TenantSuspendedError: {get_http_status_code(TenantSuspendedError('Test'))}")  # 451
    
    # DatabaseError parent class override should affect subclasses
    print(f"DatabaseError: {get_http_status_code(DatabaseError('Test'))}")  # 503
    print(f"QueryError (inherits DatabaseError): {get_http_status_code(QueryError('Test'))}")  # 503
    
    # Show mapping statistics
    stats = get_mapping_statistics()
    print(f"\n📊 Mapping statistics: {stats}")


if __name__ == "__main__":
    # Run demonstration
    demonstrate_configuration_usage()