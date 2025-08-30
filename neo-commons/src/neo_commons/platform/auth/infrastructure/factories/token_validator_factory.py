"""Token validator factory for authentication platform."""

import logging
from typing import Dict, Any, List, Optional

from ...application.validators import (
    TokenFormatValidator,
    SignatureValidator,
    ExpirationValidator,
    AudienceValidator,
    FreshnessValidator
)
from ...core.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class TokenValidatorFactory:
    """Token validator factory following maximum separation principle.
    
    Handles ONLY token validator instantiation and configuration for authentication platform.
    Does not handle token validation logic, caching, or authentication operations.
    """
    
    def __init__(self, validator_config: Dict[str, Any]):
        """Initialize token validator factory.
        
        Args:
            validator_config: Token validator configuration dictionary
        """
        self.config = validator_config or {}
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate token validator configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate clock skew settings
        clock_skew = self.config.get("clock_skew_seconds", 60)
        if not isinstance(clock_skew, int) or clock_skew < 0:
            raise ValueError("Clock skew must be a non-negative integer")
        
        # Validate freshness settings
        max_age = self.config.get("max_age_seconds", 300)
        if not isinstance(max_age, int) or max_age <= 0:
            raise ValueError("Max age must be a positive integer")
        
        # Validate supported algorithms
        algorithms = self.config.get("supported_algorithms", [])
        if algorithms and not isinstance(algorithms, list):
            raise ValueError("Supported algorithms must be a list")
        
        logger.debug("Token validator configuration validated successfully")
    
    def create_token_format_validator(self) -> TokenFormatValidator:
        """Create token format validator.
        
        Returns:
            Configured TokenFormatValidator instance
        """
        try:
            logger.debug("Creating token format validator")
            
            # Get configuration
            strict_format = self.config.get("strict_format_validation", True)
            
            validator = TokenFormatValidator(strict_format=strict_format)
            
            logger.debug("Successfully created token format validator")
            return validator
            
        except Exception as e:
            logger.error(f"Failed to create token format validator: {e}")
            raise AuthenticationFailed(
                "Token format validator creation failed",
                reason="validator_creation_failed",
                context={"validator_type": "format", "error": str(e)}
            )
    
    def create_signature_validator(
        self,
        supported_algorithms: Optional[List[str]] = None
    ) -> SignatureValidator:
        """Create signature validator.
        
        Args:
            supported_algorithms: Optional list of supported algorithms
            
        Returns:
            Configured SignatureValidator instance
        """
        try:
            logger.debug("Creating signature validator")
            
            # Get configuration
            algorithms = supported_algorithms or self.config.get("supported_algorithms", [
                "RS256", "RS384", "RS512",
                "ES256", "ES384", "ES512", 
                "PS256", "PS384", "PS512"
            ])
            
            validator = SignatureValidator(supported_algorithms=algorithms)
            
            logger.debug(f"Successfully created signature validator with algorithms: {algorithms}")
            return validator
            
        except Exception as e:
            logger.error(f"Failed to create signature validator: {e}")
            raise AuthenticationFailed(
                "Signature validator creation failed",
                reason="validator_creation_failed",
                context={
                    "validator_type": "signature",
                    "algorithms": supported_algorithms,
                    "error": str(e)
                }
            )
    
    def create_expiration_validator(
        self,
        clock_skew_seconds: Optional[int] = None
    ) -> ExpirationValidator:
        """Create expiration validator.
        
        Args:
            clock_skew_seconds: Optional clock skew in seconds
            
        Returns:
            Configured ExpirationValidator instance
        """
        try:
            logger.debug("Creating expiration validator")
            
            # Get configuration
            clock_skew = clock_skew_seconds or self.config.get("clock_skew_seconds", 60)
            
            validator = ExpirationValidator(clock_skew_seconds=clock_skew)
            
            logger.debug(f"Successfully created expiration validator with clock skew: {clock_skew}s")
            return validator
            
        except Exception as e:
            logger.error(f"Failed to create expiration validator: {e}")
            raise AuthenticationFailed(
                "Expiration validator creation failed",
                reason="validator_creation_failed",
                context={
                    "validator_type": "expiration",
                    "clock_skew": clock_skew_seconds,
                    "error": str(e)
                }
            )
    
    def create_audience_validator(
        self,
        default_audiences: Optional[List[str]] = None,
        require_audience: Optional[bool] = None
    ) -> AudienceValidator:
        """Create audience validator.
        
        Args:
            default_audiences: Optional default expected audiences
            require_audience: Optional flag to require audience validation
            
        Returns:
            Configured AudienceValidator instance
        """
        try:
            logger.debug("Creating audience validator")
            
            # Get configuration
            audiences = default_audiences or self.config.get("default_audiences", [])
            require_aud = require_audience if require_audience is not None else self.config.get("require_audience", True)
            
            validator = AudienceValidator(
                default_audiences=audiences,
                require_audience=require_aud
            )
            
            logger.debug(f"Successfully created audience validator with audiences: {audiences}")
            return validator
            
        except Exception as e:
            logger.error(f"Failed to create audience validator: {e}")
            raise AuthenticationFailed(
                "Audience validator creation failed",
                reason="validator_creation_failed",
                context={
                    "validator_type": "audience",
                    "audiences": default_audiences,
                    "error": str(e)
                }
            )
    
    def create_freshness_validator(
        self,
        max_age_seconds: Optional[int] = None
    ) -> FreshnessValidator:
        """Create freshness validator.
        
        Args:
            max_age_seconds: Optional maximum age in seconds
            
        Returns:
            Configured FreshnessValidator instance
        """
        try:
            logger.debug("Creating freshness validator")
            
            # Get configuration
            max_age = max_age_seconds or self.config.get("max_age_seconds", 300)
            
            validator = FreshnessValidator(default_max_age_seconds=max_age)
            
            logger.debug(f"Successfully created freshness validator with max age: {max_age}s")
            return validator
            
        except Exception as e:
            logger.error(f"Failed to create freshness validator: {e}")
            raise AuthenticationFailed(
                "Freshness validator creation failed",
                reason="validator_creation_failed",
                context={
                    "validator_type": "freshness",
                    "max_age": max_age_seconds,
                    "error": str(e)
                }
            )
    
    def create_validator_set(
        self,
        validator_types: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a complete set of token validators.
        
        Args:
            validator_types: Optional list of validator types to create
            custom_config: Optional custom configuration overrides
            
        Returns:
            Dictionary mapping validator names to instances
        """
        try:
            logger.debug("Creating complete token validator set")
            
            # Default validator types
            types = validator_types or [
                "format", "signature", "expiration", "audience", "freshness"
            ]
            
            # Merge custom configuration
            config = {**self.config}
            if custom_config:
                config.update(custom_config)
            
            validators = {}
            
            # Create requested validators
            if "format" in types:
                validators["format"] = self.create_token_format_validator()
            
            if "signature" in types:
                algorithms = config.get("supported_algorithms")
                validators["signature"] = self.create_signature_validator(algorithms)
            
            if "expiration" in types:
                clock_skew = config.get("clock_skew_seconds")
                validators["expiration"] = self.create_expiration_validator(clock_skew)
            
            if "audience" in types:
                audiences = config.get("default_audiences")
                require_aud = config.get("require_audience")
                validators["audience"] = self.create_audience_validator(audiences, require_aud)
            
            if "freshness" in types:
                max_age = config.get("max_age_seconds")
                validators["freshness"] = self.create_freshness_validator(max_age)
            
            logger.debug(f"Successfully created {len(validators)} token validators")
            return validators
            
        except Exception as e:
            logger.error(f"Failed to create validator set: {e}")
            raise AuthenticationFailed(
                "Validator set creation failed",
                reason="validator_set_creation_failed",
                context={
                    "validator_types": validator_types,
                    "error": str(e)
                }
            )
    
    def create_validation_pipeline(
        self,
        pipeline_config: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Create token validation pipeline with ordered validators.
        
        Args:
            pipeline_config: Optional pipeline configuration
            
        Returns:
            List of validators in execution order
        """
        try:
            logger.debug("Creating token validation pipeline")
            
            config = pipeline_config or {}
            
            # Default validation order
            default_order = [
                "format", "signature", "expiration", "audience", "freshness"
            ]
            
            validation_order = config.get("validation_order", default_order)
            skip_validators = config.get("skip_validators", [])
            
            # Create validator set
            validators = self.create_validator_set()
            
            # Build pipeline in specified order
            pipeline = []
            for validator_name in validation_order:
                if validator_name not in skip_validators and validator_name in validators:
                    pipeline.append(validators[validator_name])
            
            logger.debug(f"Successfully created validation pipeline with {len(pipeline)} validators")
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to create validation pipeline: {e}")
            raise AuthenticationFailed(
                "Validation pipeline creation failed",
                reason="pipeline_creation_failed",
                context={
                    "pipeline_config": pipeline_config,
                    "error": str(e)
                }
            )
    
    def get_validator_info(self) -> Dict[str, Any]:
        """Get validator factory configuration information.
        
        Returns:
            Dictionary with validator factory information
        """
        return {
            "supported_validators": [
                "format", "signature", "expiration", "audience", "freshness"
            ],
            "default_config": {
                "clock_skew_seconds": self.config.get("clock_skew_seconds", 60),
                "max_age_seconds": self.config.get("max_age_seconds", 300),
                "strict_format_validation": self.config.get("strict_format_validation", True),
                "require_audience": self.config.get("require_audience", True),
                "supported_algorithms": self.config.get("supported_algorithms", [
                    "RS256", "RS384", "RS512",
                    "ES256", "ES384", "ES512", 
                    "PS256", "PS384", "PS512"
                ]),
                "default_audiences": self.config.get("default_audiences", [])
            },
            "factory_config": dict(self.config)
        }