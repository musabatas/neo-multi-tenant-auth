"""
Response models for reference data API endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from src.common.models import PaginationMetadata
from src.common.utils import format_iso8601
from .domain import Currency, Country, Language, ReferenceStatus


class CurrencyResponse(BaseModel):
    """Response model for a currency."""
    code: str
    numeric_code: Optional[str]
    minor_unit: int
    name: str
    symbol: Optional[str]
    status: ReferenceStatus
    is_cryptocurrency: bool
    is_legal_tender: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: format_iso8601
        }
    
    @classmethod
    def from_domain(cls, currency: Currency) -> "CurrencyResponse":
        """Create response from domain model."""
        return cls(**currency.model_dump())


class CountryResponse(BaseModel):
    """Response model for a country."""
    code: str
    code3: str
    numeric_code: str
    name: str
    official_name: Optional[str]
    region: str
    continent: str
    status: ReferenceStatus
    calling_code: Optional[str]
    default_currency_code: Optional[str]
    gdpr_applicable: bool
    data_localization_required: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: format_iso8601
        }
    
    @classmethod
    def from_domain(cls, country: Country) -> "CountryResponse":
        """Create response from domain model."""
        return cls(**country.model_dump())


class LanguageResponse(BaseModel):
    """Response model for a language."""
    code: str
    iso639_1: Optional[str]
    iso639_2: Optional[str]
    name: str
    native_name: str
    status: ReferenceStatus
    writing_direction: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: format_iso8601
        }
    
    @classmethod
    def from_domain(cls, language: Language) -> "LanguageResponse":
        """Create response from domain model."""
        return cls(**language.model_dump())


class CurrencyListResponse(BaseModel):
    """Response model for paginated currency list."""
    items: List[CurrencyResponse]
    pagination: PaginationMetadata


class CountryListResponse(BaseModel):
    """Response model for paginated country list."""
    items: List[CountryResponse]
    pagination: PaginationMetadata


class LanguageListResponse(BaseModel):
    """Response model for paginated language list."""
    items: List[LanguageResponse]
    pagination: PaginationMetadata