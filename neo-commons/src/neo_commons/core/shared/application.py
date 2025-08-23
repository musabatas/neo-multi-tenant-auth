"""Application protocols for neo-commons.

This module defines protocols for application-level contracts and interfaces.
"""

from typing import Any, Dict, Optional, Protocol, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class ConfigurationProtocol(Protocol):
    """Protocol for configuration management."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        ...
    
    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section."""
        ...


@runtime_checkable
class EventPublisherProtocol(Protocol):
    """Protocol for event publishing."""
    
    @abstractmethod
    async def publish(
        self, 
        event_type: str, 
        data: Dict[str, Any], 
        tenant_id: Optional[str] = None
    ) -> None:
        """Publish event."""
        ...


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """Protocol for event handling."""
    
    @abstractmethod
    async def handle(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle event."""
        ...


@runtime_checkable
class ValidationProtocol(Protocol):
    """Protocol for input validation."""
    
    @abstractmethod
    def validate(self, data: Any, schema: Any) -> Dict[str, Any]:
        """Validate data against schema."""
        ...
    
    @abstractmethod
    def sanitize(self, data: str) -> str:
        """Sanitize input data."""
        ...


@runtime_checkable
class EncryptionProtocol(Protocol):
    """Protocol for encryption/decryption operations."""
    
    @abstractmethod
    async def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext."""
        ...
    
    @abstractmethod
    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext."""
        ...
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash password."""
        ...
    
    @abstractmethod
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        ...