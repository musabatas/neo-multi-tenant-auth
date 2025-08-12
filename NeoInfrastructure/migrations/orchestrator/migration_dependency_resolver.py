#!/usr/bin/env python3
"""
Migration Dependency Resolver
Ensures migrations are executed in the correct order based on schema dependencies
"""

from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class SchemaType(Enum):
    """Types of schemas in the system"""
    PLATFORM_COMMON = "platform_common"
    ADMIN = "admin"
    TENANT_TEMPLATE = "tenant_template"
    ANALYTICS = "analytics"
    TENANT_SPECIFIC = "tenant_specific"  # e.g., tenant_123


@dataclass
class SchemaMigration:
    """Represents a schema that needs to be migrated"""
    schema_name: str
    schema_type: SchemaType
    migration_location: str
    dependencies: List[str]  # List of schema names this depends on


class MigrationDependencyResolver:
    """Resolves migration order based on schema dependencies"""
    
    # Schema dependency graph
    SCHEMA_DEPENDENCIES = {
        SchemaType.PLATFORM_COMMON: [],  # No dependencies
        SchemaType.ADMIN: [SchemaType.PLATFORM_COMMON],
        SchemaType.TENANT_TEMPLATE: [SchemaType.PLATFORM_COMMON],
        SchemaType.ANALYTICS: [SchemaType.PLATFORM_COMMON],
        SchemaType.TENANT_SPECIFIC: [SchemaType.PLATFORM_COMMON, SchemaType.TENANT_TEMPLATE],
    }
    
    # Schema to migration location mapping
    SCHEMA_LOCATIONS = {
        SchemaType.PLATFORM_COMMON: "platform",
        SchemaType.ADMIN: "admin",
        SchemaType.TENANT_TEMPLATE: "regional/shared",
        SchemaType.ANALYTICS: "regional/analytics",
        SchemaType.TENANT_SPECIFIC: "regional/shared",  # Uses tenant_template migrations
    }
    
    @classmethod
    def get_schema_type(cls, schema_name: str) -> SchemaType:
        """Determine schema type from schema name"""
        if schema_name == "platform_common":
            return SchemaType.PLATFORM_COMMON
        elif schema_name == "admin":
            return SchemaType.ADMIN
        elif schema_name == "tenant_template":
            return SchemaType.TENANT_TEMPLATE
        elif schema_name == "analytics":
            return SchemaType.ANALYTICS
        elif schema_name.startswith("tenant_"):
            return SchemaType.TENANT_SPECIFIC
        else:
            # Default to tenant_template for unknown schemas
            return SchemaType.TENANT_TEMPLATE
    
    @classmethod
    def get_migration_order(cls, schemas: List[str]) -> List[SchemaMigration]:
        """
        Given a list of schema names, return them in the correct migration order
        with their dependencies resolved
        """
        # Build schema migration objects
        schema_migrations = []
        for schema_name in schemas:
            schema_type = cls.get_schema_type(schema_name)
            dependencies = [dep.value for dep in cls.SCHEMA_DEPENDENCIES.get(schema_type, [])]
            
            migration = SchemaMigration(
                schema_name=schema_name,
                schema_type=schema_type,
                migration_location=cls.SCHEMA_LOCATIONS[schema_type],
                dependencies=dependencies
            )
            schema_migrations.append(migration)
        
        # Topological sort to resolve dependencies
        sorted_migrations = cls._topological_sort(schema_migrations)
        return sorted_migrations
    
    @classmethod
    def _topological_sort(cls, migrations: List[SchemaMigration]) -> List[SchemaMigration]:
        """
        Perform topological sort on migrations based on dependencies
        """
        # Create a map of schema name to migration
        migration_map = {m.schema_name: m for m in migrations}
        
        # Track visited and result
        visited = set()
        result = []
        
        def visit(migration: SchemaMigration):
            if migration.schema_name in visited:
                return
            
            visited.add(migration.schema_name)
            
            # Visit dependencies first
            for dep_name in migration.dependencies:
                # Only visit if dependency is in our migration list
                if dep_name in migration_map:
                    visit(migration_map[dep_name])
                else:
                    # If dependency not in list, add it (e.g., platform_common)
                    dep_type = cls.get_schema_type(dep_name)
                    dep_migration = SchemaMigration(
                        schema_name=dep_name,
                        schema_type=dep_type,
                        migration_location=cls.SCHEMA_LOCATIONS[dep_type],
                        dependencies=[]
                    )
                    migration_map[dep_name] = dep_migration
                    visit(dep_migration)
            
            result.append(migration)
        
        # Visit all migrations
        for migration in migrations:
            visit(migration)
        
        return result
    
    @classmethod
    def get_required_schemas_for_database(cls, database_name: str) -> List[str]:
        """
        Determine which schemas should be migrated for a given database
        """
        schemas = []
        
        if "admin" in database_name:
            schemas = ["platform_common", "admin"]
        elif "shared" in database_name:
            schemas = ["platform_common", "tenant_template"]
        elif "analytics" in database_name:
            schemas = ["platform_common", "analytics"]
        elif database_name.startswith("tenant_"):
            # Specific tenant database
            tenant_schema = database_name.replace("neofast_", "")
            schemas = ["platform_common", "tenant_template", tenant_schema]
        
        return schemas
    
    @classmethod
    def build_flyway_config(cls, 
                           database_url: str,
                           username: str, 
                           password: str,
                           schema_name: str,
                           migration_location: str) -> str:
        """
        Build a Flyway configuration for a specific schema
        """
        return f"""# Auto-generated Flyway configuration for {schema_name}
flyway.url={database_url}
flyway.user={username}
flyway.password={password}
flyway.schemas={schema_name}
flyway.defaultSchema={schema_name}
flyway.table=flyway_schema_history
flyway.locations=filesystem:/app/flyway/{migration_location}
flyway.baselineOnMigrate=true
flyway.validateOnMigrate=true
flyway.cleanDisabled=true
flyway.mixed=true
flyway.outOfOrder=false
"""


# Example usage
if __name__ == "__main__":
    # Test dependency resolution
    schemas = ["admin", "tenant_template"]
    ordered = MigrationDependencyResolver.get_migration_order(schemas)
    
    print("Migration order:")
    for migration in ordered:
        deps = f" (depends on: {', '.join(migration.dependencies)})" if migration.dependencies else ""
        print(f"  {migration.schema_name}{deps}")