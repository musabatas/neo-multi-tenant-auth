"""Organization validation service for business logic validation.

Handles business rule validation including tax ID, website, address,
and business registration validation. Follows single responsibility principle.
"""

import logging
from typing import Dict, Any

from ....core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class OrganizationValidationService:
    """Service for organization business validation operations.
    
    Handles complex business rule validation including tax IDs,
    website URLs, addresses, and business registration verification.
    """
    
    def __init__(self):
        """Initialize validation service.
        
        In a real implementation, this would accept external validation
        service clients, API keys, etc.
        """
        pass
    
    async def validate_organization_data(self, data: Dict[str, Any]) -> None:
        """Validate organization data using business rules.
        
        Args:
            data: Organization data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate tax ID if provided
        if "tax_id" in data and "country_code" in data:
            tax_id = data["tax_id"]
            country_code = data["country_code"]
            if tax_id and country_code:
                is_valid = await self.validate_tax_id(tax_id, country_code)
                if not is_valid:
                    raise ValidationError(f"Invalid tax ID '{tax_id}' for country '{country_code}'")
        
        # Validate website URL if provided
        if "website_url" in data and data["website_url"]:
            is_valid = await self.validate_website(data["website_url"])
            if not is_valid:
                raise ValidationError(f"Invalid or inaccessible website URL: {data['website_url']}")
        
        # Validate business registration if all required fields present
        if all(field in data for field in ["legal_name", "tax_id", "country_code"]):
            legal_name = data["legal_name"]
            tax_id = data["tax_id"]
            country_code = data["country_code"]
            
            if legal_name and tax_id and country_code:
                result = await self.validate_business_registration(
                    legal_name, tax_id, country_code
                )
                if not result.get("valid", True):
                    raise ValidationError(f"Business registration validation failed: {result.get('error', 'Unknown error')}")
    
    async def validate_tax_id(self, tax_id: str, country_code: str) -> bool:
        """Validate tax ID for given country.
        
        Args:
            tax_id: Tax identification number
            country_code: ISO 2-letter country code
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Simulate tax ID validation logic
            # In real implementation, this would call external validation services
            
            # Basic validation rules by country
            if country_code.upper() == "US":
                # US EIN format: XX-XXXXXXX
                return len(tax_id.replace("-", "")) == 9 and tax_id.count("-") <= 1
            elif country_code.upper() == "GB":
                # UK UTR format: 10 digits
                return tax_id.isdigit() and len(tax_id) == 10
            elif country_code.upper() == "DE":
                # German tax number: various formats, 10-11 digits
                clean_tax_id = tax_id.replace("/", "").replace(" ", "")
                return clean_tax_id.isdigit() and 10 <= len(clean_tax_id) <= 11
            else:
                # For other countries, assume valid if not empty
                return bool(tax_id.strip())
                
        except Exception as e:
            logger.error(f"Tax ID validation failed for {tax_id} ({country_code}): {e}")
            return False
    
    async def validate_website(self, website_url: str) -> bool:
        """Validate website URL accessibility.
        
        Args:
            website_url: Website URL to validate
            
        Returns:
            True if accessible, False otherwise
        """
        try:
            import re
            
            # Basic URL format validation
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(website_url):
                return False
            
            # In real implementation, would make HTTP request to check accessibility
            # For now, simulate basic validation
            return True
            
        except Exception as e:
            logger.error(f"Website validation failed for {website_url}: {e}")
            return False
    
    async def validate_business_registration(
        self,
        legal_name: str,
        tax_id: str,
        country_code: str
    ) -> Dict[str, Any]:
        """Validate business registration information.
        
        Args:
            legal_name: Legal business name
            tax_id: Tax identification number
            country_code: ISO 2-letter country code
            
        Returns:
            Dictionary with validation result and details
        """
        try:
            # Simulate business registration validation
            # In real implementation, would call government databases/APIs
            
            validation_result = {
                "valid": True,
                "legal_name_matches": True,
                "tax_id_valid": await self.validate_tax_id(tax_id, country_code),
                "registration_active": True,
                "details": {
                    "verified_legal_name": legal_name,
                    "registration_date": "2020-01-15",  # Simulated
                    "status": "active"
                }
            }
            
            # Overall validation is valid if all components are valid
            validation_result["valid"] = all([
                validation_result["legal_name_matches"],
                validation_result["tax_id_valid"],
                validation_result["registration_active"]
            ])
            
            if not validation_result["valid"]:
                validation_result["error"] = "Business registration validation failed - see details"
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Business registration validation failed: {e}")
            return {
                "valid": False,
                "error": f"Validation service error: {str(e)}"
            }
    
    async def validate_address(self, address_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Validate address information.
        
        Args:
            address_fields: Address data to validate
            
        Returns:
            Dictionary with validation result
        """
        try:
            # Simulate address validation
            # In real implementation, would call address validation services
            
            required_fields = ["street", "city", "country"]
            missing_fields = [field for field in required_fields if not address_fields.get(field)]
            
            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Missing required address fields: {', '.join(missing_fields)}"
                }
            
            # Basic validation passed
            return {
                "valid": True,
                "normalized_address": address_fields,  # Would be normalized in real implementation
                "details": {
                    "geocoded": True,
                    "deliverable": True
                }
            }
            
        except Exception as e:
            logger.error(f"Address validation failed: {e}")
            return {
                "valid": False,
                "error": f"Address validation service error: {str(e)}"
            }