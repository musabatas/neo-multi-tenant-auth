---
title: Global Project Patterns
entry_count: 55
last_updated: 2025-08-13
---

1. All services use async patterns (async/await) for I/O operations
2. Project requires UUIDv7 for all UUID generation (time-ordered IDs)
3. Function length limit is 80 lines per project standards
4. Router registration uses dual pattern (with and without API prefix)
5. Production flag controls API documentation endpoint visibility
6. Health check endpoints include service latency measurements
7. Lifespan context managers handle startup/shutdown with resource cleanup
8. OpenAPI schemas customized with x-tagGroups for organized documentation
9. Router order matters - specific paths (/users/me) registered before generic (/users)
10. Uvicorn server configuration uses settings pattern with environment-based defaults
11. Feature modules organized with separate directories for integrations, features, and common utilities
12. Common module substructure includes cache, config, database, exceptions, middleware, models, repositories, routers, services, and utils
13. Custom routers handle both trailing and non-trailing slash endpoints to avoid 307 redirects
14. Structured logging includes request_id, correlation_id, user_id, and tenant_id context through ContextVars
15. Middleware uses loguru logger for structured logging with automatic performance classification
16. Middleware added in reverse order since FastAPI/Starlette processes them in LIFO order
17. Environment-specific middleware configurations using factory pattern (development, production, testing)
18. Sensitive headers filtered in logging middleware (authorization, cookie, x-api-key, x-keycloak-token)
19. Request IDs shortened to 8 characters from full UUID for performance in middleware
20. Performance timing uses time.perf_counter() for high-precision measurements in milliseconds
21. Security middleware implements CSP with environment-specific configurations (relaxed for development)
22. Rate limiting middleware uses in-memory storage in development, requires Redis for production
23. Middleware packages use __all__ exports for controlled public API and clear module boundaries
24. Query parameters are logged directly in middleware without filtering for sensitive data patterns
25. Common modules use __all__ exports for controlled public API (middleware, exceptions, utils, services, repositories, models)
26. Database modules should export main classes and functions through __init__.py following project patterns
27. Database connections use asyncpg directly without ORMs for performance-critical paths
28. Dynamic database connections loaded from admin.database_connections table for multi-region support
29. Connection pools configured with application_name and JIT settings for PostgreSQL optimization
30. SQL filter building functions must validate field names to prevent SQL injection attacks
31. Cache operations use redis.asyncio with connection pooling and health check intervals
32. Cache manager uses global singleton pattern with get_cache() factory function
33. Config modules should export Settings, get_settings, and settings instance through __init__.py with __all__ declaration
34. Settings use Pydantic BaseSettings with Field definitions for environment variable loading
35. Settings include environment-specific properties (is_production, is_development, is_testing)
36. Settings use SecretStr type for sensitive configuration values like passwords and API keys
37. Encryption utilities use PBKDF2 with Fernet for password encryption following NeoInfrastructure patterns
38. Singleton pattern used for shared utilities with get_[utility]() factory functions for global instances
39. Metadata collection utilities use ContextVars for thread-safe request-scoped state management
40. Performance metadata only includes non-zero counters to minimize API response payload size
41. Utils modules include comprehensive datetime utilities with UTC focus and format_iso8601 function
42. Datetime utilities consistently handle naive datetimes by assuming UTC timezone across all functions
43. UUID generation utilities should use cryptographically secure random sources (secrets module) for security-sensitive contexts
44. Repository base classes implement soft delete pattern with deleted_at timestamp checks in all queries
45. SQL field names in WHERE clauses must be validated against whitelist to prevent SQL injection attacks
46. Models package should export base models (BaseSchema, mixins) and common types (PaginatedResponse, PaginationParams) via __init__.py
47. Pagination models use Pydantic with Field descriptions and validation constraints (page_size limited to 100)
48. Pydantic models use ConfigDict with json_encoders for datetime and UUID serialization consistency
49. API response models include automatic metadata collection with graceful failure handling to never break responses
50. Service exceptions use HTTP status codes: 500 for internal errors, 502 for bad gateway, 503 for service unavailable
51. Domain exceptions inherit from base exception classes with contextual details stored in a details dictionary
52. Exception modules categorize exceptions into base/HTTP, domain-specific, and service/infrastructure groups for clear separation
53. Exception classes include to_dict() method for API response serialization with error, message, details, and status_code fields
54. Base service classes provide common patterns for pagination metadata, error handling, and response formatting
55. Integration modules should have proper __init__.py with exports even if subdirectories handle specific implementations
