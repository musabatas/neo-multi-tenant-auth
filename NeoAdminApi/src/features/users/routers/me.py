"""
Current user (me) endpoints for self-profile management.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.common.routers.base import NeoAPIRouter
from src.common.models.base import APIResponse
from src.common.exceptions.base import NotFoundError, ValidationError, UnauthorizedError
from src.features.auth.dependencies import security
from src.features.auth.models.response import UserProfile, KeycloakUserData
from src.features.auth.services.auth_service import AuthService
from loguru import logger

from ..models.request import PlatformUserUpdate, UserPreferencesUpdate
from ..models.response import PlatformUserResponse
from ..services.user_service import PlatformUserService

router = NeoAPIRouter()


@router.get(
    "/",
    response_model=APIResponse[UserProfile],
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Get complete profile of the currently authenticated user (same as /auth/me)"
)
async def get_my_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[UserProfile]:
    """
    Get current user information from token.
    
    This endpoint is identical to /auth/me and returns the exact same response.
    Both endpoints use the centralized UserDataService for consistency.
    """
    auth_service = AuthService()
    
    # Extract access token
    access_token = credentials.credentials
    
    try:
        # Get user info (this uses centralized UserDataService)
        user_info = await auth_service.get_current_user(
            access_token=access_token,
            use_cache=True
        )
        
        # Prepare Keycloak data (same as /auth/me)
        keycloak_data = None
        if "keycloak" in user_info:
            keycloak_raw = user_info["keycloak"]
            keycloak_data = KeycloakUserData(
                session_id=keycloak_raw.get("session_id"),
                realm=keycloak_raw.get("realm"),
                email_verified=keycloak_raw.get("email_verified", False),
                scopes=keycloak_raw.get("scopes", []),
                realm_roles=keycloak_raw.get("realm_roles", []),
                client_roles=keycloak_raw.get("client_roles", {}),
                authorized_party=keycloak_raw.get("authorized_party"),
                auth_context_class=keycloak_raw.get("auth_context_class"),
                full_name=keycloak_raw.get("full_name")
            )
        
        # Map to UserProfile model (exactly like /auth/me)
        user_profile = UserProfile(
            id=user_info["id"],
            email=user_info["email"],
            username=user_info["username"],
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            display_name=user_info.get("display_name"),
            full_name=user_info.get("full_name"),
            avatar_url=user_info.get("avatar_url"),
            phone=user_info.get("phone"),
            job_title=user_info.get("job_title"),
            company=user_info.get("company"),
            departments=user_info.get("departments", []),
            timezone=user_info.get("timezone", "UTC"),
            locale=user_info.get("locale", "en-US"),
            language=user_info.get("language", "en"),
            notification_preferences=user_info.get("notification_preferences", {}),
            ui_preferences=user_info.get("ui_preferences", {}),
            is_onboarding_completed=user_info.get("is_onboarding_completed", False),
            profile_completion_percentage=user_info.get("profile_completion_percentage", 0),
            is_active=user_info.get("is_active", True),
            is_superadmin=user_info.get("is_superadmin", False),
            roles=user_info.get("roles", []),
            permissions=user_info.get("permissions", []),
            tenants=user_info.get("tenants", []),
            last_login_at=user_info.get("last_login_at"),
            created_at=user_info.get("created_at"),
            updated_at=user_info.get("updated_at"),
            external_auth_provider=user_info.get("external_auth_provider"),
            external_user_id=user_info.get("external_user_id"),
            keycloak=keycloak_data
        )
        
        return APIResponse.success_response(
            message="User retrieved successfully",
            data=user_profile
        )
        
    except UnauthorizedError as e:
        logger.warning(f"Get current user failed: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise UnauthorizedError("Failed to get user information")


@router.put(
    "/",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Update profile of the currently authenticated user"
)
async def update_my_profile(
    update_data: PlatformUserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[PlatformUserResponse]:
    """
    Update current user's profile.
    
    Automatically recalculates profile completion percentage after update.
    """
    service = PlatformUserService()
    
    try:
        # Get user from token
        from src.features.auth.services.auth_service import AuthService
        auth_service = AuthService()
        
        user_info = await auth_service.get_current_user(
            access_token=credentials.credentials,
            use_cache=False  # Don't use cache for write operations
        )
        
        # Update user profile
        user = await service.update_user_with_completion(
            user_id=user_info["id"],
            update_data=update_data
        )
        
        # Invalidate auth cache to reflect changes
        await auth_service.invalidate_user_cache(user_info["id"])
        
        return APIResponse.success_response(
            data=user,
            message="Profile updated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,  # HTTP_404_NOT_FOUND
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=400,  # HTTP_400_BAD_REQUEST
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,  # HTTP_500_INTERNAL_SERVER_ERROR
            detail="Failed to update profile"
        )


@router.put(
    "/preferences",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update current user preferences",
    description="Update preferences (timezone, locale, notifications, UI) for current user"
)
async def update_my_preferences(
    preferences_update: UserPreferencesUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[PlatformUserResponse]:
    """
    Update current user's preferences.
    """
    service = PlatformUserService()
    
    try:
        # Get user from token
        from src.features.auth.services.auth_service import AuthService
        auth_service = AuthService()
        
        user_info = await auth_service.get_current_user(
            access_token=credentials.credentials,
            use_cache=False
        )
        
        # Update preferences
        user = await service.update_user_preferences(
            user_id=user_info["id"],
            preferences_update=preferences_update
        )
        
        # Invalidate auth cache
        await auth_service.invalidate_user_cache(user_info["id"])
        
        return APIResponse.success_response(
            data=user,
            message="Preferences updated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,  # HTTP_404_NOT_FOUND
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,  # HTTP_500_INTERNAL_SERVER_ERROR
            detail="Failed to update preferences"
        )


@router.post(
    "/onboarding/complete",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Complete user onboarding",
    description="Mark user onboarding as complete"
)
async def complete_onboarding(
    completed_steps: Optional[Dict[str, bool]] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[PlatformUserResponse]:
    """
    Mark user onboarding as complete.
    
    Optionally provide completed steps for tracking.
    """
    service = PlatformUserService()
    
    try:
        # Get user from token
        from src.features.auth.services.auth_service import AuthService
        auth_service = AuthService()
        
        user_info = await auth_service.get_current_user(
            access_token=credentials.credentials,
            use_cache=False
        )
        
        # Complete onboarding
        user = await service.complete_user_onboarding(
            user_id=user_info["id"],
            completed_steps=completed_steps
        )
        
        # Invalidate auth cache
        await auth_service.invalidate_user_cache(user_info["id"])
        
        return APIResponse.success_response(
            data=user,
            message="Onboarding completed successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,  # HTTP_404_NOT_FOUND
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,  # HTTP_500_INTERNAL_SERVER_ERROR
            detail="Failed to complete onboarding"
        )


@router.get(
    "/onboarding/status",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get onboarding status",
    description="Get detailed onboarding status for current user"
)
async def get_onboarding_status(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[Dict[str, Any]]:
    """
    Get detailed onboarding status including completion percentage
    and next recommended steps.
    """
    try:
        # Use centralized UserDataService
        from src.features.users.services.user_data_service import UserDataService
        from src.features.auth.services.auth_service import AuthService
        
        auth_service = AuthService()
        user_data_service = UserDataService()
        
        # First get the basic user info to get the user ID
        user_info = await auth_service.get_current_user(
            access_token=credentials.credentials,
            use_cache=True
        )
        
        # Now get the onboarding status using the centralized service
        onboarding_steps = await user_data_service._get_onboarding_steps(
            user_info["id"], 
            user_info
        )
        
        status = {
            "is_onboarding_completed": user_info.get("is_onboarding_completed", False),
            "profile_completion_percentage": user_info.get("profile_completion_percentage", 0),
            "onboarding_steps": onboarding_steps,
            "next_steps": []
        }
        
        # Add recommendations for next steps
        if not status["is_onboarding_completed"]:
            for step_name, is_complete in onboarding_steps.items():
                if not is_complete:
                    status["next_steps"].append(step_name)
        
        return APIResponse.success_response(
            data=status,
            message="Onboarding status retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,  # HTTP_404_NOT_FOUND
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error in get_onboarding_status", exc_info=True)
        raise HTTPException(
            status_code=500,  # HTTP_500_INTERNAL_SERVER_ERROR
            detail="Failed to retrieve onboarding status"
        )