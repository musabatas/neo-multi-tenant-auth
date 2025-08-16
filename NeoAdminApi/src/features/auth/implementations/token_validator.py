"""
TokenValidator implementation for NeoAdminApi.

Protocol-compliant wrapper around existing TokenManager for neo-commons integration.
"""
from typing import Dict, Any, Optional
from loguru import logger

from neo_commons.auth.protocols import TokenValidatorProtocol, ValidationStrategy
from neo_commons.auth import create_auth_service


class NeoAdminTokenValidator:
    """
    TokenValidator implementation for NeoAdminApi.
    
    Wraps the existing TokenManager to provide protocol compliance.
    """
    
    def __init__(self):
        """Initialize token validator."""
        self.auth_service = create_auth_service()
        # Import here to avoid circular dependency
        from ..repositories.auth_repository import AuthRepository
        self.auth_repo = AuthRepository()
    
    async def validate_token(
        self,
        token: str,
        realm: str,
        strategy: ValidationStrategy = ValidationStrategy.LOCAL,
        critical: bool = False
    ) -> Dict[str, Any]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token to validate
            realm: Keycloak realm
            strategy: Validation strategy (LOCAL, INTROSPECTION, DUAL)
            critical: Whether this is critical operation (forces introspection)
            
        Returns:
            Dictionary with claims and metadata
            
        Raises:
            UnauthorizedError: Invalid or expired token
        """
        try:
            # Use strategy parameter directly if it's already ValidationStrategy enum
            validation_strategy = strategy
            if isinstance(strategy, str):
                # Convert string strategy to enum for backward compatibility
                if strategy == "LOCAL":
                    validation_strategy = ValidationStrategy.LOCAL
                elif strategy == "INTROSPECTION":
                    validation_strategy = ValidationStrategy.INTROSPECTION
                else:
                    validation_strategy = ValidationStrategy.DUAL
            
            # Validate using existing token manager
            claims = await self.auth_service.token_validator.validate_token(
                token=token,
                realm=realm,
                strategy=validation_strategy,
                critical=critical
            )
            
            # Extract standard fields
            keycloak_user_id = claims.get("sub", "")
            username = claims.get("preferred_username", "")
            email = claims.get("email", "")
            
            logger.debug(f"Token validation: Keycloak user ID = {keycloak_user_id}")
            
            # Map Keycloak user ID to platform user ID
            platform_user_id = keycloak_user_id  # Default fallback
            try:
                # Try to find platform user by external_user_id
                platform_user = await self.auth_repo.get_user_by_external_id(
                    provider="keycloak",
                    external_id=keycloak_user_id
                )
                if platform_user:
                    platform_user_id = platform_user['id']
                    logger.debug(f"Mapped to platform user ID: {platform_user_id}")
                else:
                    logger.warning(f"Platform user not found for Keycloak ID: {keycloak_user_id}")
            except Exception as e:
                logger.warning(f"Failed to map Keycloak user ID to platform user ID: {e}")
            
            # Extract expiration
            expires_at = claims.get("exp")
            
            # Extract realm and client info
            issuer_realm = claims.get("iss", "").split("/")[-1] if claims.get("iss") else realm
            client_id = claims.get("azp", claims.get("aud", ""))
            
            # Extract roles and permissions
            realm_roles = []
            realm_access = claims.get("realm_access", {})
            if "roles" in realm_access:
                realm_roles = realm_access["roles"]
            
            client_roles = []
            resource_access = claims.get("resource_access", {})
            if client_id and client_id in resource_access:
                client_access = resource_access[client_id]
                client_roles = client_access.get("roles", [])
            
            # Combine all roles as permissions for compatibility
            permissions = list(set(realm_roles + client_roles))
            
            # Extract scopes
            scopes = claims.get("scope", "").split() if claims.get("scope") else []
            
            # Return dictionary that matches the protocol
            return {
                "user_id": platform_user_id,  # Use platform user ID for permissions
                "keycloak_user_id": keycloak_user_id,  # Keep original for reference
                "username": username,
                "email": email,
                "realm": issuer_realm,
                "client_id": client_id,
                "expires_at": expires_at,
                "permissions": permissions,
                "roles": realm_roles + client_roles,
                "scopes": scopes,
                "raw_claims": claims,
                # Standard JWT claims
                "sub": keycloak_user_id,  # Keep original Keycloak ID in sub
                "preferred_username": username,
                **claims  # Include all original claims
            }
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successful
        """
        try:
            await self.auth_service.revoke_token(token)
            return True
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    async def introspect_token(
        self,
        token: str,
        realm: str
    ) -> Dict[str, Any]:
        """
        Introspect token with Keycloak.
        
        Args:
            token: Token to introspect
            realm: Keycloak realm
            
        Returns:
            Introspection response
        """
        # Use token manager's introspection if available
        if hasattr(self.auth_service, 'introspect_token'):
            return await self.auth_service.introspect_token(token, realm)
        
        # Fallback to validation for basic info
        try:
            claims = await self.auth_service.validate_token(
                token=token,
                realm=realm,
                strategy=ValidationStrategy.INTROSPECTION,
                critical=True
            )
            return {
                "active": True,
                "sub": claims.get("sub"),
                "username": claims.get("preferred_username"),
                "email": claims.get("email"),
                "exp": claims.get("exp"),
                "iat": claims.get("iat"),
                "scope": claims.get("scope")
            }
        except Exception:
            return {"active": False}
    
    async def get_public_key(self, realm: str) -> Optional[str]:
        """
        Get public key for realm.
        
        Args:
            realm: Keycloak realm
            
        Returns:
            Public key if available
        """
        # Delegate to token manager if available
        if hasattr(self.auth_service, 'get_public_key'):
            return await self.auth_service.get_public_key(realm)
        
        logger.warning(f"Public key retrieval not available for realm {realm}")
        return None
    
    async def clear_user_tokens(self, user_id: str) -> None:
        """
        Clear cached tokens for user.
        
        Args:
            user_id: User ID to clear tokens for
        """
        try:
            await self.auth_service.clear_user_tokens(user_id)
        except Exception as e:
            logger.warning(f"Failed to clear user tokens for {user_id}: {e}")