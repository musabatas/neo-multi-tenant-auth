"""Factory utilities for creating organization entities and related objects.

Provides factory patterns for consistent object creation following DRY principles
and centralizing creation logic with parameter validation.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import asdict

from ....core.value_objects import OrganizationId
from ....utils import generate_uuid_v7
from ..entities.organization import Organization
from .validation import OrganizationValidationRules


class OrganizationFactory:
    """Factory for creating organization entities with consistent defaults and validation."""
    
    @staticmethod
    def create_organization(
        name: str,
        slug: Optional[str] = None,
        legal_name: Optional[str] = None,
        tax_id: Optional[str] = None,
        business_type: Optional[str] = None,
        industry: Optional[str] = None,
        company_size: Optional[str] = None,
        website_url: Optional[str] = None,
        primary_contact_id: Optional[str] = None,
        # Address fields
        address_line1: Optional[str] = None,
        address_line2: Optional[str] = None,
        city: Optional[str] = None,
        state_province: Optional[str] = None,
        postal_code: Optional[str] = None,
        country_code: Optional[str] = None,
        full_address: Optional[str] = None,
        # Localization
        default_timezone: str = "UTC",
        default_locale: str = "en-US",
        default_currency: str = "USD",
        # Branding
        logo_url: Optional[str] = None,
        brand_colors: Optional[Dict[str, str]] = None,
        # Status
        is_active: bool = True,
        is_verified: bool = False,
        verified_at: Optional[datetime] = None,
        verification_documents: Optional[List[str]] = None,
        # Metadata
        custom_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Organization:
        """Create a new organization entity with validation and defaults.
        
        Args:
            name: Organization display name (required)
            slug: Organization slug (auto-generated if not provided)
            legal_name: Legal business name
            tax_id: Tax identification number
            business_type: Type of business entity
            industry: Industry category
            company_size: Company size category
            website_url: Website URL
            primary_contact_id: Primary contact user ID
            address_line1: Address line 1
            address_line2: Address line 2
            city: City
            state_province: State or province
            postal_code: Postal code
            country_code: ISO 2-letter country code
            full_address: Formatted full address
            default_timezone: Default timezone (default: UTC)
            default_locale: Default locale (default: en-US)
            default_currency: Default currency (default: USD)
            logo_url: Logo URL
            brand_colors: Brand color scheme
            is_active: Whether organization is active (default: True)
            is_verified: Whether organization is verified (default: False)
            verified_at: Verification timestamp
            verification_documents: List of verification document URLs
            custom_id: Custom organization ID (generates UUIDv7 if not provided)
            metadata: Additional metadata
            
        Returns:
            Organization entity
            
        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        validated_name = OrganizationValidationRules.validate_display_name(name)
        
        # Generate slug if not provided
        if slug is None:
            slug = OrganizationValidationRules.name_to_slug(validated_name)
        else:
            slug = OrganizationValidationRules.validate_slug(slug)
        
        # Generate ID if not provided
        if custom_id is None:
            org_id = OrganizationId(value=str(generate_uuid_v7()))
        else:
            org_id = OrganizationId(value=custom_id)
        
        # Normalize optional fields
        if legal_name:
            legal_name = legal_name.strip()
        if tax_id:
            tax_id = tax_id.strip().upper()
        if business_type:
            business_type = business_type.strip()
        if industry:
            industry = industry.strip()
        if company_size:
            company_size = company_size.strip()
        if website_url:
            website_url = website_url.strip()
            if not website_url.startswith(('http://', 'https://')):
                website_url = f"https://{website_url}"
        
        # Normalize address fields
        if address_line1:
            address_line1 = address_line1.strip()
        if address_line2:
            address_line2 = address_line2.strip()
        if city:
            city = city.strip()
        if state_province:
            state_province = state_province.strip()
        if postal_code:
            postal_code = postal_code.strip()
        if country_code:
            country_code = country_code.strip().upper()
            if len(country_code) != 2:
                raise ValueError("Country code must be 2 characters")
        
        # Generate full address if components provided
        if not full_address and any([address_line1, city, state_province, postal_code, country_code]):
            address_parts = []
            if address_line1:
                address_parts.append(address_line1)
            if address_line2:
                address_parts.append(address_line2)
            if city:
                address_parts.append(city)
            if state_province:
                address_parts.append(state_province)
            if postal_code:
                address_parts.append(postal_code)
            if country_code:
                address_parts.append(country_code)
            full_address = ", ".join(address_parts)
        
        # Set defaults
        if brand_colors is None:
            brand_colors = {}
        if verification_documents is None:
            verification_documents = []
        if metadata is None:
            metadata = {}
        
        # Set timestamps
        now = datetime.utcnow()
        
        return Organization(
            id=org_id,
            name=validated_name,
            slug=slug,
            legal_name=legal_name,
            tax_id=tax_id,
            business_type=business_type,
            industry=industry,
            company_size=company_size,
            website_url=website_url,
            primary_contact_id=primary_contact_id,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state_province=state_province,
            postal_code=postal_code,
            country_code=country_code,
            full_address=full_address,
            default_timezone=default_timezone,
            default_locale=default_locale,
            default_currency=default_currency,
            logo_url=logo_url,
            brand_colors=brand_colors,
            is_active=is_active,
            is_verified=is_verified,
            verified_at=verified_at,
            verification_documents=verification_documents,
            metadata=metadata,
            created_at=now,
            updated_at=now
        )
    
    @staticmethod
    def create_from_request(request, custom_id: Optional[str] = None, **kwargs) -> Organization:
        """Create organization from request model.
        
        Args:
            request: CreateOrganizationRequest or similar request model
            custom_id: Custom organization ID
            
        Returns:
            Organization entity
        """
        # Convert request to dictionary for unpacking
        if hasattr(request, 'dict'):
            # Pydantic v1/v2 compatibility
            try:
                request_data = request.model_dump()  # Pydantic v2
            except AttributeError:
                request_data = request.dict()  # Pydantic v1
        elif hasattr(request, '__dict__'):
            request_data = request.__dict__
        else:
            # Assume it's already a dictionary
            request_data = dict(request)
        
        # Add custom ID if provided
        if custom_id:
            request_data['custom_id'] = custom_id
        
        # Add additional kwargs
        request_data.update(kwargs)
        
        return OrganizationFactory.create_organization(**request_data)
    
    @staticmethod
    def create_from_dict(data: Dict[str, Any]) -> Organization:
        """Create organization from dictionary data.
        
        Args:
            data: Dictionary containing organization data
            
        Returns:
            Organization entity
        """
        return OrganizationFactory.create_organization(**data)
    
    @staticmethod
    def update_organization(
        existing: Organization,
        updates: Dict[str, Any],
        validate_changes: bool = True
    ) -> Organization:
        """Create updated organization entity from existing one.
        
        Args:
            existing: Existing organization entity
            updates: Dictionary of fields to update
            validate_changes: Whether to validate updated fields
            
        Returns:
            New organization entity with updates applied
        """
        # Convert existing organization to dictionary
        current_data = asdict(existing)
        
        # Remove ID field to prevent modification
        if 'id' in updates:
            del updates['id']
        
        # Apply updates
        current_data.update(updates)
        
        # Always update the timestamp
        current_data['updated_at'] = datetime.utcnow()
        
        # Validate critical fields if requested
        if validate_changes:
            if 'name' in updates:
                current_data['name'] = OrganizationValidationRules.validate_display_name(current_data['name'])
            if 'slug' in updates:
                current_data['slug'] = OrganizationValidationRules.validate_slug(current_data['slug'])
        
        # Convert ID back to value object (it becomes string in asdict)
        if isinstance(current_data.get('id'), str):
            current_data['id'] = OrganizationId(value=current_data['id'])
        
        # Create new organization entity
        return Organization(**current_data)


class OrganizationTestFactory:
    """Factory for creating test organization entities with predefined data patterns."""
    
    @staticmethod
    def create_test_organization(
        name_suffix: str = "",
        industry: str = "Technology",
        country_code: str = "US",
        **overrides
    ) -> Organization:
        """Create a test organization with realistic defaults.
        
        Args:
            name_suffix: Suffix to add to organization name for uniqueness
            industry: Industry category
            country_code: Country code
            **overrides: Additional field overrides
            
        Returns:
            Test organization entity
        """
        base_data = {
            "name": f"Test Organization{name_suffix}",
            "legal_name": f"Test Organization Inc.{name_suffix}",
            "tax_id": f"12-345678{len(name_suffix)}",
            "business_type": "Corporation",
            "industry": industry,
            "company_size": "11-50",
            "website_url": f"https://test-org{name_suffix.lower()}.com",
            "address_line1": "123 Test Street",
            "city": "Test City",
            "state_province": "TC",
            "postal_code": "12345",
            "country_code": country_code,
            "brand_colors": {"primary": "#007bff", "secondary": "#6c757d"},
            "is_active": True,
            "is_verified": False
        }
        
        # Apply overrides
        base_data.update(overrides)
        
        return OrganizationFactory.create_organization(**base_data)
    
    @staticmethod
    def create_minimal_organization(name: str = "Minimal Org") -> Organization:
        """Create organization with minimal required fields.
        
        Args:
            name: Organization name
            
        Returns:
            Minimal organization entity
        """
        return OrganizationFactory.create_organization(name=name)
    
    @staticmethod
    def create_verified_organization(name: str = "Verified Org") -> Organization:
        """Create a verified organization for testing.
        
        Args:
            name: Organization name
            
        Returns:
            Verified organization entity
        """
        return OrganizationFactory.create_organization(
            name=name,
            is_verified=True,
            verified_at=datetime.utcnow(),
            verification_documents=["https://example.com/doc1.pdf"]
        )
    
    @staticmethod
    def create_organization_batch(
        count: int,
        name_prefix: str = "Batch Org",
        **base_overrides
    ) -> List[Organization]:
        """Create multiple test organizations for batch testing.
        
        Args:
            count: Number of organizations to create
            name_prefix: Prefix for organization names
            **base_overrides: Base overrides applied to all organizations
            
        Returns:
            List of organization entities
        """
        organizations = []
        
        for i in range(count):
            org_data = base_overrides.copy()
            org_data.update({
                "name": f"{name_prefix} {i+1}",
                "slug": f"{name_prefix.lower().replace(' ', '-')}-{i+1}",
                "industry": ["Technology", "Healthcare", "Finance", "Education", "Retail"][i % 5]
            })
            
            organizations.append(OrganizationFactory.create_organization(**org_data))
        
        return organizations