"""
Request models for reference data API endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field

from .domain import ReferenceStatus


class ReferenceDataFilter(BaseModel):
    """Base filter parameters for reference data."""
    status: Optional[ReferenceStatus] = Field(None, description="Filter by status")
    search: Optional[str] = Field(None, description="Search in name or code")


class CurrencyFilter(ReferenceDataFilter):
    """Filter parameters for currencies."""
    is_cryptocurrency: Optional[bool] = Field(None, description="Filter by cryptocurrency status")
    is_legal_tender: Optional[bool] = Field(None, description="Filter by legal tender status")
    minor_unit: Optional[int] = Field(None, ge=0, le=6, description="Filter by decimal places")


class CountryFilter(ReferenceDataFilter):
    """Filter parameters for countries."""
    continent: Optional[str] = Field(None, description="Filter by continent")
    region: Optional[str] = Field(None, description="Filter by geographic region")
    gdpr_applicable: Optional[bool] = Field(None, description="Filter by GDPR applicability")
    data_localization_required: Optional[bool] = Field(None, description="Filter by data localization requirement")
    default_currency_code: Optional[str] = Field(None, min_length=3, max_length=3, description="Filter by currency")


class LanguageFilter(ReferenceDataFilter):
    """Filter parameters for languages."""
    writing_direction: Optional[str] = Field(None, description="Filter by writing direction")
    iso639_1: Optional[str] = Field(None, min_length=2, max_length=2, description="Filter by ISO 639-1 code")