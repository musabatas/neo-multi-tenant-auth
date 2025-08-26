"""Logging configuration for the events feature."""

import logging
import logging.config
from typing import Dict, Any, Optional
from datetime import datetime
import json


class EventActionFormatter(logging.Formatter):
    """Custom formatter for event action logs with structured output."""
    
    def __init__(self, include_extra_fields: bool = True):
        """Initialize formatter.
        
        Args:
            include_extra_fields: Whether to include extra context fields
        """
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Basic log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if available and enabled
        if self.include_extra_fields and hasattr(record, '__dict__'):
            extra_fields = {}
            
            # Event action specific fields
            event_fields = [
                'action_id', 'action_name', 'execution_id', 'event_type', 
                'handler_type', 'execution_mode', 'status', 'duration_ms',
                'retry_count', 'error_message', 'tenant_id', 'user_id'
            ]
            
            for field in event_fields:
                if hasattr(record, field):
                    extra_fields[field] = getattr(record, field)
            
            # Alert specific fields
            alert_fields = [
                'alert_type', 'threshold', 'success_rate', 'total_executions'
            ]
            
            for field in alert_fields:
                if hasattr(record, field):
                    extra_fields[field] = getattr(record, field)
            
            if extra_fields:
                log_data["context"] = extra_fields
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class EventActionFilter(logging.Filter):
    """Filter for event action related logs."""
    
    def __init__(self, min_level: str = "INFO", include_patterns: Optional[list] = None):
        """Initialize filter.
        
        Args:
            min_level: Minimum log level to include
            include_patterns: Patterns to include (module names, etc.)
        """
        super().__init__()
        self.min_level = getattr(logging, min_level.upper())
        self.include_patterns = include_patterns or []
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on criteria."""
        # Check minimum level
        if record.levelno < self.min_level:
            return False
        
        # Check include patterns
        if self.include_patterns:
            for pattern in self.include_patterns:
                if pattern in record.name or pattern in record.module:
                    return True
            return False
        
        return True


def setup_event_action_logging(
    log_level: str = "INFO",
    enable_structured_logging: bool = True,
    log_file_path: Optional[str] = None,
    enable_console_logging: bool = True,
    include_extra_fields: bool = True
) -> None:
    """Setup logging configuration for event actions.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_structured_logging: Whether to use structured JSON logging
        log_file_path: Path to log file (optional)
        enable_console_logging: Whether to log to console
        include_extra_fields: Whether to include extra context fields
    """
    # Create formatters
    if enable_structured_logging:
        formatter = EventActionFormatter(include_extra_fields=include_extra_fields)
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Create handlers
    handlers = {}
    
    if enable_console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        console_handler.addFilter(EventActionFilter(min_level=log_level))
        handlers['console'] = console_handler
    
    if log_file_path:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(EventActionFilter(min_level=log_level))
        handlers['file'] = file_handler
    
    # Configure loggers
    event_logger_names = [
        'neo_commons.features.events',
        'neo_commons.features.events.services',
        'neo_commons.features.events.handlers',
        'neo_commons.features.events.repositories'
    ]
    
    for logger_name in event_logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        logger.handlers = []
        
        # Add new handlers
        for handler in handlers.values():
            logger.addHandler(handler)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False


def get_logging_config_dict(
    log_level: str = "INFO",
    log_file_path: Optional[str] = None,
    enable_structured_logging: bool = True
) -> Dict[str, Any]:
    """Get logging configuration dictionary for dictConfig.
    
    Args:
        log_level: Logging level
        log_file_path: Optional log file path
        enable_structured_logging: Whether to use structured logging
        
    Returns:
        Configuration dictionary for logging.config.dictConfig
    """
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'filters': {
            'event_action_filter': {
                '()': EventActionFilter,
                'min_level': log_level,
                'include_patterns': ['neo_commons.features.events']
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'filters': ['event_action_filter'],
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            'neo_commons.features.events': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            }
        }
    }
    
    # Add structured formatter if enabled
    if enable_structured_logging:
        config['formatters']['structured'] = {
            '()': EventActionFormatter,
            'include_extra_fields': True
        }
        config['handlers']['console']['formatter'] = 'structured'
    
    # Add file handler if path provided
    if log_file_path:
        config['handlers']['file'] = {
            'class': 'logging.FileHandler',
            'level': log_level,
            'formatter': 'structured' if enable_structured_logging else 'standard',
            'filters': ['event_action_filter'],
            'filename': log_file_path,
            'mode': 'a',
            'encoding': 'utf-8'
        }
        config['loggers']['neo_commons.features.events']['handlers'].append('file')
    
    return config


class EventActionLogger:
    """Utility class for consistent event action logging."""
    
    def __init__(self, logger_name: str):
        """Initialize logger wrapper.
        
        Args:
            logger_name: Name of the logger
        """
        self.logger = logging.getLogger(logger_name)
    
    def log_action_created(self, action_name: str, action_id: str, handler_type: str) -> None:
        """Log action creation."""
        self.logger.info(
            f"Event action created: {action_name}",
            extra={
                "action_id": action_id,
                "action_name": action_name,
                "handler_type": handler_type,
                "event_type": "action_created"
            }
        )
    
    def log_action_updated(self, action_name: str, action_id: str, fields_updated: list) -> None:
        """Log action update."""
        self.logger.info(
            f"Event action updated: {action_name}",
            extra={
                "action_id": action_id,
                "action_name": action_name,
                "fields_updated": fields_updated,
                "event_type": "action_updated"
            }
        )
    
    def log_action_deleted(self, action_name: str, action_id: str) -> None:
        """Log action deletion."""
        self.logger.info(
            f"Event action deleted: {action_name}",
            extra={
                "action_id": action_id,
                "action_name": action_name,
                "event_type": "action_deleted"
            }
        )
    
    def log_execution_started(
        self, 
        action_name: str, 
        action_id: str, 
        execution_id: str,
        event_type: str
    ) -> None:
        """Log execution start."""
        self.logger.info(
            f"Action execution started: {action_name}",
            extra={
                "action_id": action_id,
                "action_name": action_name,
                "execution_id": execution_id,
                "event_type": event_type,
                "event_action_type": "execution_started"
            }
        )
    
    def log_execution_completed(
        self, 
        action_name: str, 
        action_id: str, 
        execution_id: str,
        status: str,
        duration_ms: int
    ) -> None:
        """Log execution completion."""
        self.logger.info(
            f"Action execution completed: {action_name} ({status})",
            extra={
                "action_id": action_id,
                "action_name": action_name,
                "execution_id": execution_id,
                "status": status,
                "duration_ms": duration_ms,
                "event_action_type": "execution_completed"
            }
        )
    
    def log_execution_failed(
        self, 
        action_name: str, 
        action_id: str, 
        execution_id: str,
        error_message: str,
        retry_count: int = 0
    ) -> None:
        """Log execution failure."""
        self.logger.error(
            f"Action execution failed: {action_name} - {error_message}",
            extra={
                "action_id": action_id,
                "action_name": action_name,
                "execution_id": execution_id,
                "error_message": error_message,
                "retry_count": retry_count,
                "event_action_type": "execution_failed"
            }
        )
    
    def log_high_error_rate_alert(
        self, 
        action_name: str, 
        action_id: str, 
        success_rate: float,
        threshold: float,
        total_executions: int
    ) -> None:
        """Log high error rate alert."""
        self.logger.critical(
            f"HIGH ERROR RATE ALERT: {action_name} success rate {success_rate:.1f}%",
            extra={
                "alert_type": "high_error_rate",
                "action_id": action_id,
                "action_name": action_name,
                "success_rate": success_rate,
                "threshold": threshold,
                "total_executions": total_executions,
                "event_action_type": "alert"
            }
        )