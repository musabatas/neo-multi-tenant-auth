"""Quota validator.

ONLY quota validation - handles storage quota checks,
usage calculations, and limit enforcement.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class QuotaValidatorConfig:
    """Configuration for quota validator."""
    
    enforce_tenant_quota: bool = True
    enforce_user_quota: bool = True
    enforce_organization_quota: bool = True
    quota_buffer_percentage: float = 0.05  # 5% buffer before hard limit


class QuotaValidator:
    """Storage quota validation service."""
    
    def __init__(self, config: Optional[QuotaValidatorConfig] = None):
        self._config = config or QuotaValidatorConfig()
    
    async def validate_quota(self, tenant_id: str, additional_bytes: int) -> bool:
        """Validate if upload would exceed quota."""
        # TODO: Implement quota validation logic
        return True


def create_quota_validator(config: Optional[QuotaValidatorConfig] = None) -> QuotaValidator:
    """Create quota validator."""
    return QuotaValidator(config)