"""
Schema enhancers for OpenAPI documentation.
Provides reusable schema enhancement functions for security, examples, and other extensions.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def enhance_schema_with_security(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schema customizer that adds security definitions.
    
    Args:
        schema: Base OpenAPI schema
        
    Returns:
        Enhanced schema with security definitions
    """
    # Add security schemes
    security_schemes = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        },
        "GuestSession": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Guest-Session"
        }
    }
    
    if "components" not in schema:
        schema["components"] = {}
    
    schema["components"]["securitySchemes"] = security_schemes
    
    # Add global security requirement (can be overridden per endpoint)
    schema["security"] = [
        {"BearerAuth": []},
        {"GuestSession": []}
    ]
    
    return schema


def enhance_schema_with_examples(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schema customizer that adds common response examples.
    
    Args:
        schema: Base OpenAPI schema
        
    Returns:
        Enhanced schema with response examples
    """
    if "components" not in schema:
        schema["components"] = {}
    
    if "examples" not in schema["components"]:
        schema["components"]["examples"] = {}
    
    # Add common response examples
    common_examples = {
        "SuccessResponse": {
            "summary": "Successful operation",
            "value": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {},
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123"
                }
            }
        },
        "ErrorResponse": {
            "summary": "Error response",
            "value": {
                "success": False,
                "message": "An error occurred",
                "errors": [{
                    "error": "ValidationError",
                    "message": "Invalid input data",
                    "field": "email"
                }],
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123"
                }
            }
        },
        "PaginatedResponse": {
            "summary": "Paginated response",
            "value": {
                "success": True,
                "data": {
                    "items": [],
                    "pagination": {
                        "page": 1,
                        "page_size": 20,
                        "total_pages": 5,
                        "total_items": 100,
                        "has_next": True,
                        "has_previous": False
                    }
                },
                "message": "Data retrieved successfully"
            }
        }
    }
    
    schema["components"]["examples"].update(common_examples)
    return schema


def enhance_schema_with_tenant_security(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schema customizer that adds tenant-specific security definitions.
    
    Args:
        schema: Base OpenAPI schema
        
    Returns:
        Enhanced schema with tenant security definitions
    """
    # Add tenant-specific security schemes
    security_schemes = {
        "TenantBearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Tenant-scoped JWT token"
        },
        "TenantApiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Tenant-API-Key",
            "description": "Tenant API key for service-to-service communication"
        }
    }
    
    if "components" not in schema:
        schema["components"] = {}
    
    if "securitySchemes" not in schema["components"]:
        schema["components"]["securitySchemes"] = {}
    
    schema["components"]["securitySchemes"].update(security_schemes)
    
    # Add tenant security requirements
    if "security" not in schema:
        schema["security"] = []
    
    schema["security"].extend([
        {"TenantBearerAuth": []},
        {"TenantApiKey": []}
    ])
    
    return schema


def enhance_schema_with_admin_security(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schema customizer that adds admin-specific security definitions.
    
    Args:
        schema: Base OpenAPI schema
        
    Returns:
        Enhanced schema with admin security definitions
    """
    # Add admin-specific security schemes
    security_schemes = {
        "AdminBearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Platform admin JWT token"
        },
        "AdminApiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Admin-API-Key",
            "description": "Platform admin API key for administrative operations"
        }
    }
    
    if "components" not in schema:
        schema["components"] = {}
    
    if "securitySchemes" not in schema["components"]:
        schema["components"]["securitySchemes"] = {}
    
    schema["components"]["securitySchemes"].update(security_schemes)
    
    # Add admin security requirements
    if "security" not in schema:
        schema["security"] = []
    
    schema["security"].extend([
        {"AdminBearerAuth": []},
        {"AdminApiKey": []}
    ])
    
    return schema


def enhance_schema_with_cors_info(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schema customizer that adds CORS information to the schema.
    
    Args:
        schema: Base OpenAPI schema
        
    Returns:
        Enhanced schema with CORS information
    """
    if "info" not in schema:
        schema["info"] = {}
    
    if "x-cors" not in schema["info"]:
        schema["info"]["x-cors"] = {
            "allowedOrigins": ["*"],
            "allowedMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allowedHeaders": ["Content-Type", "Authorization", "X-Requested-With"],
            "exposedHeaders": ["X-Total-Count", "X-Request-ID"],
            "allowCredentials": True,
            "maxAge": 86400
        }
    
    return schema


def enhance_schema_with_rate_limiting_info(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schema customizer that adds rate limiting information to the schema.
    
    Args:
        schema: Base OpenAPI schema
        
    Returns:
        Enhanced schema with rate limiting information
    """
    if "info" not in schema:
        schema["info"] = {}
    
    if "x-rate-limiting" not in schema["info"]:
        schema["info"]["x-rate-limiting"] = {
            "default": {
                "requests": 60,
                "period": "1 minute",
                "headers": {
                    "limit": "X-RateLimit-Limit",
                    "remaining": "X-RateLimit-Remaining",
                    "reset": "X-RateLimit-Reset"
                }
            },
            "authenticated": {
                "requests": 1000,
                "period": "1 hour"
            },
            "guest": {
                "requests": 100,
                "period": "1 hour"
            }
        }
    
    return schema