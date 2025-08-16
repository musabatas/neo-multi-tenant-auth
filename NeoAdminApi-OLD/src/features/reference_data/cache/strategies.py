"""
Caching strategies for reference data.
Reference data is relatively static, so we can cache aggressively.
"""

from typing import Optional, List, Any, Dict
from src.common.cache.client import CacheClient
from src.common.utils.datetime import utc_now


class ReferenceDataCache:
    """Cache manager for reference data."""
    
    # Cache TTL settings (reference data is relatively static)
    ACTIVE_LIST_TTL = 3600 * 24  # 24 hours for active lists
    ITEM_TTL = 3600 * 12         # 12 hours for individual items
    FILTERED_LIST_TTL = 3600 * 6 # 6 hours for filtered lists
    
    def __init__(self, cache_client: CacheClient):
        """Initialize cache with client.
        
        Args:
            cache_client: Cache client instance
        """
        self.cache = cache_client
        self.prefix = "ref_data"
    
    def _make_key(self, *parts: str) -> str:
        """Create cache key with prefix.
        
        Args:
            *parts: Key parts to join
            
        Returns:
            Formatted cache key
        """
        return f"{self.prefix}:{':'.join(parts)}"
    
    def _make_filter_key(self, entity_type: str, filters: Dict[str, Any], page: int, page_size: int) -> str:
        """Create cache key for filtered lists.
        
        Args:
            entity_type: Type of entity (currencies, countries, languages)
            filters: Filter parameters
            page: Page number
            page_size: Page size
            
        Returns:
            Cache key for filtered list
        """
        # Sort filters for consistent key generation
        sorted_filters = sorted(filters.items()) if filters else []
        filter_str = "&".join([f"{k}={v}" for k, v in sorted_filters if v is not None])
        
        return self._make_key(
            entity_type, 
            "filtered",
            f"filters={filter_str}",
            f"page={page}",
            f"size={page_size}"
        )
    
    # Currency caching methods
    async def get_currency(self, code: str) -> Optional[Dict[str, Any]]:
        """Get cached currency by code."""
        key = self._make_key("currency", code.upper())
        return await self.cache.get(key)
    
    async def set_currency(self, code: str, currency_data: Dict[str, Any]) -> None:
        """Cache currency data."""
        key = self._make_key("currency", code.upper())
        await self.cache.set(key, currency_data, ttl=self.ITEM_TTL)
    
    async def get_active_currencies(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached active currencies list."""
        key = self._make_key("currencies", "active")
        return await self.cache.get(key)
    
    async def set_active_currencies(self, currencies: List[Dict[str, Any]]) -> None:
        """Cache active currencies list."""
        key = self._make_key("currencies", "active")
        await self.cache.set(key, currencies, ttl=self.ACTIVE_LIST_TTL)
    
    async def get_currencies_list(self, filters: Dict[str, Any], page: int, page_size: int) -> Optional[Dict[str, Any]]:
        """Get cached filtered currencies list."""
        key = self._make_filter_key("currencies", filters, page, page_size)
        return await self.cache.get(key)
    
    async def set_currencies_list(
        self, 
        filters: Dict[str, Any], 
        page: int, 
        page_size: int, 
        result: Dict[str, Any]
    ) -> None:
        """Cache filtered currencies list."""
        key = self._make_filter_key("currencies", filters, page, page_size)
        await self.cache.set(key, result, ttl=self.FILTERED_LIST_TTL)
    
    # Country caching methods
    async def get_country(self, code: str) -> Optional[Dict[str, Any]]:
        """Get cached country by code."""
        key = self._make_key("country", code.upper())
        return await self.cache.get(key)
    
    async def set_country(self, code: str, country_data: Dict[str, Any]) -> None:
        """Cache country data."""
        key = self._make_key("country", code.upper())
        await self.cache.set(key, country_data, ttl=self.ITEM_TTL)
    
    async def get_country_by_code3(self, code3: str) -> Optional[Dict[str, Any]]:
        """Get cached country by alpha-3 code."""
        key = self._make_key("country", "code3", code3.upper())
        return await self.cache.get(key)
    
    async def set_country_by_code3(self, code3: str, country_data: Dict[str, Any]) -> None:
        """Cache country data by alpha-3 code."""
        key = self._make_key("country", "code3", code3.upper())
        await self.cache.set(key, country_data, ttl=self.ITEM_TTL)
    
    async def get_countries_by_continent(self, continent: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached countries by continent."""
        key = self._make_key("countries", "continent", continent.lower())
        return await self.cache.get(key)
    
    async def set_countries_by_continent(self, continent: str, countries: List[Dict[str, Any]]) -> None:
        """Cache countries by continent."""
        key = self._make_key("countries", "continent", continent.lower())
        await self.cache.set(key, countries, ttl=self.ACTIVE_LIST_TTL)
    
    async def get_gdpr_countries(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached GDPR countries."""
        key = self._make_key("countries", "gdpr")
        return await self.cache.get(key)
    
    async def set_gdpr_countries(self, countries: List[Dict[str, Any]]) -> None:
        """Cache GDPR countries."""
        key = self._make_key("countries", "gdpr")
        await self.cache.set(key, countries, ttl=self.ACTIVE_LIST_TTL)
    
    async def get_countries_list(self, filters: Dict[str, Any], page: int, page_size: int) -> Optional[Dict[str, Any]]:
        """Get cached filtered countries list."""
        key = self._make_filter_key("countries", filters, page, page_size)
        return await self.cache.get(key)
    
    async def set_countries_list(
        self, 
        filters: Dict[str, Any], 
        page: int, 
        page_size: int, 
        result: Dict[str, Any]
    ) -> None:
        """Cache filtered countries list."""
        key = self._make_filter_key("countries", filters, page, page_size)
        await self.cache.set(key, result, ttl=self.FILTERED_LIST_TTL)
    
    # Language caching methods
    async def get_language(self, code: str) -> Optional[Dict[str, Any]]:
        """Get cached language by code."""
        key = self._make_key("language", code.lower())
        return await self.cache.get(key)
    
    async def set_language(self, code: str, language_data: Dict[str, Any]) -> None:
        """Cache language data."""
        key = self._make_key("language", code.lower())
        await self.cache.set(key, language_data, ttl=self.ITEM_TTL)
    
    async def get_language_by_iso639_1(self, iso639_1: str) -> Optional[Dict[str, Any]]:
        """Get cached language by ISO 639-1 code."""
        key = self._make_key("language", "iso639_1", iso639_1.lower())
        return await self.cache.get(key)
    
    async def set_language_by_iso639_1(self, iso639_1: str, language_data: Dict[str, Any]) -> None:
        """Cache language data by ISO 639-1 code."""
        key = self._make_key("language", "iso639_1", iso639_1.lower())
        await self.cache.set(key, language_data, ttl=self.ITEM_TTL)
    
    async def get_active_languages(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached active languages list."""
        key = self._make_key("languages", "active")
        return await self.cache.get(key)
    
    async def set_active_languages(self, languages: List[Dict[str, Any]]) -> None:
        """Cache active languages list."""
        key = self._make_key("languages", "active")
        await self.cache.set(key, languages, ttl=self.ACTIVE_LIST_TTL)
    
    async def get_languages_list(self, filters: Dict[str, Any], page: int, page_size: int) -> Optional[Dict[str, Any]]:
        """Get cached filtered languages list."""
        key = self._make_filter_key("languages", filters, page, page_size)
        return await self.cache.get(key)
    
    async def set_languages_list(
        self, 
        filters: Dict[str, Any], 
        page: int, 
        page_size: int, 
        result: Dict[str, Any]
    ) -> None:
        """Cache filtered languages list."""
        key = self._make_filter_key("languages", filters, page, page_size)
        await self.cache.set(key, result, ttl=self.FILTERED_LIST_TTL)
    
    # Cache invalidation methods
    async def invalidate_currency(self, code: str) -> None:
        """Invalidate currency cache."""
        key = self._make_key("currency", code.upper())
        await self.cache.delete(key)
        
        # Also invalidate active list
        await self.cache.delete(self._make_key("currencies", "active"))
    
    async def invalidate_country(self, code: str, code3: Optional[str] = None) -> None:
        """Invalidate country cache."""
        key = self._make_key("country", code.upper())
        await self.cache.delete(key)
        
        if code3:
            key3 = self._make_key("country", "code3", code3.upper())
            await self.cache.delete(key3)
    
    async def invalidate_language(self, code: str, iso639_1: Optional[str] = None) -> None:
        """Invalidate language cache."""
        key = self._make_key("language", code.lower())
        await self.cache.delete(key)
        
        if iso639_1:
            key_iso = self._make_key("language", "iso639_1", iso639_1.lower())
            await self.cache.delete(key_iso)
        
        # Also invalidate active list
        await self.cache.delete(self._make_key("languages", "active"))
    
    async def invalidate_all_reference_data(self) -> None:
        """Invalidate all reference data cache."""
        pattern = f"{self.prefix}:*"
        await self.cache.delete_pattern(pattern)