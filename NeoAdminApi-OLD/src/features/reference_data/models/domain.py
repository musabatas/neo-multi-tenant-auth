"""
Domain models for reference data.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ReferenceStatus(str, Enum):
    """Reference data status enum."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    HISTORICAL = "historical"


class Currency(BaseModel):
    """Domain model for ISO 4217 currency."""
    model_config = ConfigDict(from_attributes=True)
    
    # ISO 4217 Standard (Primary Key)
    code: str = Field(..., min_length=3, max_length=3, description="ISO 4217 alphabetic code")
    numeric_code: Optional[str] = Field(None, min_length=3, max_length=3, description="ISO 4217 numeric code")
    minor_unit: int = Field(2, ge=0, le=6, description="Number of decimal places")
    
    # Essential Information
    name: str = Field(..., max_length=100, description="Official currency name")
    symbol: Optional[str] = Field(None, max_length=5, description="Currency symbol")
    
    # Basic Metadata
    status: ReferenceStatus = Field(ReferenceStatus.ACTIVE, description="Currency status")
    is_cryptocurrency: bool = Field(False, description="Is cryptocurrency flag")
    is_legal_tender: bool = Field(True, description="Is legal tender flag")
    
    # System Fields
    created_at: datetime
    updated_at: datetime


class Country(BaseModel):
    """Domain model for ISO 3166 country."""
    model_config = ConfigDict(from_attributes=True)
    
    # ISO 3166-1 Standard (Primary Key)
    code: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 code")
    code3: str = Field(..., min_length=3, max_length=3, description="ISO 3166-1 alpha-3 code")
    numeric_code: str = Field(..., min_length=3, max_length=3, description="ISO 3166-1 numeric code")
    
    # Essential Information
    name: str = Field(..., max_length=100, description="Official short name")
    official_name: Optional[str] = Field(None, max_length=200, description="Official full name")
    region: str = Field(..., max_length=50, description="Geographic region")
    continent: str = Field(..., max_length=20, description="Continent")
    
    # Basic Metadata
    status: ReferenceStatus = Field(ReferenceStatus.ACTIVE, description="Country status")
    calling_code: Optional[str] = Field(None, max_length=10, description="International calling code")
    default_currency_code: Optional[str] = Field(None, min_length=3, max_length=3, description="Primary currency code")
    
    # Compliance Flags
    gdpr_applicable: bool = Field(False, description="GDPR applicable flag")
    data_localization_required: bool = Field(False, description="Data localization required flag")
    
    # System Fields
    created_at: datetime
    updated_at: datetime


class Language(BaseModel):
    """Domain model for ISO 639 language."""
    model_config = ConfigDict(from_attributes=True)
    
    # ISO 639 Standard (Primary Key)
    code: str = Field(..., max_length=10, description="ISO 639-1/639-3 code")
    iso639_1: Optional[str] = Field(None, min_length=2, max_length=2, description="ISO 639-1 two-letter code")
    iso639_2: Optional[str] = Field(None, min_length=3, max_length=3, description="ISO 639-2 three-letter code")
    
    # Essential Information
    name: str = Field(..., max_length=100, description="English name")
    native_name: str = Field(..., max_length=100, description="Native name")
    
    # Basic Metadata
    status: ReferenceStatus = Field(ReferenceStatus.ACTIVE, description="Language status")
    writing_direction: str = Field("ltr", description="Writing direction (ltr, rtl, ttb)")
    
    # System Fields
    created_at: datetime
    updated_at: datetime