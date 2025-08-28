"""Quota manager service.

ONLY quota management - handles storage limits,
usage tracking, and quota enforcement.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Optional

from ...core.protocols.file_repository import FileRepository


@dataclass
class QuotaManagerConfig:
    """Configuration for quota manager service."""
    
    default_tenant_quota_gb: int = 100  # 100GB default
    default_user_quota_gb: int = 10     # 10GB default
    quota_check_enabled: bool = True
    cache_usage_stats: bool = True


class QuotaManager:
    """Storage quota management service."""
    
    def __init__(
        self,
        file_repository: FileRepository,
        config: Optional[QuotaManagerConfig] = None
    ):
        self._file_repository = file_repository
        self._config = config or QuotaManagerConfig()
    
    async def check_quota(self, tenant_id: str, additional_bytes: int) -> bool:
        """Check if additional storage would exceed quota."""
        # TODO: Implement quota checking
        return True
    
    async def get_usage_stats(self, tenant_id: str) -> dict:
        """Get current storage usage statistics."""
        # TODO: Implement usage calculation
        return {
            "used_bytes": 0,
            "quota_bytes": self._config.default_tenant_quota_gb * 1024 * 1024 * 1024,
            "available_bytes": self._config.default_tenant_quota_gb * 1024 * 1024 * 1024,
            "usage_percentage": 0.0
        }
    
    async def update_quota(self, tenant_id: str, new_quota_bytes: int):
        """Update tenant quota limit."""
        # TODO: Implement quota updates
        pass


def create_quota_manager(
    file_repository: FileRepository,
    config: Optional[QuotaManagerConfig] = None
) -> QuotaManager:
    """Create quota manager service."""
    return QuotaManager(file_repository, config)