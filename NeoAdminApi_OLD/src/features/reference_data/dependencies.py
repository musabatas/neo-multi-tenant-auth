"""
Dependencies for reference data feature.
"""

from fastapi import Depends
from src.common.cache.client import get_cache
from .repositories.reference_data_repository import (
    CurrencyRepository, CountryRepository, LanguageRepository
)
from .services.reference_data_service import (
    CurrencyService, CountryService, LanguageService
)
from .cache.strategies import ReferenceDataCache


# Repository dependencies using neo-commons patterns
def get_currency_repository() -> CurrencyRepository:
    """Get currency repository instance using neo-commons patterns."""
    return CurrencyRepository()


def get_country_repository() -> CountryRepository:
    """Get country repository instance using neo-commons patterns."""
    return CountryRepository()


def get_language_repository() -> LanguageRepository:
    """Get language repository instance using neo-commons patterns."""
    return LanguageRepository()


# Cache dependency
def get_reference_data_cache() -> ReferenceDataCache:
    """Get reference data cache instance."""
    cache_client = get_cache()
    return ReferenceDataCache(cache_client)


# Service dependencies
def get_currency_service(
    repository: CurrencyRepository = Depends(get_currency_repository)
) -> CurrencyService:
    """Get currency service instance."""
    return CurrencyService(repository)


def get_country_service(
    repository: CountryRepository = Depends(get_country_repository)
) -> CountryService:
    """Get country service instance."""
    return CountryService(repository)


def get_language_service(
    repository: LanguageRepository = Depends(get_language_repository)
) -> LanguageService:
    """Get language service instance."""
    return LanguageService(repository)