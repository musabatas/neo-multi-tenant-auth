"""
API routes for reference data management.
"""

from typing import Optional, List, Dict
from fastapi import Depends, Query, HTTPException, status, Path
from src.common.routers.base import NeoAPIRouter

from src.common.models.base import APIResponse
from src.common.models import PaginationParams
from src.common.database.connection import get_database
from src.features.auth.dependencies import get_reference_data_access, get_guest_session_info
from ..models.request import CurrencyFilter, CountryFilter, LanguageFilter
from ..models.response import (
    CurrencyResponse, CountryResponse, LanguageResponse,
    CurrencyListResponse, CountryListResponse, LanguageListResponse
)
from ..services.reference_data_service import CurrencyService, CountryService, LanguageService
from ..repositories.reference_data_repository import CurrencyRepository, CountryRepository, LanguageRepository

router = NeoAPIRouter()

# Sub-routers for better organization  
currency_router = NeoAPIRouter(prefix="/currencies", tags=["Currencies"])
country_router = NeoAPIRouter(prefix="/countries", tags=["Countries"])
language_router = NeoAPIRouter(prefix="/languages", tags=["Languages"])


def get_currency_service() -> CurrencyService:
    """Dependency to get currency service."""
    repository = CurrencyRepository()
    return CurrencyService(repository)


def get_country_service() -> CountryService:
    """Dependency to get country service."""
    repository = CountryRepository()
    return CountryService(repository)


def get_language_service() -> LanguageService:
    """Dependency to get language service."""
    repository = LanguageRepository()
    return LanguageService(repository)


# ============================================================================
# CURRENCY ENDPOINTS
# ============================================================================

@currency_router.get(
    "",
    response_model=APIResponse[CurrencyListResponse],
    summary="List currencies",
    description="Get a paginated list of ISO 4217 currencies with filtering"
)
async def list_currencies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    is_cryptocurrency: Optional[bool] = Query(None, description="Filter by cryptocurrency"),
    is_legal_tender: Optional[bool] = Query(None, description="Filter by legal tender"),
    minor_unit: Optional[int] = Query(None, ge=0, le=6, description="Filter by decimal places"),
    search: Optional[str] = Query(None, description="Search in code or name"),
    service: CurrencyService = Depends(get_currency_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[CurrencyListResponse]:
    """
    List all ISO 4217 currencies with pagination and filtering.
    
    This endpoint provides:
    - Paginated list of currencies
    - Filtering by status, type, and characteristics
    - Search functionality in code and name
    """
    try:
        # Create filter object
        filters = CurrencyFilter(
            status=status,
            is_cryptocurrency=is_cryptocurrency,
            is_legal_tender=is_legal_tender,
            minor_unit=minor_unit,
            search=search
        )
        
        # Create pagination params
        pagination = PaginationParams(page=page, page_size=page_size)
        
        # Get currencies
        result = await service.list_currencies(
            filters=filters,
            pagination=pagination
        )
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result.items)} currencies"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@currency_router.get(
    "/active",
    response_model=APIResponse[List[CurrencyResponse]],
    summary="Get active currencies",
    description="Get all active currencies (no pagination)"
)
async def get_active_currencies(
    service: CurrencyService = Depends(get_currency_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[List[CurrencyResponse]]:
    """
    Get all active currencies without pagination.
    
    This is useful for dropdown lists and forms.
    """
    try:
        result = await service.get_active_currencies()
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result)} active currencies"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@currency_router.get(
    "/{code}",
    response_model=APIResponse[CurrencyResponse],
    summary="Get currency details",
    description="Get detailed information about a specific currency"
)
async def get_currency(
    code: str = Path(..., description="Currency code (ISO 4217)", min_length=3, max_length=3),
    service: CurrencyService = Depends(get_currency_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[CurrencyResponse]:
    """
    Get detailed information about a specific currency by ISO 4217 code.
    """
    try:
        result = await service.get_currency(code)
        
        return APIResponse.success_response(
            data=result,
            message="Currency retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# COUNTRY ENDPOINTS
# ============================================================================

@country_router.get(
    "",
    response_model=APIResponse[CountryListResponse],
    summary="List countries",
    description="Get a paginated list of ISO 3166 countries with filtering"
)
async def list_countries(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    continent: Optional[str] = Query(None, description="Filter by continent"),
    region: Optional[str] = Query(None, description="Filter by region"),
    gdpr_applicable: Optional[bool] = Query(None, description="Filter by GDPR applicability"),
    data_localization_required: Optional[bool] = Query(None, description="Filter by data localization"),
    default_currency_code: Optional[str] = Query(None, description="Filter by currency"),
    search: Optional[str] = Query(None, description="Search in code or name"),
    service: CountryService = Depends(get_country_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[CountryListResponse]:
    """
    List all ISO 3166 countries with pagination and filtering.
    
    This endpoint provides:
    - Paginated list of countries
    - Filtering by region, continent, compliance
    - Search functionality in code and name
    """
    try:
        # Create filter object
        filters = CountryFilter(
            status=status,
            continent=continent,
            region=region,
            gdpr_applicable=gdpr_applicable,
            data_localization_required=data_localization_required,
            default_currency_code=default_currency_code,
            search=search
        )
        
        # Create pagination params
        pagination = PaginationParams(page=page, page_size=page_size)
        
        # Get countries
        result = await service.list_countries(
            filters=filters,
            pagination=pagination
        )
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result.items)} countries"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@country_router.get(
    "/continent/{continent}",
    response_model=APIResponse[List[CountryResponse]],
    summary="Get countries by continent",
    description="Get all countries in a specific continent"
)
async def get_countries_by_continent(
    continent: str = Path(..., description="Continent name"),
    service: CountryService = Depends(get_country_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[List[CountryResponse]]:
    """
    Get all countries in a specific continent.
    
    This is useful for regional filtering and forms.
    """
    try:
        result = await service.get_countries_by_continent(continent)
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result)} countries in {continent}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@country_router.get(
    "/gdpr",
    response_model=APIResponse[List[CountryResponse]],
    summary="Get GDPR countries",
    description="Get all GDPR-applicable countries"
)
async def get_gdpr_countries(
    service: CountryService = Depends(get_country_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[List[CountryResponse]]:
    """
    Get all countries where GDPR is applicable.
    
    This is useful for compliance and data protection workflows.
    """
    try:
        result = await service.get_gdpr_countries()
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result)} GDPR-applicable countries"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@country_router.get(
    "/{code}",
    response_model=APIResponse[CountryResponse],
    summary="Get country details",
    description="Get detailed information about a specific country"
)
async def get_country(
    code: str = Path(..., description="Country code (ISO 3166-1 alpha-2)", min_length=2, max_length=2),
    service: CountryService = Depends(get_country_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[CountryResponse]:
    """
    Get detailed information about a specific country by ISO 3166-1 alpha-2 code.
    """
    try:
        result = await service.get_country(code)
        
        return APIResponse.success_response(
            data=result,
            message="Country retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@country_router.get(
    "/code3/{code3}",
    response_model=APIResponse[CountryResponse],
    summary="Get country by alpha-3 code",
    description="Get country details by ISO 3166-1 alpha-3 code"
)
async def get_country_by_code3(
    code3: str = Path(..., description="Country code (ISO 3166-1 alpha-3)", min_length=3, max_length=3),
    service: CountryService = Depends(get_country_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[CountryResponse]:
    """
    Get country information by ISO 3166-1 alpha-3 code.
    """
    try:
        result = await service.get_country_by_code3(code3)
        
        return APIResponse.success_response(
            data=result,
            message="Country retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# LANGUAGE ENDPOINTS
# ============================================================================

@language_router.get(
    "",
    response_model=APIResponse[LanguageListResponse],
    summary="List languages",
    description="Get a paginated list of ISO 639 languages with filtering"
)
async def list_languages(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    writing_direction: Optional[str] = Query(None, description="Filter by writing direction"),
    iso639_1: Optional[str] = Query(None, description="Filter by ISO 639-1 code"),
    search: Optional[str] = Query(None, description="Search in code or name"),
    service: LanguageService = Depends(get_language_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[LanguageListResponse]:
    """
    List all ISO 639 languages with pagination and filtering.
    
    This endpoint provides:
    - Paginated list of languages
    - Filtering by status and characteristics
    - Search functionality in code and name
    """
    try:
        # Create filter object
        filters = LanguageFilter(
            status=status,
            writing_direction=writing_direction,
            iso639_1=iso639_1,
            search=search
        )
        
        # Create pagination params
        pagination = PaginationParams(page=page, page_size=page_size)
        
        # Get languages
        result = await service.list_languages(
            filters=filters,
            pagination=pagination
        )
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result.items)} languages"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@language_router.get(
    "/active",
    response_model=APIResponse[List[LanguageResponse]],
    summary="Get active languages",
    description="Get all active languages (no pagination)"
)
async def get_active_languages(
    service: LanguageService = Depends(get_language_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[List[LanguageResponse]]:
    """
    Get all active languages without pagination.
    
    This is useful for dropdown lists and forms.
    """
    try:
        result = await service.get_active_languages()
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result)} active languages"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@language_router.get(
    "/{code}",
    response_model=APIResponse[LanguageResponse],
    summary="Get language details",
    description="Get detailed information about a specific language"
)
async def get_language(
    code: str = Path(..., description="Language code (ISO 639)", max_length=10),
    service: LanguageService = Depends(get_language_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[LanguageResponse]:
    """
    Get detailed information about a specific language by ISO 639 code.
    """
    try:
        result = await service.get_language(code)
        
        return APIResponse.success_response(
            data=result,
            message="Language retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@language_router.get(
    "/iso639-1/{iso639_1}",
    response_model=APIResponse[LanguageResponse],
    summary="Get language by ISO 639-1 code",
    description="Get language details by ISO 639-1 two-letter code"
)
async def get_language_by_iso639_1(
    iso639_1: str = Path(..., description="Language code (ISO 639-1)", min_length=2, max_length=2),
    service: LanguageService = Depends(get_language_service),
    current_user: dict = Depends(get_reference_data_access)
) -> APIResponse[LanguageResponse]:
    """
    Get language information by ISO 639-1 two-letter code.
    """
    try:
        result = await service.get_language_by_iso639_1(iso639_1)
        
        return APIResponse.success_response(
            data=result,
            message="Language retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# GUEST SESSION ENDPOINTS
# ============================================================================

@router.get(
    "/session",
    response_model=APIResponse[Dict],
    summary="Get session information",
    description="Get current session information (guest or authenticated)"
)
async def get_session_info(
    current_user: dict = Depends(get_reference_data_access),
    session_info: Optional[dict] = Depends(get_guest_session_info)
) -> APIResponse[Dict]:
    """
    Get information about the current session.
    
    Returns session details for both authenticated users and guests.
    Useful for debugging and monitoring session state.
    """
    try:
        response_data = {
            "user_type": current_user.get("user_type", "unknown"),
            "session_type": current_user.get("session_type", "unknown")
        }
        
        if current_user.get("user_type") == "guest":
            # Guest session information
            response_data.update({
                "session_id": current_user.get("session_id"),
                "permissions": current_user.get("permissions", []),
                "rate_limit": current_user.get("rate_limit", {}),
                "request_count": current_user.get("request_count", 0),
                "created_at": current_user.get("created_at"),
                "expires_at": current_user.get("expires_at")
            })
            
            # Include new session token if this is a new session
            if "new_session_token" in current_user:
                response_data["new_session_token"] = current_user["new_session_token"]
        else:
            # Authenticated user information
            response_data.update({
                "user_id": current_user.get("id"),
                "username": current_user.get("username"),
                "email": current_user.get("email"),
                "permissions": [p.get("code") for p in current_user.get("permissions", [])][:10]  # First 10
            })
        
        return APIResponse.success_response(
            data=response_data,
            message="Session information retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Include sub-routers
router.include_router(currency_router)
router.include_router(country_router)  
router.include_router(language_router)