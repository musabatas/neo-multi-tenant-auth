"""Tenant validation rules and utilities.

Centralized validation logic for tenant-related operations without
duplicating validation patterns from other neo-commons features.
"""

import re
from typing import List, Optional


class TenantValidationRules:
    """Centralized tenant validation rules.
    
    Provides consistent validation logic for tenant operations
    without duplicating patterns from other features.
    """
    
    # Regex patterns
    SLUG_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    SCHEMA_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    DOMAIN_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')
    
    # Length constraints
    MIN_SLUG_LENGTH = 4
    MAX_SLUG_LENGTH = 54
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 500
    MAX_SCHEMA_NAME_LENGTH = 63
    
    # Reserved slugs (cannot be used for tenant slugs)
    RESERVED_SLUGS = {
        'admin', 'api', 'app', 'www', 'mail', 'ftp', 'test', 'dev',
        'staging', 'prod', 'production', 'platform', 'system', 'root',
        'tenant', 'organization', 'org', 'public', 'private', 'shared'
    }
    
    @classmethod
    def validate_slug(cls, slug: str) -> None:
        """Validate tenant slug format and constraints.
        
        Args:
            slug: Tenant slug to validate
            
        Raises:
            ValueError: If slug is invalid
        """
        if not slug:
            raise ValueError("Slug cannot be empty")
        
        if len(slug) < cls.MIN_SLUG_LENGTH or len(slug) > cls.MAX_SLUG_LENGTH:
            raise ValueError(f"Slug length must be between {cls.MIN_SLUG_LENGTH}-{cls.MAX_SLUG_LENGTH} characters")
        
        if not cls.SLUG_PATTERN.match(slug):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens, and cannot start or end with a hyphen")
        
        if slug in cls.RESERVED_SLUGS:
            raise ValueError(f"Slug '{slug}' is reserved and cannot be used")
        
        # Additional checks for consecutive hyphens
        if '--' in slug:
            raise ValueError("Slug cannot contain consecutive hyphens")
    
    @classmethod
    def validate_name(cls, name: str) -> None:
        """Validate tenant display name.
        
        Args:
            name: Tenant name to validate
            
        Raises:
            ValueError: If name is invalid
        """
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")
        
        name = name.strip()
        
        if len(name) < cls.MIN_NAME_LENGTH or len(name) > cls.MAX_NAME_LENGTH:
            raise ValueError(f"Name length must be between {cls.MIN_NAME_LENGTH}-{cls.MAX_NAME_LENGTH} characters")
        
        # Check for only whitespace or special characters
        if not re.search(r'[a-zA-Z0-9]', name):
            raise ValueError("Name must contain at least one alphanumeric character")
    
    @classmethod
    def validate_description(cls, description: Optional[str]) -> None:
        """Validate tenant description.
        
        Args:
            description: Tenant description to validate
            
        Raises:
            ValueError: If description is invalid
        """
        if description is not None:
            if len(description) > cls.MAX_DESCRIPTION_LENGTH:
                raise ValueError(f"Description cannot exceed {cls.MAX_DESCRIPTION_LENGTH} characters")
    
    @classmethod
    def validate_schema_name(cls, schema_name: str) -> None:
        """Validate database schema name.
        
        Args:
            schema_name: Schema name to validate
            
        Raises:
            ValueError: If schema name is invalid
        """
        if not schema_name:
            raise ValueError("Schema name cannot be empty")
        
        if len(schema_name) > cls.MAX_SCHEMA_NAME_LENGTH:
            raise ValueError(f"Schema name cannot exceed {cls.MAX_SCHEMA_NAME_LENGTH} characters")
        
        if not cls.SCHEMA_NAME_PATTERN.match(schema_name):
            raise ValueError("Schema name must start with a letter and contain only lowercase letters, numbers, and underscores")
        
        # PostgreSQL reserved words check (basic set)
        reserved_words = {
            'user', 'table', 'index', 'where', 'select', 'insert', 'update', 'delete',
            'create', 'drop', 'alter', 'grant', 'revoke', 'commit', 'rollback'
        }
        
        if schema_name.lower() in reserved_words:
            raise ValueError(f"Schema name '{schema_name}' is a reserved word")
    
    @classmethod
    def validate_custom_domain(cls, domain: Optional[str]) -> None:
        """Validate custom domain format.
        
        Args:
            domain: Custom domain to validate
            
        Raises:
            ValueError: If domain is invalid
        """
        if domain is not None:
            if not domain.strip():
                raise ValueError("Custom domain cannot be empty if provided")
            
            domain = domain.strip().lower()
            
            if not cls.DOMAIN_PATTERN.match(domain):
                raise ValueError("Invalid domain format")
            
            if len(domain) > 253:
                raise ValueError("Domain name too long (max 253 characters)")
    
    @classmethod
    def generate_schema_name(cls, slug: str) -> str:
        """Generate a valid schema name from tenant slug.
        
        Args:
            slug: Tenant slug
            
        Returns:
            Valid PostgreSQL schema name
        """
        # Replace hyphens with underscores for PostgreSQL compatibility
        schema_name = f"tenant_{slug.replace('-', '_')}"
        
        # Validate the generated name
        cls.validate_schema_name(schema_name)
        
        return schema_name
    
    @classmethod
    def validate_all(cls, slug: str, name: str, description: Optional[str] = None, 
                    schema_name: Optional[str] = None, custom_domain: Optional[str] = None) -> List[str]:
        """Validate all tenant fields and return list of errors.
        
        Args:
            slug: Tenant slug
            name: Tenant name
            description: Optional description
            schema_name: Optional schema name
            custom_domain: Optional custom domain
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            cls.validate_slug(slug)
        except ValueError as e:
            errors.append(f"Slug: {e}")
        
        try:
            cls.validate_name(name)
        except ValueError as e:
            errors.append(f"Name: {e}")
        
        try:
            cls.validate_description(description)
        except ValueError as e:
            errors.append(f"Description: {e}")
        
        if schema_name:
            try:
                cls.validate_schema_name(schema_name)
            except ValueError as e:
                errors.append(f"Schema name: {e}")
        
        try:
            cls.validate_custom_domain(custom_domain)
        except ValueError as e:
            errors.append(f"Custom domain: {e}")
        
        return errors