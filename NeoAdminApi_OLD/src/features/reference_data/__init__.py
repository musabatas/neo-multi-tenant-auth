"""
Reference Data feature module.

Provides read-only access to platform-wide reference data including:
- Currencies (ISO 4217)
- Countries (ISO 3166)
- Languages (ISO 639)

This data is sourced from platform_common schema and is shared across all tenants.
"""

from .routers.v1 import router as reference_data_router

__all__ = ["reference_data_router"]