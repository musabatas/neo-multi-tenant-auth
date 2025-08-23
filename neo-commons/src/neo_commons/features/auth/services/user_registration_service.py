"""User registration service."""

import logging
from typing import Dict

from ....core.exceptions.auth import (
    AuthenticationError,
    RealmConfigurationError,
    UserAlreadyExistsError,
)
from ....core.value_objects.identifiers import KeycloakUserId, TenantId, UserId
from ....utils.uuid import generate_uuid7
from ..adapters.keycloak_admin import KeycloakAdminAdapter
from ..entities.protocols import UserMapperProtocol
from ..models.requests import RegisterRequest
from ..models.responses import RegisterResponse

logger = logging.getLogger(__name__)


class UserRegistrationService:
    """Service for user registration operations."""
    
    def __init__(
        self,
        keycloak_admin: KeycloakAdminAdapter,
        user_mapper: UserMapperProtocol,
    ):
        """Initialize user registration service."""
        self.keycloak_admin = keycloak_admin
        self.user_mapper = user_mapper
    
    async def register_user(
        self,
        registration_data: RegisterRequest,
        tenant_id: TenantId,
        realm_name: str,
    ) -> RegisterResponse:
        """Register a new user."""
        try:
            # Check if user already exists
            await self._validate_user_availability(
                registration_data.email,
                registration_data.username,
                realm_name,
            )
            
            # Generate platform user ID
            platform_user_id = UserId(generate_uuid7())
            
            # Create user in Keycloak
            keycloak_user_data = self._prepare_keycloak_user_data(
                registration_data, platform_user_id
            )
            
            keycloak_user_id = await self.keycloak_admin.create_user(
                realm_name, keycloak_user_data
            )
            
            # Create user mapping between Keycloak and platform
            await self.user_mapper.create_user_mapping(
                keycloak_user_id=KeycloakUserId(keycloak_user_id),
                platform_user_id=platform_user_id,
                tenant_id=tenant_id,
                email=registration_data.email,
                username=registration_data.username,
                first_name=registration_data.first_name,
                last_name=registration_data.last_name,
            )
            
            # Send email verification if required
            email_verification_required = True
            try:
                await self.keycloak_admin.send_user_email_verification(
                    realm_name, keycloak_user_id
                )
                logger.info(f"Email verification sent to user {registration_data.email}")
            except Exception as e:
                logger.warning(f"Failed to send email verification: {e}")
                # Don't fail registration if email verification fails
                email_verification_required = False
            
            logger.info(
                f"Successfully registered user {registration_data.username} "
                f"in tenant {tenant_id.value}"
            )
            
            return RegisterResponse(
                user_id=platform_user_id.value,
                keycloak_user_id=keycloak_user_id,
                email=registration_data.email,
                username=registration_data.username,
                email_verification_required=email_verification_required,
                message="Registration successful. Please check your email for verification.",
            )
        
        except UserAlreadyExistsError:
            raise
        
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            raise AuthenticationError(f"Registration failed: {e}") from e
    
    async def _validate_user_availability(
        self,
        email: str,
        username: str,
        realm_name: str,
    ) -> None:
        """Validate that email and username are available."""
        # Check email availability
        existing_user_by_email = await self.keycloak_admin.get_user_by_email(
            realm_name, email
        )
        if existing_user_by_email:
            raise UserAlreadyExistsError(f"User with email {email} already exists")
        
        # Check username availability
        existing_user_by_username = await self.keycloak_admin.get_user_by_username(
            realm_name, username
        )
        if existing_user_by_username:
            raise UserAlreadyExistsError(f"Username {username} is already taken")
    
    def _prepare_keycloak_user_data(
        self,
        registration_data: RegisterRequest,
        platform_user_id: UserId,
    ) -> Dict:
        """Prepare user data for Keycloak creation."""
        return {
            "username": registration_data.username,
            "email": registration_data.email,
            "firstName": registration_data.first_name,
            "lastName": registration_data.last_name,
            "enabled": True,
            "emailVerified": False,  # Will be verified via email
            "credentials": [
                {
                    "type": "password",
                    "value": registration_data.password,
                    "temporary": False,
                }
            ],
            "attributes": {
                "platform_user_id": platform_user_id.value,
                "registration_source": "api",
            },
        }
    
    async def validate_username_availability(
        self, username: str, realm_name: str
    ) -> bool:
        """Check if username is available."""
        try:
            existing_user = await self.keycloak_admin.get_user_by_username(
                realm_name, username
            )
            return existing_user is None
        except Exception as e:
            logger.error(f"Failed to check username availability: {e}")
            return False
    
    async def validate_email_availability(
        self, email: str, realm_name: str
    ) -> bool:
        """Check if email is available."""
        try:
            existing_user = await self.keycloak_admin.get_user_by_email(
                realm_name, email
            )
            return existing_user is None
        except Exception as e:
            logger.error(f"Failed to check email availability: {e}")
            return False
    
    async def resend_email_verification(
        self, user_id: str, realm_name: str
    ) -> bool:
        """Resend email verification."""
        try:
            await self.keycloak_admin.send_user_email_verification(
                realm_name, user_id
            )
            logger.info(f"Resent email verification to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resend email verification: {e}")
            return False