"""Action configuration validator."""

import re
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ActionConfigValidator:
    """Validator for action configuration."""
    
    def validate_config(self, action_type: str, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate action configuration based on action type.
        
        Args:
            action_type: Type of action being configured
            config: Configuration dictionary to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        if not isinstance(config, dict):
            errors.append("Config must be a dictionary")
            return ValidationResult(False, errors, warnings)
        
        # Validate based on action type
        if action_type == "email":
            self._validate_email_config(config, errors, warnings)
        elif action_type == "sms":
            self._validate_sms_config(config, errors, warnings)
        elif action_type == "webhook":
            self._validate_webhook_config(config, errors, warnings)
        elif action_type == "database_operation":
            self._validate_database_config(config, errors, warnings)
        elif action_type == "function_execution":
            self._validate_function_config(config, errors, warnings)
        else:
            # Generic validation for unknown types
            self._validate_generic_config(config, errors, warnings)
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    def _validate_email_config(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate email action configuration."""
        required_fields = ["smtp_host", "smtp_port", "from_email"]
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate email format
        if "from_email" in config:
            if not self._is_valid_email(config["from_email"]):
                errors.append("Invalid from_email format")
        
        # Validate port
        if "smtp_port" in config:
            try:
                port = int(config["smtp_port"])
                if port <= 0 or port > 65535:
                    errors.append("smtp_port must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.append("smtp_port must be a valid integer")
        
        # Check for security settings
        if config.get("use_tls") is False and config.get("use_ssl") is False:
            warnings.append("Consider using TLS or SSL for secure email transmission")
    
    def _validate_sms_config(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate SMS action configuration."""
        if "provider" not in config:
            errors.append("Missing required field: provider")
        
        provider = config.get("provider", "").lower()
        
        if provider == "twilio":
            required_fields = ["account_sid", "auth_token", "from_number"]
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required Twilio field: {field}")
        elif provider == "aws_sns":
            required_fields = ["aws_access_key_id", "aws_secret_access_key", "region"]
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required AWS SNS field: {field}")
        else:
            warnings.append(f"Unknown SMS provider: {provider}")
    
    def _validate_webhook_config(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate webhook action configuration."""
        if "webhook_url" not in config:
            errors.append("Missing required field: webhook_url")
        
        # Validate URL format
        if "webhook_url" in config:
            url = config["webhook_url"]
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                errors.append("webhook_url must be a valid HTTP/HTTPS URL")
            elif url.startswith("http://"):
                warnings.append("Consider using HTTPS for secure webhook delivery")
        
        # Validate method
        if "method" in config:
            method = config["method"].upper()
            if method not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                errors.append("Invalid HTTP method")
        
        # Validate timeout
        if "timeout_seconds" in config:
            try:
                timeout = int(config["timeout_seconds"])
                if timeout <= 0:
                    errors.append("timeout_seconds must be positive")
                elif timeout > 300:
                    warnings.append("timeout_seconds > 300 may cause action timeouts")
            except (ValueError, TypeError):
                errors.append("timeout_seconds must be a valid integer")
    
    def _validate_database_config(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate database operation configuration."""
        if "operation_type" not in config:
            errors.append("Missing required field: operation_type")
        
        operation_type = config.get("operation_type", "").lower()
        if operation_type not in ["query", "execute", "transaction"]:
            errors.append("operation_type must be one of: query, execute, transaction")
        
        if "sql_query" not in config:
            errors.append("Missing required field: sql_query")
        
        # Basic SQL injection checks
        if "sql_query" in config:
            sql = config["sql_query"].lower()
            dangerous_patterns = ["drop table", "truncate", "delete from", "update "]
            if operation_type == "query":
                for pattern in dangerous_patterns:
                    if pattern in sql:
                        errors.append(f"Dangerous SQL operation '{pattern}' not allowed in query operations")
        
        # Validate connection settings
        if "connection_name" in config and not isinstance(config["connection_name"], str):
            errors.append("connection_name must be a string")
    
    def _validate_function_config(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Validate function execution configuration."""
        if "function_name" not in config:
            errors.append("Missing required field: function_name")
        
        # Validate function name format (should be a valid Python identifier)
        if "function_name" in config:
            func_name = config["function_name"]
            if not isinstance(func_name, str) or not func_name.replace(".", "_").replace(":", "_").isidentifier():
                errors.append("function_name must be a valid function identifier")
        
        # Validate timeout
        if "timeout_seconds" in config:
            try:
                timeout = int(config["timeout_seconds"])
                if timeout <= 0:
                    errors.append("timeout_seconds must be positive")
                elif timeout > 3600:
                    warnings.append("timeout_seconds > 3600 (1 hour) may cause long-running executions")
            except (ValueError, TypeError):
                errors.append("timeout_seconds must be a valid integer")
    
    def _validate_generic_config(self, config: Dict[str, Any], errors: List[str], warnings: List[str]):
        """Generic validation for unknown action types."""
        # Check for common sensitive fields
        sensitive_fields = ["password", "secret", "token", "key", "credential"]
        for field in config:
            if any(sensitive in field.lower() for sensitive in sensitive_fields):
                warnings.append(f"Consider encrypting sensitive field: {field}")
        
        # Check for reasonable timeout values
        if "timeout_seconds" in config:
            try:
                timeout = int(config["timeout_seconds"])
                if timeout <= 0:
                    errors.append("timeout_seconds must be positive")
                elif timeout > 3600:
                    warnings.append("timeout_seconds > 3600 may cause long-running executions")
            except (ValueError, TypeError):
                errors.append("timeout_seconds must be a valid integer")
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format using regex."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None