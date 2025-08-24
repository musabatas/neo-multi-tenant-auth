# Neo-Commons Configuration Examples

This directory contains example configurations and usage patterns for neo-commons features.

## HTTP Status Mapping Configuration

### Files:
- `example_http_config.py` - Example configuration provider implementation
- `CONFIGURABLE_HTTP_MAPPING.md` - Detailed documentation on HTTP status mapping

### Usage:
```python
from neo_commons.examples.configuration.example_http_config import setup_example_configuration

# Setup custom HTTP status mappings
setup_example_configuration()
```

### Integration:
These examples demonstrate how to:
1. Create custom configuration providers
2. Override default HTTP status codes
3. Set up environment-specific mappings
4. Use the ConfigurationProtocol for runtime configuration

## Features Demonstrated:
- ✅ Runtime configuration override
- ✅ Environment-specific settings
- ✅ Custom error status codes
- ✅ Configuration provider patterns
- ✅ Statistics and monitoring