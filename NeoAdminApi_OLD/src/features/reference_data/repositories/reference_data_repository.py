"""
Repository for reference data operations.
Accesses read-only data from platform_common schema.
"""

import asyncpg
from typing import Optional, List, Tuple, Dict, Any, TypeVar
from src.common.repositories.base import BaseRepository
from src.common.exceptions import NotFoundError, DatabaseError
from src.common.database.utils import process_database_record
from src.common.models import PaginationParams
from ..models.domain import Currency, Country, Language
from ..models.request import CurrencyFilter, CountryFilter, LanguageFilter

T = TypeVar('T')


class BaseReferenceRepository(BaseRepository[T]):
    """Base repository for reference data operations using neo-commons BaseRepository."""
    
    def __init__(self, table_name: str):
        """Initialize repository with platform_common schema.
        
        Args:
            table_name: The table name in platform_common schema
        """
        super().__init__(table_name=table_name, schema="platform_common")
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create method required by BaseRepository - not used for reference data."""
        raise NotImplementedError("Reference data is read-only")
    
    async def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update method required by BaseRepository - not used for reference data."""
        raise NotImplementedError("Reference data is read-only")
    
    def _build_where_clause(self, filters: dict, base_params: List) -> Tuple[str, List]:
        """Build WHERE clause from filters.
        
        Args:
            filters: Dictionary of filter conditions
            base_params: Base parameters list
            
        Returns:
            Tuple of (where_clause, parameters)
        """
        where_clauses = []
        params = base_params.copy()
        param_count = len(params)
        
        for field, value in filters.items():
            if value is not None:
                param_count += 1
                if field == 'search':
                    # Search in both code and name fields (implementation specific per repository)
                    continue
                else:
                    where_clauses.append(f"{field} = ${param_count}")
                    params.append(value)
        
        return " AND ".join(where_clauses) if where_clauses else "1=1", params


class CurrencyRepository(BaseReferenceRepository):
    """Repository for currency reference data."""
    
    def __init__(self):
        """Initialize currency repository."""
        super().__init__(table_name="currencies")
    
    async def get_by_code(self, code: str) -> Currency:
        """Get currency by code using neo-commons BaseRepository."""
        select_fields = """
            code, numeric_code, minor_unit, name, symbol,
            status, is_cryptocurrency, is_legal_tender,
            created_at, updated_at
        """
        
        table_name = self.get_full_table_name()
        query = f"""
            SELECT {select_fields}
            FROM {table_name}
            WHERE code = $1
        """
        
        db = await self.get_connection()
        row = await db.fetchrow(query, code)
        if not row:
            raise NotFoundError(f"Currency {code} not found")
        
        data = process_database_record(dict(row))
        return Currency(**data)
    
    async def list(
        self,
        filters: Optional[CurrencyFilter] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Currency], int]:
        """List currencies with filters using neo-commons BaseRepository."""
        # Build WHERE clause
        filter_dict = {}
        if filters:
            filter_data = filters.model_dump(exclude_unset=True, exclude={'search'})
            filter_dict.update(filter_data)
        
        where_clause, params = self._build_where_clause(filter_dict, [])
        
        # Add search filter if provided
        if filters and filters.search:
            search_clause = f"(code ILIKE ${len(params) + 1} OR name ILIKE ${len(params) + 2})"
            if where_clause != "1=1":
                where_clause += f" AND {search_clause}"
            else:
                where_clause = search_clause
            params.extend([f"%{filters.search}%", f"%{filters.search}%"])
        
        # Count query
        table_name = self.get_full_table_name()
        count_query = f"""
            SELECT COUNT(*) FROM {table_name}
            WHERE {where_clause}
        """
        
        # Data query
        params.extend([limit, offset])
        data_query = f"""
            SELECT 
                code, numeric_code, minor_unit, name, symbol,
                status, is_cryptocurrency, is_legal_tender,
                created_at, updated_at
            FROM {table_name}
            WHERE {where_clause}
            ORDER BY code ASC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """
        
        try:
            db = await self.get_connection()
            # Execute both queries
            count_params = params[:-2] if params else []
            total_count = await db.fetchval(count_query, *count_params)
            rows = await db.fetch(data_query, *params)
            
            currencies = []
            for row in rows:
                data = process_database_record(dict(row))
                currencies.append(Currency(**data))
            
            return currencies, total_count
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to list currencies: {str(e)}")
    
    async def get_active_currencies(self) -> List[Currency]:
        """Get all active currencies using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, numeric_code, minor_unit, name, symbol,
                status, is_cryptocurrency, is_legal_tender,
                created_at, updated_at
            FROM {table_name}
            WHERE status = 'active'
            ORDER BY code ASC
        """
        
        try:
            db = await self.get_connection()
            rows = await db.fetch(query)
            currencies = []
            for row in rows:
                data = process_database_record(dict(row))
                currencies.append(Currency(**data))
            
            return currencies
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get active currencies: {str(e)}")


class CountryRepository(BaseReferenceRepository):
    """Repository for country reference data."""
    
    def __init__(self):
        """Initialize country repository."""
        super().__init__(table_name="countries")
    
    async def get_by_code(self, code: str) -> Country:
        """Get country by ISO 3166-1 alpha-2 code using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, code3, numeric_code, name, official_name,
                region, continent, status, calling_code, default_currency_code,
                gdpr_applicable, data_localization_required,
                created_at, updated_at
            FROM {table_name}
            WHERE code = $1
        """
        
        try:
            db = await self.get_connection()
            row = await db.fetchrow(query, code)
            if not row:
                raise NotFoundError(f"Country {code} not found")
            
            data = process_database_record(dict(row))
            return Country(**data)
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get country: {str(e)}")
    
    async def get_by_code3(self, code3: str) -> Country:
        """Get country by ISO 3166-1 alpha-3 code using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, code3, numeric_code, name, official_name,
                region, continent, status, calling_code, default_currency_code,
                gdpr_applicable, data_localization_required,
                created_at, updated_at
            FROM {table_name}
            WHERE code3 = $1
        """
        
        try:
            db = await self.get_connection()
            row = await db.fetchrow(query, code3)
            if not row:
                raise NotFoundError(f"Country {code3} not found")
            
            data = process_database_record(dict(row))
            return Country(**data)
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get country: {str(e)}")
    
    async def list(
        self,
        filters: Optional[CountryFilter] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Country], int]:
        """List countries with filters using neo-commons BaseRepository."""
        # Build WHERE clause
        filter_dict = {}
        if filters:
            filter_data = filters.model_dump(exclude_unset=True, exclude={'search'})
            filter_dict.update(filter_data)
        
        where_clause, params = self._build_where_clause(filter_dict, [])
        
        # Add search filter if provided
        if filters and filters.search:
            search_clause = f"(code ILIKE ${len(params) + 1} OR code3 ILIKE ${len(params) + 2} OR name ILIKE ${len(params) + 3})"
            if where_clause != "1=1":
                where_clause += f" AND {search_clause}"
            else:
                where_clause = search_clause
            params.extend([f"%{filters.search}%", f"%{filters.search}%", f"%{filters.search}%"])
        
        # Count query
        table_name = self.get_full_table_name()
        count_query = f"""
            SELECT COUNT(*) FROM {table_name}
            WHERE {where_clause}
        """
        
        # Data query
        params.extend([limit, offset])
        data_query = f"""
            SELECT 
                code, code3, numeric_code, name, official_name,
                region, continent, status, calling_code, default_currency_code,
                gdpr_applicable, data_localization_required,
                created_at, updated_at
            FROM {table_name}
            WHERE {where_clause}
            ORDER BY name ASC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """
        
        try:
            db = await self.get_connection()
            # Execute both queries
            count_params = params[:-2] if params else []
            total_count = await db.fetchval(count_query, *count_params)
            rows = await db.fetch(data_query, *params)
            
            countries = []
            for row in rows:
                data = process_database_record(dict(row))
                countries.append(Country(**data))
            
            return countries, total_count
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to list countries: {str(e)}")
    
    async def get_by_continent(self, continent: str) -> List[Country]:
        """Get all countries in a continent using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, code3, numeric_code, name, official_name,
                region, continent, status, calling_code, default_currency_code,
                gdpr_applicable, data_localization_required,
                created_at, updated_at
            FROM {table_name}
            WHERE continent = $1 AND status = 'active'
            ORDER BY name ASC
        """
        
        try:
            db = await self.get_connection()
            rows = await db.fetch(query, continent)
            countries = []
            for row in rows:
                data = process_database_record(dict(row))
                countries.append(Country(**data))
            
            return countries
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get countries by continent: {str(e)}")
    
    async def get_gdpr_countries(self) -> List[Country]:
        """Get all GDPR-applicable countries using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, code3, numeric_code, name, official_name,
                region, continent, status, calling_code, default_currency_code,
                gdpr_applicable, data_localization_required,
                created_at, updated_at
            FROM {table_name}
            WHERE gdpr_applicable = true AND status = 'active'
            ORDER BY name ASC
        """
        
        try:
            db = await self.get_connection()
            rows = await db.fetch(query)
            countries = []
            for row in rows:
                data = process_database_record(dict(row))
                countries.append(Country(**data))
            
            return countries
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get GDPR countries: {str(e)}")


class LanguageRepository(BaseReferenceRepository):
    """Repository for language reference data."""
    
    def __init__(self):
        """Initialize language repository."""
        super().__init__(table_name="languages")
    
    async def get_by_code(self, code: str) -> Language:
        """Get language by code using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, iso639_1, iso639_2, name, native_name,
                status, writing_direction,
                created_at, updated_at
            FROM {table_name}
            WHERE code = $1
        """
        
        try:
            db = await self.get_connection()
            row = await db.fetchrow(query, code)
            if not row:
                raise NotFoundError(f"Language {code} not found")
            
            data = process_database_record(dict(row))
            return Language(**data)
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get language: {str(e)}")
    
    async def get_by_iso639_1(self, iso639_1: str) -> Language:
        """Get language by ISO 639-1 code using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, iso639_1, iso639_2, name, native_name,
                status, writing_direction,
                created_at, updated_at
            FROM {table_name}
            WHERE iso639_1 = $1
        """
        
        try:
            db = await self.get_connection()
            row = await db.fetchrow(query, iso639_1)
            if not row:
                raise NotFoundError(f"Language with ISO 639-1 code {iso639_1} not found")
            
            data = process_database_record(dict(row))
            return Language(**data)
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get language: {str(e)}")
    
    async def list(
        self,
        filters: Optional[LanguageFilter] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Language], int]:
        """List languages with filters using neo-commons BaseRepository."""
        # Build WHERE clause
        filter_dict = {}
        if filters:
            filter_data = filters.model_dump(exclude_unset=True, exclude={'search'})
            filter_dict.update(filter_data)
        
        where_clause, params = self._build_where_clause(filter_dict, [])
        
        # Add search filter if provided
        if filters and filters.search:
            search_clause = f"(code ILIKE ${len(params) + 1} OR name ILIKE ${len(params) + 2} OR native_name ILIKE ${len(params) + 3})"
            if where_clause != "1=1":
                where_clause += f" AND {search_clause}"
            else:
                where_clause = search_clause
            params.extend([f"%{filters.search}%", f"%{filters.search}%", f"%{filters.search}%"])
        
        # Count query
        table_name = self.get_full_table_name()
        count_query = f"""
            SELECT COUNT(*) FROM {table_name}
            WHERE {where_clause}
        """
        
        # Data query
        params.extend([limit, offset])
        data_query = f"""
            SELECT 
                code, iso639_1, iso639_2, name, native_name,
                status, writing_direction,
                created_at, updated_at
            FROM {table_name}
            WHERE {where_clause}
            ORDER BY name ASC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """
        
        try:
            db = await self.get_connection()
            # Execute both queries
            count_params = params[:-2] if params else []
            total_count = await db.fetchval(count_query, *count_params)
            rows = await db.fetch(data_query, *params)
            
            languages = []
            for row in rows:
                data = process_database_record(dict(row))
                languages.append(Language(**data))
            
            return languages, total_count
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to list languages: {str(e)}")
    
    async def get_active_languages(self) -> List[Language]:
        """Get all active languages using neo-commons BaseRepository."""
        table_name = self.get_full_table_name()
        query = f"""
            SELECT 
                code, iso639_1, iso639_2, name, native_name,
                status, writing_direction,
                created_at, updated_at
            FROM {table_name}
            WHERE status = 'active'
            ORDER BY name ASC
        """
        
        try:
            db = await self.get_connection()
            rows = await db.fetch(query)
            languages = []
            for row in rows:
                data = process_database_record(dict(row))
                languages.append(Language(**data))
            
            return languages
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get active languages: {str(e)}")