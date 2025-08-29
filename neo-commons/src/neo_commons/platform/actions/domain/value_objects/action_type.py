"""Action Type value object."""

from dataclasses import dataclass
from enum import Enum
from typing import Set


class ActionTypeEnum(Enum):
    """Action type enumeration matching platform_common.action_type."""
    # Communication & Notifications
    EMAIL = "email"
    SMS = "sms"
    PUSH_NOTIFICATION = "push_notification"
    WEBHOOK = "webhook"
    SYSTEM_NOTIFICATION = "system_notification"
    SLACK_NOTIFICATION = "slack_notification"
    TEAMS_NOTIFICATION = "teams_notification"
    
    # Function & Code Execution
    FUNCTION_EXECUTION = "function_execution"
    SCRIPT_EXECUTION = "script_execution"
    WORKFLOW_TRIGGER = "workflow_trigger"
    LAMBDA_FUNCTION = "lambda_function"
    BACKGROUND_JOB = "background_job"
    
    # Data & Storage Operations
    DATABASE_OPERATION = "database_operation"
    FILE_OPERATION = "file_operation"
    STORAGE_OPERATION = "storage_operation"
    BACKUP_OPERATION = "backup_operation"
    DATA_SYNC = "data_sync"
    
    # Cache & Performance
    CACHE_INVALIDATION = "cache_invalidation"
    CACHE_WARMING = "cache_warming"
    INDEX_REBUILD = "index_rebuild"
    
    # External Integrations
    EXTERNAL_API = "external_api"
    PAYMENT_PROCESSING = "payment_processing"
    ANALYTICS_TRACKING = "analytics_tracking"
    CRM_SYNC = "crm_sync"
    ERP_SYNC = "erp_sync"
    
    # Security & Compliance
    SECURITY_SCAN = "security_scan"
    COMPLIANCE_CHECK = "compliance_check"
    AUDIT_LOG = "audit_log"
    ACCESS_REVIEW = "access_review"
    
    # Infrastructure & DevOps
    DEPLOYMENT_TRIGGER = "deployment_trigger"
    SCALING_OPERATION = "scaling_operation"
    MONITORING_ALERT = "monitoring_alert"
    HEALTH_CHECK = "health_check"
    
    # Business Logic
    REPORT_GENERATION = "report_generation"
    BATCH_PROCESSING = "batch_processing"
    DATA_PIPELINE = "data_pipeline"
    
    # Extensibility
    CUSTOM = "custom"


@dataclass(frozen=True)
class ActionType:
    """
    Action Type value object.
    
    Represents a valid action type that can be executed by the system.
    Provides validation against the platform_common.action_type enum.
    """
    
    value: str
    
    def __post_init__(self):
        """Validate action type on creation."""
        if not isinstance(self.value, str):
            raise TypeError(f"ActionType value must be string, got {type(self.value)}")
        
        if not self.value:
            raise ValueError("ActionType value cannot be empty")
        
        # Validate against enum values
        valid_types = {action_type.value for action_type in ActionTypeEnum}
        if self.value not in valid_types:
            raise ValueError(
                f"Invalid action type: {self.value}. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )
    
    @classmethod
    def from_enum(cls, action_type_enum: ActionTypeEnum) -> 'ActionType':
        """Create ActionType from ActionTypeEnum."""
        return cls(action_type_enum.value)
    
    @property
    def enum_value(self) -> ActionTypeEnum:
        """Get the corresponding enum value."""
        return ActionTypeEnum(self.value)
    
    @property
    def category(self) -> str:
        """Get the action type category."""
        category_mapping = {
            # Communication & Notifications
            "email": "communication",
            "sms": "communication",
            "push_notification": "communication",
            "webhook": "communication",
            "system_notification": "communication",
            "slack_notification": "communication",
            "teams_notification": "communication",
            
            # Function & Code Execution
            "function_execution": "execution",
            "script_execution": "execution",
            "workflow_trigger": "execution",
            "lambda_function": "execution",
            "background_job": "execution",
            
            # Data & Storage Operations
            "database_operation": "data",
            "file_operation": "data",
            "storage_operation": "data",
            "backup_operation": "data",
            "data_sync": "data",
            
            # Cache & Performance
            "cache_invalidation": "performance",
            "cache_warming": "performance",
            "index_rebuild": "performance",
            
            # External Integrations
            "external_api": "integration",
            "payment_processing": "integration",
            "analytics_tracking": "integration",
            "crm_sync": "integration",
            "erp_sync": "integration",
            
            # Security & Compliance
            "security_scan": "security",
            "compliance_check": "security",
            "audit_log": "security",
            "access_review": "security",
            
            # Infrastructure & DevOps
            "deployment_trigger": "infrastructure",
            "scaling_operation": "infrastructure",
            "monitoring_alert": "infrastructure",
            "health_check": "infrastructure",
            
            # Business Logic
            "report_generation": "business",
            "batch_processing": "business",
            "data_pipeline": "business",
            
            # Extensibility
            "custom": "custom",
        }
        return category_mapping.get(self.value, "unknown")
    
    def is_communication_action(self) -> bool:
        """Check if this is a communication action type."""
        return self.category == "communication"
    
    def is_data_action(self) -> bool:
        """Check if this is a data operation action type."""
        return self.category == "data"
    
    def is_execution_action(self) -> bool:
        """Check if this is an execution action type."""
        return self.category == "execution"
    
    def is_security_action(self) -> bool:
        """Check if this is a security action type."""
        return self.category == "security"
    
    def requires_external_service(self) -> bool:
        """Check if this action type requires external service integration."""
        external_types = {
            "email", "sms", "push_notification", "webhook", 
            "slack_notification", "teams_notification",
            "external_api", "payment_processing", "analytics_tracking",
            "crm_sync", "erp_sync"
        }
        return self.value in external_types
    
    @classmethod
    def get_all_valid_types(cls) -> Set[str]:
        """Get all valid action type values."""
        return {action_type.value for action_type in ActionTypeEnum}
    
    @classmethod
    def get_types_by_category(cls, category: str) -> Set[str]:
        """Get all action types in a specific category."""
        all_types = cls.get_all_valid_types()
        return {
            action_type for action_type in all_types
            if cls(action_type).category == category
        }
    
    def __str__(self) -> str:
        """String representation returns the action type value."""
        return self.value
    
    def __hash__(self) -> int:
        """Hash based on action type value."""
        return hash(self.value)
    
    def __eq__(self, other) -> bool:
        """Equality based on action type value."""
        if isinstance(other, ActionType):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False