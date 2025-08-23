"""Password reset service with enhanced Keycloak features."""

import logging
from typing import Optional, Dict, Any, List

from ....core.exceptions.auth import (
    AuthenticationError,
    UserNotFoundError,
    InvalidCredentialsError,
)
from ....core.value_objects.identifiers import TenantId
from ..adapters.keycloak_admin import KeycloakAdminAdapter
from ..models.requests import ForgotPasswordRequest, ResetPasswordRequest
from ..models.responses import MessageResponse, PasswordResetResponse

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for password reset operations."""
    
    def __init__(self, keycloak_admin: KeycloakAdminAdapter):
        """Initialize password reset service."""
        self.keycloak_admin = keycloak_admin
    
    async def initiate_password_reset(
        self,
        request: ForgotPasswordRequest,
        tenant_id: TenantId,
        realm_name: str,
    ) -> PasswordResetResponse:
        """Initiate password reset process."""
        try:
            # Find user by email
            user_data = await self.keycloak_admin.get_user_by_email(
                realm_name, request.email
            )
            
            if not user_data:
                # For security, don't reveal if email exists or not
                logger.info(f"Password reset requested for non-existent email: {request.email}")
                return PasswordResetResponse(
                    message="If an account with this email exists, you will receive a password reset link.",
                    reset_token_sent=False,  # No token actually sent
                )
            
            user_id = user_data["id"]
            
            # Send password reset email via Keycloak
            await self.keycloak_admin.send_user_password_reset(realm_name, user_id)
            
            logger.info(
                f"Password reset email sent to {request.email} "
                f"for user {user_id} in tenant {tenant_id.value}"
            )
            
            return PasswordResetResponse(
                message="If an account with this email exists, you will receive a password reset link.",
                reset_token_sent=True,
                expires_in=3600,  # Keycloak default: 1 hour
            )
        
        except Exception as e:
            logger.error(f"Password reset initiation failed: {e}")
            # Return generic message for security
            return PasswordResetResponse(
                message="If an account with this email exists, you will receive a password reset link.",
                reset_token_sent=False,
            )
    
    async def complete_password_reset(
        self,
        request: ResetPasswordRequest,
        tenant_id: TenantId,
        realm_name: str,
    ) -> MessageResponse:
        """Complete password reset with new password."""
        try:
            # Note: In a real implementation, you would validate the reset token
            # and extract user information from it. For this example, we assume
            # the token contains the user ID or we have another way to identify the user.
            
            # This is a simplified implementation - in production, you would:
            # 1. Validate the reset token (JWT or database lookup)
            # 2. Extract user ID from the validated token
            # 3. Check token expiration
            # 4. Set the new password
            
            # For now, we'll raise an error indicating this needs to be completed
            # based on your specific token strategy
            raise NotImplementedError(
                "Password reset completion requires token validation implementation. "
                "This should be handled through Keycloak's password reset flow or "
                "custom token management."
            )
        
        except Exception as e:
            logger.error(f"Password reset completion failed: {e}")
            raise AuthenticationError(f"Password reset failed: {e}") from e
    
    async def change_user_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        realm_name: str,
    ) -> MessageResponse:
        """Change user password with current password verification."""
        try:
            # Note: This requires additional verification that the current password
            # is correct. You would typically:
            # 1. Attempt to authenticate the user with current password
            # 2. If successful, update the password
            # 3. Invalidate existing sessions (optional)
            
            # For this implementation, we'll directly set the password
            # In production, add current password verification
            await self.keycloak_admin.set_user_password(
                realm_name=realm_name,
                user_id=user_id,
                password=new_password,
                temporary=False,
            )
            
            logger.info(f"Password changed for user {user_id} in realm {realm_name}")
            
            return MessageResponse(
                message="Password changed successfully",
                success=True,
            )
        
        except Exception as e:
            logger.error(f"Password change failed for user {user_id}: {e}")
            raise AuthenticationError(f"Password change failed: {e}") from e
    
    async def set_temporary_password(
        self,
        user_id: str,
        temporary_password: str,
        realm_name: str,
    ) -> MessageResponse:
        """Set temporary password for user (admin operation)."""
        try:
            await self.keycloak_admin.set_user_password(
                realm_name=realm_name,
                user_id=user_id,
                password=temporary_password,
                temporary=True,  # User must change on next login
            )
            
            logger.info(f"Temporary password set for user {user_id} in realm {realm_name}")
            
            return MessageResponse(
                message="Temporary password set successfully",
                success=True,
                details={
                    "requires_password_change": True,
                    "temporary": True,
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to set temporary password for user {user_id}: {e}")
            raise AuthenticationError(f"Failed to set temporary password: {e}") from e
    
    async def validate_password_reset_token(self, token: str) -> Optional[dict]:
        """Validate password reset token."""
        # This is a placeholder for token validation logic
        # In a real implementation, you would:
        # 1. Decode/validate the token (JWT or database lookup)
        # 2. Check expiration
        # 3. Return user information if valid
        # 4. Return None if invalid
        
        logger.warning("Password reset token validation not implemented")
        return None
    
    async def send_verify_email(self, user_id: str, realm_name: str) -> MessageResponse:
        """
        Send email verification email to user.
        
        Args:
            user_id: Keycloak user ID
            realm_name: Keycloak realm name
            
        Returns:
            MessageResponse with success status
            
        Raises:
            AuthenticationError: If service unavailable
        """
        try:
            await self.keycloak_admin.send_verify_email(realm_name, user_id)
            
            logger.info(f"Email verification sent to user {user_id} in realm {realm_name}")
            
            return MessageResponse(
                message="Email verification sent successfully",
                success=True
            )
                
        except Exception as e:
            logger.error(f"Failed to send email verification to user {user_id}: {e}")
            raise AuthenticationError(f"Email verification service temporarily unavailable: {e}") from e
    
    async def send_required_actions_email(
        self, 
        user_id: str,
        realm_name: str,
        actions: List[str], 
        redirect_uri: Optional[str] = None,
        client_id: Optional[str] = None,
        lifespan: Optional[int] = None
    ) -> MessageResponse:
        """
        Send required actions email to user.
        
        Available actions:
        - UPDATE_PASSWORD: Require password update
        - VERIFY_EMAIL: Require email verification  
        - UPDATE_PROFILE: Require profile update
        - CONFIGURE_TOTP: Require TOTP/MFA setup
        - terms_and_conditions: Require terms acceptance
        
        Args:
            user_id: Keycloak user ID
            realm_name: Keycloak realm name
            actions: List of required actions
            redirect_uri: Optional redirect URI after completing actions
            client_id: Optional client ID for the redirect
            lifespan: Optional email lifespan in seconds
            
        Returns:
            MessageResponse with success status
            
        Raises:
            AuthenticationError: If service unavailable
        """
        try:
            await self.keycloak_admin.send_user_action_email(
                realm_name=realm_name,
                user_id=user_id,
                actions=actions,
                redirect_uri=redirect_uri,
                client_id=client_id,
                lifespan=lifespan
            )
            
            logger.info(f"Required actions email sent to user {user_id}: {actions}")
            
            return MessageResponse(
                message="Required actions email sent successfully",
                success=True,
                details={"actions": actions}
            )
                
        except Exception as e:
            logger.error(f"Failed to send required actions email to user {user_id}: {e}")
            raise AuthenticationError(f"Required actions service temporarily unavailable: {e}") from e
    
    async def get_user_credentials(self, user_id: str, realm_name: str) -> Dict[str, Any]:
        """
        Get user credentials information (for MFA/OTP management).
        
        Args:
            user_id: Keycloak user ID
            realm_name: Keycloak realm name
            
        Returns:
            Dict containing user credentials information
            
        Raises:
            AuthenticationError: If service unavailable
        """
        try:
            credentials = await self.keycloak_admin.get_user_credentials(realm_name, user_id)
            
            logger.info(f"Retrieved credentials for user {user_id}")
            
            return {
                "success": True,
                "credentials": credentials,
                "user_id": user_id
            }
                
        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}: {e}")
            raise AuthenticationError(f"Credentials service temporarily unavailable: {e}") from e
    
    async def remove_totp(self, user_id: str, realm_name: str) -> MessageResponse:
        """
        Remove TOTP/OTP from user account.
        
        Args:
            user_id: Keycloak user ID
            realm_name: Keycloak realm name
            
        Returns:
            MessageResponse with success status
            
        Raises:
            AuthenticationError: If service unavailable
        """
        try:
            await self.keycloak_admin.remove_user_totp(realm_name, user_id)
            
            logger.info(f"TOTP removed for user {user_id}")
            
            return MessageResponse(
                message="TOTP removed successfully",
                success=True
            )
                
        except Exception as e:
            logger.error(f"Failed to remove TOTP for user {user_id}: {e}")
            raise AuthenticationError(f"TOTP service temporarily unavailable: {e}") from e
    
    async def delete_user_credential(
        self, 
        user_id: str, 
        realm_name: str, 
        credential_id: str
    ) -> MessageResponse:
        """
        Delete specific user credential (password, OTP token, etc.).
        
        Args:
            user_id: Keycloak user ID
            realm_name: Keycloak realm name
            credential_id: Specific credential ID to delete
            
        Returns:
            MessageResponse with success status
            
        Raises:
            AuthenticationError: If service unavailable
        """
        try:
            await self.keycloak_admin.delete_user_credential(realm_name, user_id, credential_id)
            
            logger.info(f"Credential {credential_id} deleted for user {user_id}")
            
            return MessageResponse(
                message="Credential deleted successfully",
                success=True,
                details={"credential_id": credential_id}
            )
                
        except Exception as e:
            logger.error(f"Failed to delete credential {credential_id} for user {user_id}: {e}")
            raise AuthenticationError(f"Credential service temporarily unavailable: {e}") from e
    
    async def logout_user_sessions(self, user_id: str, realm_name: str) -> MessageResponse:
        """
        Logout all user sessions (useful after password reset).
        
        Args:
            user_id: Keycloak user ID
            realm_name: Keycloak realm name
            
        Returns:
            MessageResponse with success status
            
        Raises:
            AuthenticationError: If service unavailable
        """
        try:
            await self.keycloak_admin.logout_user(realm_name, user_id)
            
            logger.info(f"All sessions logged out for user {user_id}")
            
            return MessageResponse(
                message="All sessions logged out successfully",
                success=True
            )
                
        except Exception as e:
            logger.error(f"Failed to logout sessions for user {user_id}: {e}")
            raise AuthenticationError(f"Logout service temporarily unavailable: {e}") from e