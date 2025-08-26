"""Validation rules for events feature following neo-commons patterns.

This module provides centralized validation logic for webhook endpoints, 
event types, and domain events.
"""

import re
from typing import Any, Dict, List
from urllib.parse import urlparse
from ..services.webhook_config_service import get_webhook_config


class WebhookValidationRules:
    """Centralized validation rules for webhook-related entities."""
    
    # URL validation pattern
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    # Event type pattern (category.action)
    EVENT_TYPE_PATTERN = re.compile(r'^[a-z_]+\.[a-z_]+$')
    
    @classmethod
    def _get_validation_config(cls):
        """Get validation configuration with caching."""
        return get_webhook_config().validation
    
    @classmethod
    def validate_webhook_url(cls, url: str) -> None:
        """Validate webhook endpoint URL.
        
        Args:
            url: URL to validate
            
        Raises:
            ValueError: If URL is invalid
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Get validation configuration
        config = cls._get_validation_config()
        
        # Check URL length
        if len(url) > config.max_url_length:
            raise ValueError(f"URL length cannot exceed {config.max_url_length} characters")
        
        if not cls.URL_PATTERN.match(url):
            raise ValueError("Invalid URL format")
        
        # Parse URL to check components
        parsed = urlparse(url)
        
        # Check allowed protocols
        allowed_protocols = config.allowed_protocols.split(',')
        if parsed.scheme not in allowed_protocols:
            raise ValueError(f"URL must use one of: {', '.join(allowed_protocols).upper()}")
        
        if not parsed.netloc:
            raise ValueError("URL must have a valid domain")
        
        # Check for localhost/internal IPs based on configuration
        if config.block_loopback and parsed.hostname in ['127.0.0.1', '0.0.0.0', 'localhost']:
            raise ValueError("Loopback addresses not allowed")
            
        # Check for private networks if configured
        if config.block_private_networks:
            private_ranges = [
                '10.', '172.16.', '172.17.', '172.18.', '172.19.',
                '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
                '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                '172.30.', '172.31.', '192.168.'
            ]
            if parsed.hostname and any(parsed.hostname.startswith(prefix) for prefix in private_ranges):
                raise ValueError("Private network addresses not allowed")
    
    @classmethod
    def validate_endpoint_name(cls, name: str) -> None:
        """Validate webhook endpoint name.
        
        Args:
            name: Name to validate
            
        Raises:
            ValueError: If name is invalid
        """
        if not name:
            raise ValueError("Endpoint name cannot be empty")
        
        config = cls._get_validation_config()
        
        if len(name) > config.max_endpoint_name_length:
            raise ValueError(f"Endpoint name cannot exceed {config.max_endpoint_name_length} characters")
        
        if not name.strip():
            raise ValueError("Endpoint name cannot be only whitespace")
    
    @classmethod
    def validate_event_type(cls, event_type: str) -> None:
        """Validate event type format using configurable thresholds.
        
        Args:
            event_type: Event type to validate (e.g., 'organization.created')
            
        Raises:
            ValueError: If event type is invalid
        """
        if not event_type:
            raise ValueError("Event type cannot be empty")
        
        config = cls._get_validation_config()
        
        # Check total length
        if len(event_type) > config.max_event_type_length:
            raise ValueError(f"Event type cannot exceed {config.max_event_type_length} characters")
        
        if not cls.EVENT_TYPE_PATTERN.match(event_type):
            raise ValueError("Event type must follow 'category.action' format with lowercase letters and underscores only")
        
        parts = event_type.split('.')
        if len(parts) != 2:
            raise ValueError("Event type must have exactly one dot separating category and action")
        
        category, action = parts
        if len(category) == 0 or len(action) == 0:
            raise ValueError("Both category and action parts must be non-empty")
        
        # Check individual part lengths
        if len(category) > config.max_event_category_length:
            raise ValueError(f"Event category cannot exceed {config.max_event_category_length} characters")
        
        if len(action) > config.max_event_action_length:
            raise ValueError(f"Event action cannot exceed {config.max_event_action_length} characters")
    
    @classmethod
    def validate_secret_token(cls, token: str) -> None:
        """Validate webhook secret token.
        
        Args:
            token: Secret token to validate
            
        Raises:
            ValueError: If token is invalid
        """
        if not token:
            raise ValueError("Secret token cannot be empty")
        
        config = cls._get_validation_config()
        
        if len(token) < config.min_secret_token_length:
            raise ValueError(f"Secret token must be at least {config.min_secret_token_length} characters long")
        
        if len(token) > config.max_secret_token_length:
            raise ValueError(f"Secret token cannot exceed {config.max_secret_token_length} characters")
    
    @classmethod
    def validate_custom_headers(cls, headers: Dict[str, str]) -> None:
        """Validate custom headers using configurable thresholds.
        
        Args:
            headers: Dictionary of custom headers
            
        Raises:
            ValueError: If headers are invalid
        """
        if not isinstance(headers, dict):
            raise ValueError("Custom headers must be a dictionary")
        
        config = cls._get_validation_config()
        
        # Check number of headers limit
        if len(headers) > config.max_custom_headers:
            raise ValueError(f"Cannot have more than {config.max_custom_headers} custom headers")
        
        for name, value in headers.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise ValueError("Header names and values must be strings")
            
            if not name.strip():
                raise ValueError("Header names cannot be empty or whitespace only")
            
            # Check header name length
            if len(name) > config.max_header_name_length:
                raise ValueError(f"Header name '{name}' exceeds maximum length of {config.max_header_name_length}")
            
            # Check header value length
            if len(value) > config.max_header_value_length:
                raise ValueError(f"Header value for '{name}' exceeds maximum length of {config.max_header_value_length}")
            
            # Check for forbidden headers
            forbidden_headers = [
                'host', 'content-length', 'authorization', 
                'x-webhook-signature', 'user-agent'
            ]
            if name.lower() in forbidden_headers:
                raise ValueError(f"Header '{name}' is not allowed as custom header")
    
    @classmethod
    def validate_retry_config(cls, max_attempts: int, backoff_seconds: int, multiplier: float) -> None:
        """Validate retry configuration using configurable thresholds.
        
        Args:
            max_attempts: Maximum retry attempts
            backoff_seconds: Base backoff seconds
            multiplier: Backoff multiplier
            
        Raises:
            ValueError: If retry config is invalid
        """
        config = cls._get_validation_config()
        
        if not (config.min_retry_attempts <= max_attempts <= config.max_retry_attempts_limit):
            raise ValueError(
                f"max_retry_attempts must be between {config.min_retry_attempts} and {config.max_retry_attempts_limit}"
            )
        
        if not (config.min_backoff_seconds <= backoff_seconds <= config.max_backoff_seconds):
            raise ValueError(
                f"retry_backoff_seconds must be between {config.min_backoff_seconds} and {config.max_backoff_seconds}"
            )
        
        if not (config.min_backoff_multiplier <= multiplier <= config.max_backoff_multiplier):
            raise ValueError(
                f"retry_backoff_multiplier must be between {config.min_backoff_multiplier} and {config.max_backoff_multiplier}"
            )
    
    @classmethod
    def validate_timeout_seconds(cls, timeout: int) -> None:
        """Validate timeout configuration using configurable thresholds.
        
        Args:
            timeout: Timeout in seconds
            
        Raises:
            ValueError: If timeout is invalid
        """
        config = cls._get_validation_config()
        
        if not (config.min_timeout_seconds <= timeout <= config.max_timeout_seconds):
            raise ValueError(
                f"timeout_seconds must be between {config.min_timeout_seconds} and {config.max_timeout_seconds}"
            )
    
    @classmethod
    def validate_payload_size(cls, payload_data: Dict[str, Any]) -> None:
        """Validate payload size using configurable thresholds.
        
        Args:
            payload_data: Payload data to validate size
            
        Raises:
            ValueError: If payload size exceeds limits
        """
        config = cls._get_validation_config()
        
        # Calculate approximate payload size
        import sys
        payload_size_bytes = sys.getsizeof(str(payload_data))
        max_size_bytes = config.max_payload_size_mb * 1024 * 1024
        
        if payload_size_bytes > max_size_bytes:
            raise ValueError(
                f"Payload size ({payload_size_bytes} bytes) exceeds limit ({config.max_payload_size_mb}MB)"
            )
    
    @classmethod
    def validate_response_constraints(cls, response_size_bytes: int, response_time_ms: int) -> None:
        """Validate response size and timing constraints.
        
        Args:
            response_size_bytes: Response size in bytes
            response_time_ms: Response time in milliseconds
            
        Raises:
            ValueError: If response exceeds configured limits
        """
        config = cls._get_validation_config()
        
        max_response_size_bytes = config.max_response_size_mb * 1024 * 1024
        if response_size_bytes > max_response_size_bytes:
            raise ValueError(
                f"Response size ({response_size_bytes} bytes) exceeds limit ({config.max_response_size_mb}MB)"
            )
        
        if response_time_ms > config.max_response_time_ms:
            raise ValueError(
                f"Response time ({response_time_ms}ms) exceeds limit ({config.max_response_time_ms}ms)"
            )
    
    @classmethod
    def validate_environment_specific_constraints(cls, endpoint_url: str, environment_profile: str = None) -> None:
        """Validate environment-specific constraints and policies.
        
        Args:
            endpoint_url: URL to validate against environment policies
            environment_profile: Override environment profile
            
        Raises:
            ValueError: If endpoint violates environment-specific policies
        """
        config = cls._get_validation_config()
        profile = environment_profile or config.get_environment_profile()
        
        # Get environment-specific adjustments
        env_limits = config.get_adjusted_limits_for_environment()
        
        # Apply environment-specific URL validation
        from urllib.parse import urlparse
        parsed = urlparse(endpoint_url)
        
        # Development environment allows test endpoints
        if profile == 'development':
            if not config.allow_test_endpoints and any(test_domain in parsed.netloc 
                for test_domain in ['webhook.site', 'httpbin.org', 'postb.in']):
                raise ValueError("Test endpoints are not allowed in this environment")
        
        # Production environment requires HTTPS and SSL validation
        elif profile == 'production':
            if parsed.scheme != 'https':
                raise ValueError("Production environment requires HTTPS endpoints")
            
            if config.validate_ssl_certificates and not config.strict_validation_mode:
                raise ValueError("Production environment requires strict SSL certificate validation")
        
        # Apply adjusted network restrictions
        if env_limits.get('block_loopback', config.block_loopback):
            if parsed.hostname in ['127.0.0.1', '0.0.0.0', 'localhost']:
                raise ValueError(f"Loopback addresses not allowed in {profile} environment")
        
        if env_limits.get('block_private_networks', config.block_private_networks):
            private_ranges = [
                '10.', '172.16.', '172.17.', '172.18.', '172.19.',
                '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
                '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                '172.30.', '172.31.', '192.168.'
            ]
            if parsed.hostname and any(parsed.hostname.startswith(prefix) for prefix in private_ranges):
                raise ValueError(f"Private network addresses not allowed in {profile} environment")


class ValidationOrchestrator:
    """Centralized validation orchestrator with environment-aware validation.
    
    Coordinates all webhook-related validations using configurable thresholds
    and environment-specific policies for comprehensive validation management.
    """
    
    def __init__(self, environment_profile: str = None):
        """Initialize validation orchestrator.
        
        Args:
            environment_profile: Optional environment override ('development', 'staging', 'production')
        """
        self._environment_profile = environment_profile
        self._config = WebhookValidationRules._get_validation_config()
    
    def validate_webhook_endpoint_complete(
        self, 
        endpoint_url: str, 
        endpoint_name: str,
        custom_headers: Dict[str, str] = None,
        secret_token: str = None,
        timeout_seconds: int = None,
        max_retry_attempts: int = None,
        retry_backoff_seconds: int = None,
        retry_multiplier: float = None
    ) -> List[str]:
        """Perform complete webhook endpoint validation.
        
        Args:
            endpoint_url: Webhook endpoint URL
            endpoint_name: Endpoint name
            custom_headers: Custom headers dictionary
            secret_token: Optional secret token for HMAC signing
            timeout_seconds: Request timeout
            max_retry_attempts: Maximum retry attempts
            retry_backoff_seconds: Base retry backoff
            retry_multiplier: Retry backoff multiplier
            
        Returns:
            List of validation warnings (empty if all validations pass)
            
        Raises:
            ValueError: If any validation fails
        """
        warnings = []
        
        try:
            # Core validations
            WebhookValidationRules.validate_webhook_url(endpoint_url)
            WebhookValidationRules.validate_endpoint_name(endpoint_name)
            
            # Environment-specific validations
            WebhookValidationRules.validate_environment_specific_constraints(
                endpoint_url, self._environment_profile
            )
            
            # Optional component validations
            if custom_headers:
                WebhookValidationRules.validate_custom_headers(custom_headers)
            
            if secret_token:
                WebhookValidationRules.validate_secret_token(secret_token)
            
            if timeout_seconds is not None:
                WebhookValidationRules.validate_timeout_seconds(timeout_seconds)
            
            if all(param is not None for param in [max_retry_attempts, retry_backoff_seconds, retry_multiplier]):
                WebhookValidationRules.validate_retry_config(
                    max_retry_attempts, retry_backoff_seconds, retry_multiplier
                )
            
            # Configuration consistency check
            config_warnings = self._config.validate_configuration()
            warnings.extend(config_warnings)
            
            return warnings
            
        except ValueError as e:
            # Re-raise validation errors with additional context
            profile = self._environment_profile or self._config.get_environment_profile()
            raise ValueError(f"Webhook endpoint validation failed in {profile} environment: {e}")
    
    def validate_domain_event_complete(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_version: int,
        event_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> List[str]:
        """Perform complete domain event validation.
        
        Args:
            event_type: Event type (e.g., 'organization.created')
            aggregate_type: Aggregate type name
            aggregate_version: Aggregate version number
            event_data: Event payload data
            metadata: Optional event metadata
            
        Returns:
            List of validation warnings (empty if all validations pass)
            
        Raises:
            ValueError: If any validation fails
        """
        warnings = []
        
        try:
            # Core event validations
            WebhookValidationRules.validate_event_type(event_type)
            DomainEventValidationRules.validate_aggregate_type(aggregate_type)
            DomainEventValidationRules.validate_aggregate_version(aggregate_version)
            DomainEventValidationRules.validate_event_data(event_data)
            
            # Payload size validation
            WebhookValidationRules.validate_payload_size(event_data)
            
            # Metadata validation if present
            if metadata:
                import sys
                metadata_size_bytes = sys.getsizeof(str(metadata))
                max_metadata_bytes = self._config.max_metadata_size_kb * 1024
                
                if metadata_size_bytes > max_metadata_bytes:
                    warnings.append(
                        f"Metadata size ({metadata_size_bytes} bytes) exceeds recommended limit "
                        f"({self._config.max_metadata_size_kb}KB)"
                    )
            
            return warnings
            
        except ValueError as e:
            profile = self._environment_profile or self._config.get_environment_profile()
            raise ValueError(f"Domain event validation failed in {profile} environment: {e}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get comprehensive validation configuration summary.
        
        Returns:
            Dictionary containing validation limits and environment settings
        """
        profile = self._environment_profile or self._config.get_environment_profile()
        env_limits = self._config.get_adjusted_limits_for_environment()
        
        return {
            "environment_profile": profile,
            "validation_thresholds": {
                "urls": {
                    "max_length": self._config.max_url_length,
                    "allowed_protocols": self._config.allowed_protocols.split(','),
                    "block_loopback": env_limits.get('block_loopback', self._config.block_loopback),
                    "block_private_networks": env_limits.get('block_private_networks', self._config.block_private_networks)
                },
                "endpoints": {
                    "max_name_length": self._config.max_endpoint_name_length,
                    "max_description_length": self._config.max_description_length
                },
                "headers": {
                    "max_custom_headers": self._config.max_custom_headers,
                    "max_name_length": self._config.max_header_name_length,
                    "max_value_length": self._config.max_header_value_length
                },
                "timeouts": {
                    "min_seconds": self._config.min_timeout_seconds,
                    "max_seconds": env_limits.get('max_timeout_seconds', self._config.max_timeout_seconds)
                },
                "retries": {
                    "max_attempts": env_limits.get('max_retry_attempts_limit', self._config.max_retry_attempts_limit),
                    "backoff_range": f"{self._config.min_backoff_seconds}-{self._config.max_backoff_seconds}s",
                    "multiplier_range": f"{self._config.min_backoff_multiplier}-{self._config.max_backoff_multiplier}"
                },
                "payloads": {
                    "max_payload_size_mb": self._config.max_payload_size_mb,
                    "max_event_data_depth": self._config.max_event_data_depth,
                    "max_metadata_size_kb": self._config.max_metadata_size_kb
                }
            },
            "environment_settings": {
                "strict_validation": env_limits.get('strict_validation_mode', self._config.strict_validation_mode),
                "allow_test_endpoints": self._config.allow_test_endpoints,
                "validate_ssl_certificates": self._config.validate_ssl_certificates
            },
            "performance_limits": {
                "max_concurrent_validations": self._config.max_concurrent_validations,
                "validation_timeout_seconds": self._config.validation_timeout_seconds,
                "max_response_size_mb": self._config.max_response_size_mb,
                "max_response_time_ms": self._config.max_response_time_ms
            }
        }


class DomainEventValidationRules:
    """Validation rules for domain events."""
    
    @classmethod
    def validate_aggregate_type(cls, aggregate_type: str) -> None:
        """Validate aggregate type using configurable thresholds.
        
        Args:
            aggregate_type: Aggregate type to validate
            
        Raises:
            ValueError: If aggregate type is invalid
        """
        if not aggregate_type:
            raise ValueError("Aggregate type cannot be empty")
        
        # Get validation configuration
        config = WebhookValidationRules._get_validation_config()
        
        if len(aggregate_type) > config.max_aggregate_type_length:
            raise ValueError(f"Aggregate type cannot exceed {config.max_aggregate_type_length} characters")
        
        # Must be lowercase with optional underscores
        if not re.match(r'^[a-z][a-z0-9_]*$', aggregate_type):
            raise ValueError("Aggregate type must start with lowercase letter and contain only lowercase letters, numbers, and underscores")
    
    @classmethod
    def validate_event_data(cls, event_data: Dict[str, Any]) -> None:
        """Validate event data payload using configurable thresholds.
        
        Args:
            event_data: Event data to validate
            
        Raises:
            ValueError: If event data is invalid
        """
        if not isinstance(event_data, dict):
            raise ValueError("Event data must be a dictionary")
        
        # Get validation configuration
        config = WebhookValidationRules._get_validation_config()
        
        # Check for nested depth (prevent deeply nested objects)
        def check_depth(obj: Any, current_depth: int = 0) -> None:
            if current_depth > config.max_event_data_depth:
                raise ValueError(f"Event data nesting cannot exceed {config.max_event_data_depth} levels")
            
            if isinstance(obj, dict):
                for value in obj.values():
                    check_depth(value, current_depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, current_depth + 1)
        
        check_depth(event_data)
        
        # Check payload size if configured
        import sys
        payload_size_bytes = sys.getsizeof(str(event_data))
        max_size_bytes = config.max_event_data_size_kb * 1024
        
        if payload_size_bytes > max_size_bytes:
            raise ValueError(f"Event data size ({payload_size_bytes} bytes) exceeds limit ({max_size_bytes} bytes)")
    
    @classmethod
    def validate_aggregate_version(cls, version: int) -> None:
        """Validate aggregate version using configurable thresholds.
        
        Args:
            version: Version number to validate
            
        Raises:
            ValueError: If version is invalid
        """
        # Get validation configuration
        config = WebhookValidationRules._get_validation_config()
        
        if not (config.min_aggregate_version <= version <= config.max_aggregate_version):
            raise ValueError(
                f"Aggregate version must be between {config.min_aggregate_version} and {config.max_aggregate_version}"
            )