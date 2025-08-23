"""Centralized logging configuration for neo-commons and services.

Provides consistent, configurable logging across all services with
environment-based control over verbosity and log levels.
"""

import logging
import logging.config
import os
import sys
from typing import Dict, Any, Optional
from enum import Enum


class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogVerbosity(str, Enum):
    """Log verbosity modes."""
    QUIET = "QUIET"      # Only errors and critical
    NORMAL = "NORMAL"    # Standard logging (warnings and above)
    VERBOSE = "VERBOSE"  # Info level logging
    DEBUG = "DEBUG"      # Full debug logging


def get_log_level_from_verbosity(verbosity: str) -> str:
    """Map verbosity mode to log level."""
    verbosity_map = {
        LogVerbosity.QUIET: LogLevel.ERROR.value,
        LogVerbosity.NORMAL: LogLevel.WARNING.value,
        LogVerbosity.VERBOSE: LogLevel.INFO.value,
        LogVerbosity.DEBUG: LogLevel.DEBUG.value,
    }
    return verbosity_map.get(LogVerbosity(verbosity.upper()), LogLevel.WARNING.value)


def should_log_module(module_name: str, excluded_modules: list) -> bool:
    """Check if module should be logged based on exclusion list."""
    for excluded in excluded_modules:
        if module_name.startswith(excluded):
            return False
    return True


class LoggingConfig:
    """Centralized logging configuration manager."""
    
    # Default modules to reduce verbosity for
    DEFAULT_QUIET_MODULES = [
        "neo_commons.features.database.repositories.connection_registry",
        "neo_commons.features.database.repositories.health_checker",
        "neo_commons.features.users.repositories",
        "neo_commons.features.users.services",
        "neo_commons.features.auth.adapters.keycloak_openid",
        "neo_commons.features.auth.adapters.keycloak_admin",
    ]
    
    # Modules that should only log errors
    ERROR_ONLY_MODULES = [
        "httpx",
        "httpcore",
        "urllib3",
        "asyncio",
    ]
    
    @classmethod
    def configure(cls) -> None:
        """Configure logging based on environment variables."""
        # Get configuration from environment
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_verbosity = os.getenv("LOG_VERBOSITY", "NORMAL").upper()
        log_format = os.getenv("LOG_FORMAT", "simple")
        enable_sql_logging = os.getenv("ENABLE_SQL_LOGGING", "false").lower() == "true"
        enable_auth_logging = os.getenv("ENABLE_AUTH_LOGGING", "false").lower() == "true"
        enable_db_logging = os.getenv("ENABLE_DB_LOGGING", "false").lower() == "true"
        
        # Use verbosity to determine log level
        effective_log_level = get_log_level_from_verbosity(log_verbosity)
        
        # Configure log format
        if log_format == "json":
            format_string = '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","message":"%(message)s"}'
        elif log_format == "detailed":
            format_string = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        else:  # simple
            format_string = "%(asctime)s - %(levelname)s - %(message)s"
        
        # Create logging configuration
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": format_string,
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": effective_log_level,
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": effective_log_level,
                "handlers": ["console"],
            },
            "loggers": {}
        }
        
        # Configure quiet modules (reduce verbosity)
        for module in cls.DEFAULT_QUIET_MODULES:
            logging_config["loggers"][module] = {
                "level": "WARNING" if effective_log_level != "DEBUG" else "DEBUG",
                "handlers": ["console"],
                "propagate": False,
            }
        
        # Configure error-only modules
        for module in cls.ERROR_ONLY_MODULES:
            logging_config["loggers"][module] = {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            }
        
        # Configure specific feature logging
        if not enable_sql_logging:
            logging_config["loggers"]["asyncpg"] = {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            }
        
        if not enable_auth_logging:
            for module in ["neo_commons.features.auth", "src.features.auth"]:
                if module not in logging_config["loggers"]:
                    logging_config["loggers"][module] = {
                        "level": "WARNING" if effective_log_level != "DEBUG" else "INFO",
                        "handlers": ["console"],
                        "propagate": False,
                    }
        
        if not enable_db_logging:
            logging_config["loggers"]["neo_commons.features.database"] = {
                "level": "WARNING" if effective_log_level != "DEBUG" else "INFO",
                "handlers": ["console"],
                "propagate": False,
            }
        
        # Apply configuration
        logging.config.dictConfig(logging_config)
        
        # Log configuration info (only in debug mode)
        logger = logging.getLogger(__name__)
        if effective_log_level == "DEBUG":
            logger.debug(f"Logging configured: level={effective_log_level}, format={log_format}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a configured logger for the given module name.
        
        Args:
            name: Module name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)
    
    @classmethod
    def set_module_level(cls, module_name: str, level: str) -> None:
        """Set log level for a specific module.
        
        Args:
            module_name: Name of the module
            level: Log level to set
        """
        logger = logging.getLogger(module_name)
        logger.setLevel(getattr(logging, level.upper()))
    
    @classmethod
    def silence_module(cls, module_name: str) -> None:
        """Silence all logging from a module.
        
        Args:
            module_name: Name of the module to silence
        """
        cls.set_module_level(module_name, "CRITICAL")


class LogFormat(str, Enum):
    """Log format options."""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"


def setup_logging() -> None:
    """Setup logging configuration from environment variables.
    
    This is the main entry point for configuring logging in the application.
    It should be called once at application startup.
    """
    LoggingConfig.configure()


# Convenience function for backward compatibility
def configure_logging() -> None:
    """Configure logging based on environment settings."""
    LoggingConfig.configure()


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return LoggingConfig.get_logger(name)