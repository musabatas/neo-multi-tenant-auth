"""
Service layer for reference data management.
"""

from typing import Optional, List
from src.common.services.base import BaseService
from src.common.models import PaginationParams
from ..models.domain import Currency, Country, Language
from ..models.request import CurrencyFilter, CountryFilter, LanguageFilter
from ..models.response import (
    CurrencyResponse, CountryResponse, LanguageResponse,
    CurrencyListResponse, CountryListResponse, LanguageListResponse
)
from ..repositories.reference_data_repository import (
    CurrencyRepository, CountryRepository, LanguageRepository
)


class CurrencyService(BaseService):
    """Service for currency reference data."""
    
    def __init__(self, repository: CurrencyRepository):
        """Initialize currency service.
        
        Args:
            repository: Currency repository for database operations
        """
        super().__init__()
        self.repository = repository
    
    async def get_currency(self, code: str) -> CurrencyResponse:
        """Get a currency by code.
        
        Args:
            code: Currency code (ISO 4217)
            
        Returns:
            CurrencyResponse with currency details
        """
        currency = await self.repository.get_by_code(code.upper())
        return CurrencyResponse.from_domain(currency)
    
    async def list_currencies(
        self,
        filters: Optional[CurrencyFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> CurrencyListResponse:
        """List currencies with optional filters and pagination.
        
        Args:
            filters: Optional filters for currencies
            pagination: Optional pagination parameters
            
        Returns:
            CurrencyListResponse with currencies and metadata
        """
        if pagination is None:
            pagination = PaginationParams(page=1, page_size=50)
        
        # Validate pagination
        self.validate_pagination_params(pagination.page, pagination.page_size)
        
        # Get currencies from repository
        offset = (pagination.page - 1) * pagination.page_size
        currencies, total_count = await self.repository.list(
            filters=filters,
            limit=pagination.page_size,
            offset=offset
        )
        
        # Build response
        response_items = [
            CurrencyResponse.from_domain(currency) for currency in currencies
        ]
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page, pagination.page_size, total_count
        )
        
        return CurrencyListResponse(
            items=response_items,
            pagination=pagination_meta
        )
    
    async def get_active_currencies(self) -> List[CurrencyResponse]:
        """Get all active currencies.
        
        Returns:
            List of active currencies
        """
        currencies = await self.repository.get_active_currencies()
        return [CurrencyResponse.from_domain(currency) for currency in currencies]


class CountryService(BaseService):
    """Service for country reference data."""
    
    def __init__(self, repository: CountryRepository):
        """Initialize country service.
        
        Args:
            repository: Country repository for database operations
        """
        super().__init__()
        self.repository = repository
    
    async def get_country(self, code: str) -> CountryResponse:
        """Get a country by code.
        
        Args:
            code: Country code (ISO 3166-1 alpha-2)
            
        Returns:
            CountryResponse with country details
        """
        country = await self.repository.get_by_code(code.upper())
        return CountryResponse.from_domain(country)
    
    async def get_country_by_code3(self, code3: str) -> CountryResponse:
        """Get a country by ISO 3166-1 alpha-3 code.
        
        Args:
            code3: Country code (ISO 3166-1 alpha-3)
            
        Returns:
            CountryResponse with country details
        """
        country = await self.repository.get_by_code3(code3.upper())
        return CountryResponse.from_domain(country)
    
    async def list_countries(
        self,
        filters: Optional[CountryFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> CountryListResponse:
        """List countries with optional filters and pagination.
        
        Args:
            filters: Optional filters for countries
            pagination: Optional pagination parameters
            
        Returns:
            CountryListResponse with countries and metadata
        """
        if pagination is None:
            pagination = PaginationParams(page=1, page_size=50)
        
        # Validate pagination
        self.validate_pagination_params(pagination.page, pagination.page_size)
        
        # Get countries from repository
        offset = (pagination.page - 1) * pagination.page_size
        countries, total_count = await self.repository.list(
            filters=filters,
            limit=pagination.page_size,
            offset=offset
        )
        
        # Build response
        response_items = [
            CountryResponse.from_domain(country) for country in countries
        ]
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page, pagination.page_size, total_count
        )
        
        return CountryListResponse(
            items=response_items,
            pagination=pagination_meta
        )
    
    async def get_countries_by_continent(self, continent: str) -> List[CountryResponse]:
        """Get all countries in a continent.
        
        Args:
            continent: Continent name
            
        Returns:
            List of countries in the continent
        """
        countries = await self.repository.get_by_continent(continent)
        return [CountryResponse.from_domain(country) for country in countries]
    
    async def get_gdpr_countries(self) -> List[CountryResponse]:
        """Get all GDPR-applicable countries.
        
        Returns:
            List of GDPR countries
        """
        countries = await self.repository.get_gdpr_countries()
        return [CountryResponse.from_domain(country) for country in countries]


class LanguageService(BaseService):
    """Service for language reference data."""
    
    def __init__(self, repository: LanguageRepository):
        """Initialize language service.
        
        Args:
            repository: Language repository for database operations
        """
        super().__init__()
        self.repository = repository
    
    async def get_language(self, code: str) -> LanguageResponse:
        """Get a language by code.
        
        Args:
            code: Language code (ISO 639)
            
        Returns:
            LanguageResponse with language details
        """
        language = await self.repository.get_by_code(code.lower())
        return LanguageResponse.from_domain(language)
    
    async def get_language_by_iso639_1(self, iso639_1: str) -> LanguageResponse:
        """Get a language by ISO 639-1 code.
        
        Args:
            iso639_1: Language code (ISO 639-1)
            
        Returns:
            LanguageResponse with language details
        """
        language = await self.repository.get_by_iso639_1(iso639_1.lower())
        return LanguageResponse.from_domain(language)
    
    async def list_languages(
        self,
        filters: Optional[LanguageFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> LanguageListResponse:
        """List languages with optional filters and pagination.
        
        Args:
            filters: Optional filters for languages
            pagination: Optional pagination parameters
            
        Returns:
            LanguageListResponse with languages and metadata
        """
        if pagination is None:
            pagination = PaginationParams(page=1, page_size=50)
        
        # Validate pagination
        self.validate_pagination_params(pagination.page, pagination.page_size)
        
        # Get languages from repository
        offset = (pagination.page - 1) * pagination.page_size
        languages, total_count = await self.repository.list(
            filters=filters,
            limit=pagination.page_size,
            offset=offset
        )
        
        # Build response
        response_items = [
            LanguageResponse.from_domain(language) for language in languages
        ]
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page, pagination.page_size, total_count
        )
        
        return LanguageListResponse(
            items=response_items,
            pagination=pagination_meta
        )
    
    async def get_active_languages(self) -> List[LanguageResponse]:
        """Get all active languages.
        
        Returns:
            List of active languages
        """
        languages = await self.repository.get_active_languages()
        return [LanguageResponse.from_domain(language) for language in languages]