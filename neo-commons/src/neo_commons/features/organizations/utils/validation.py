"""Organization validation utilities.

This module provides centralized validation logic for organization data
that can be reused across different layers (Pydantic, entity validation, etc.).
"""

import re
from typing import Optional


class OrganizationValidationRules:
    """Centralized validation rules for organization data."""
    
    # Regex patterns
    SLUG_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    DOMAIN_PATTERN = re.compile(r'^[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,}$')
    
    # Length constraints
    NAME_MIN_LENGTH = 2
    NAME_MAX_LENGTH = 100
    DISPLAY_NAME_MIN_LENGTH = 2
    DISPLAY_NAME_MAX_LENGTH = 200
    DESCRIPTION_MAX_LENGTH = 1000
    SLUG_MIN_LENGTH = 4
    SLUG_MAX_LENGTH = 60
    
    @staticmethod
    def validate_name(name: str) -> str:
        """Validate and normalize organization name (identifier/slug).
        
        Args:
            name: Raw organization name
            
        Returns:
            Normalized name (lowercase, validated)
            
        Raises:
            ValueError: If name is invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")
        
        # Normalize
        normalized = name.strip().lower()
        
        # Length validation
        if len(normalized) < OrganizationValidationRules.NAME_MIN_LENGTH:
            raise ValueError(f"Name must be at least {OrganizationValidationRules.NAME_MIN_LENGTH} characters")
        if len(normalized) > OrganizationValidationRules.NAME_MAX_LENGTH:
            raise ValueError(f"Name must be at most {OrganizationValidationRules.NAME_MAX_LENGTH} characters")
        
        # Format validation (alphanumeric, hyphens, underscores)
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Name must contain only alphanumeric characters, hyphens, and underscores")
        
        return normalized
    
    @staticmethod
    def validate_slug(slug: str) -> str:
        """Validate organization slug format.
        
        Args:
            slug: Organization slug
            
        Returns:
            Validated slug
            
        Raises:
            ValueError: If slug is invalid
        """
        if not slug or not isinstance(slug, str):
            raise ValueError("Slug must be a non-empty string")
        
        # Length validation
        if not (OrganizationValidationRules.SLUG_MIN_LENGTH <= len(slug) <= OrganizationValidationRules.SLUG_MAX_LENGTH):
            raise ValueError(f"Slug length must be {OrganizationValidationRules.SLUG_MIN_LENGTH}-{OrganizationValidationRules.SLUG_MAX_LENGTH} characters")
        
        # Format validation
        if not OrganizationValidationRules.SLUG_PATTERN.match(slug):
            raise ValueError("Slug must start and end with alphanumeric, contain only lowercase letters, numbers, and hyphens")
        
        return slug
    
    @staticmethod
    def validate_display_name(display_name: str) -> str:
        """Validate organization display name.
        
        Args:
            display_name: Human-readable display name
            
        Returns:
            Validated display name
            
        Raises:
            ValueError: If display name is invalid
        """
        if not display_name or not isinstance(display_name, str):
            raise ValueError("Display name must be a non-empty string")
        
        normalized = display_name.strip()
        
        # Length validation
        if len(normalized) < OrganizationValidationRules.DISPLAY_NAME_MIN_LENGTH:
            raise ValueError(f"Display name must be at least {OrganizationValidationRules.DISPLAY_NAME_MIN_LENGTH} characters")
        if len(normalized) > OrganizationValidationRules.DISPLAY_NAME_MAX_LENGTH:
            raise ValueError(f"Display name must be at most {OrganizationValidationRules.DISPLAY_NAME_MAX_LENGTH} characters")
        
        return normalized
    
    @staticmethod
    def validate_description(description: Optional[str]) -> Optional[str]:
        """Validate organization description.
        
        Args:
            description: Optional description
            
        Returns:
            Validated description or None
            
        Raises:
            ValueError: If description is invalid
        """
        if description is None:
            return None
        
        if not isinstance(description, str):
            raise ValueError("Description must be a string")
        
        normalized = description.strip()
        if not normalized:
            return None
        
        # Length validation
        if len(normalized) > OrganizationValidationRules.DESCRIPTION_MAX_LENGTH:
            raise ValueError(f"Description must be at most {OrganizationValidationRules.DESCRIPTION_MAX_LENGTH} characters")
        
        return normalized
    
    @staticmethod
    def validate_domain(domain: Optional[str]) -> Optional[str]:
        """Validate domain name.
        
        Args:
            domain: Optional domain name
            
        Returns:
            Normalized domain or None
            
        Raises:
            ValueError: If domain is invalid
        """
        if domain is None:
            return None
        
        if not isinstance(domain, str):
            raise ValueError("Domain must be a string")
        
        normalized = domain.strip().lower()
        if not normalized:
            return None
        
        # Basic domain format validation
        if "." not in normalized:
            raise ValueError("Domain must contain at least one dot")
        
        # More strict domain validation (optional)
        if not OrganizationValidationRules.DOMAIN_PATTERN.match(normalized):
            raise ValueError("Invalid domain format")
        
        return normalized
    
    @staticmethod
    def name_to_slug(name: str) -> str:
        """Convert organization name to slug format.
        
        Args:
            name: Organization name
            
        Returns:
            Slug formatted name
        """
        # Validate name first
        validated_name = OrganizationValidationRules.validate_name(name)
        
        # Convert underscores to hyphens for slug
        slug = validated_name.replace("_", "-")
        
        # Validate as slug
        return OrganizationValidationRules.validate_slug(slug)