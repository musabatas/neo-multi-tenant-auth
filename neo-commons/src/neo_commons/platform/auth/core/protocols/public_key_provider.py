"""Public key provider protocol contract."""

from typing import Protocol, runtime_checkable, Optional, List
from ..value_objects import PublicKey, RealmIdentifier


@runtime_checkable
class PublicKeyProvider(Protocol):
    """Protocol for public key retrieval operations.
    
    Defines ONLY the contract for public key management.
    Implementations handle specific key sources (JWKS, file, database, etc.).
    """
    
    async def get_public_key(
        self, 
        realm: RealmIdentifier,
        key_id: Optional[str] = None
    ) -> PublicKey:
        """Get public key for token validation.
        
        Args:
            realm: Realm identifier for key lookup
            key_id: Specific key ID to retrieve (if supported)
            
        Returns:
            Public key for signature validation
            
        Raises:
            PublicKeyError: If key cannot be retrieved
            RealmNotFound: If realm is not configured
        """
        ...
    
    async def get_all_public_keys(self, realm: RealmIdentifier) -> List[PublicKey]:
        """Get all available public keys for a realm.
        
        Args:
            realm: Realm identifier for key lookup
            
        Returns:
            List of available public keys
            
        Raises:
            PublicKeyError: If keys cannot be retrieved
            RealmNotFound: If realm is not configured
        """
        ...
    
    async def refresh_keys(self, realm: RealmIdentifier) -> None:
        """Refresh cached public keys for a realm.
        
        Args:
            realm: Realm identifier to refresh
            
        Raises:
            PublicKeyError: If keys cannot be refreshed
            RealmNotFound: If realm is not configured
        """
        ...
    
    async def is_key_available(
        self, 
        realm: RealmIdentifier,
        key_id: str
    ) -> bool:
        """Check if a specific key is available.
        
        Args:
            realm: Realm identifier
            key_id: Key identifier to check
            
        Returns:
            True if key is available, False otherwise
        """
        ...