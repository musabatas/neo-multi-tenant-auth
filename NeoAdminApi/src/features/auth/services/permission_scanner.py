"""
Permission scanner for discovering endpoint permissions.
"""
from typing import List, Dict, Any, Set, Optional
from fastapi import FastAPI
from fastapi.routing import APIRoute
from loguru import logger
from neo_commons.auth.decorators import PermissionMetadata


class EndpointPermissionScanner:
    """
    Scans FastAPI application to discover all endpoint permissions.
    
    Features:
    - Discovers all routes and their permission requirements
    - Extracts permission metadata from decorators
    - Generates permission definitions for database sync
    """
    
    def __init__(self, app: FastAPI):
        """
        Initialize scanner with FastAPI app.
        
        Args:
            app: FastAPI application instance
        """
        self.app = app
        self.discovered_permissions: Dict[str, Dict[str, Any]] = {}
        self.discovered_endpoints: List[Dict[str, Any]] = []
    
    def scan(self) -> Dict[str, Dict[str, Any]]:
        """
        Scan application and discover all permissions.
        
        Returns:
            Dictionary of permission code -> permission definition
        """
        logger.info("Starting endpoint permission discovery...")
        
        # Clear previous discoveries
        self.discovered_permissions.clear()
        self.discovered_endpoints.clear()
        
        # Scan all routes
        for route in self.app.routes:
            if isinstance(route, APIRoute):
                self._process_route(route)
        
        logger.info(f"Discovered {len(self.discovered_permissions)} unique permissions")
        logger.info(f"Discovered {len(self.discovered_endpoints)} protected endpoints")
        
        return self.discovered_permissions
    
    def _process_route(self, route: APIRoute):
        """
        Process a single route to extract permissions.
        
        Args:
            route: FastAPI route to process
        """
        # Get the endpoint function
        endpoint = route.endpoint
        if not endpoint:
            return
        
        # Extract permission metadata
        permissions_metadata = PermissionMetadata.extract(endpoint)
        
        if not permissions_metadata:
            # No permissions required for this endpoint
            return
        
        # Process each permission requirement
        for perm_meta in permissions_metadata:
            endpoint_info = {
                'path': route.path,
                'methods': list(route.methods),
                'name': route.name,
                'permissions': perm_meta['permissions'],
                'scope': perm_meta['scope'],
                'any_of': perm_meta.get('any_of', False)
            }
            self.discovered_endpoints.append(endpoint_info)
            
            # Process each individual permission
            for permission_code in perm_meta['permissions']:
                self._add_permission(
                    code=permission_code,
                    scope=perm_meta['scope'],
                    description=perm_meta.get('description'),
                    is_dangerous=perm_meta.get('is_dangerous', False),
                    requires_mfa=perm_meta.get('requires_mfa', False),
                    requires_approval=perm_meta.get('requires_approval', False),
                    endpoint_path=route.path,
                    methods=list(route.methods)
                )
    
    def _add_permission(
        self,
        code: str,
        scope: str,
        description: Optional[str],
        is_dangerous: bool,
        requires_mfa: bool,
        requires_approval: bool,
        endpoint_path: str,
        methods: List[str]
    ):
        """
        Add a discovered permission to the registry.
        
        Args:
            code: Permission code (e.g., "users:read")
            scope: Permission scope level
            description: Permission description
            is_dangerous: Whether dangerous operation
            requires_mfa: Whether MFA required
            requires_approval: Whether approval required
            endpoint_path: API endpoint path
            methods: HTTP methods
        """
        # Parse resource and action from code
        if ':' in code:
            resource, action = code.split(':', 1)
        else:
            resource = code
            action = 'access'
        
        # Generate description if not provided
        if not description:
            description = self._generate_description(resource, action, scope)
        
        # Create or update permission definition
        if code not in self.discovered_permissions:
            self.discovered_permissions[code] = {
                'code': code,
                'resource': resource,
                'action': action,
                'scope_level': scope,
                'description': description,
                'is_dangerous': is_dangerous,
                'requires_mfa': requires_mfa,
                'requires_approval': requires_approval,
                'endpoints': []
            }
        
        # Add endpoint reference
        self.discovered_permissions[code]['endpoints'].append({
            'path': endpoint_path,
            'methods': methods
        })
        
        # Update flags (use most restrictive)
        perm = self.discovered_permissions[code]
        perm['is_dangerous'] = perm['is_dangerous'] or is_dangerous
        perm['requires_mfa'] = perm['requires_mfa'] or requires_mfa
        perm['requires_approval'] = perm['requires_approval'] or requires_approval
    
    def _generate_description(self, resource: str, action: str, scope: str) -> str:
        """
        Generate a human-readable description for a permission.
        
        Args:
            resource: Resource name
            action: Action name
            scope: Scope level
            
        Returns:
            Generated description
        """
        action_verbs = {
            'read': 'View',
            'write': 'Modify',
            'create': 'Create',
            'update': 'Update',
            'delete': 'Delete',
            'list': 'List',
            'execute': 'Execute',
            'export': 'Export',
            'import': 'Import',
            'approve': 'Approve',
            'reject': 'Reject',
            'access': 'Access'
        }
        
        verb = action_verbs.get(action, action.capitalize())
        resource_name = resource.replace('_', ' ').replace('-', ' ').title()
        
        if scope == 'platform':
            return f"{verb} platform-level {resource_name}"
        elif scope == 'tenant':
            return f"{verb} tenant-level {resource_name}"
        else:
            return f"{verb} {resource_name}"
    
    def get_endpoint_report(self) -> str:
        """
        Generate a report of discovered endpoints and permissions.
        
        Returns:
            Formatted report string
        """
        report = ["=" * 80]
        report.append("ENDPOINT PERMISSION DISCOVERY REPORT")
        report.append("=" * 80)
        
        # Summary
        report.append(f"\nSummary:")
        report.append(f"  - Total Endpoints: {len(self.discovered_endpoints)}")
        report.append(f"  - Unique Permissions: {len(self.discovered_permissions)}")
        report.append(f"  - Platform Scope: {len([p for p in self.discovered_permissions.values() if p['scope_level'] == 'platform'])}")
        report.append(f"  - Tenant Scope: {len([p for p in self.discovered_permissions.values() if p['scope_level'] == 'tenant'])}")
        
        # Permissions by resource
        report.append(f"\nPermissions by Resource:")
        resources = {}
        for perm in self.discovered_permissions.values():
            resource = perm['resource']
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(perm['code'])
        
        for resource in sorted(resources.keys()):
            report.append(f"  {resource}:")
            for code in sorted(resources[resource]):
                perm = self.discovered_permissions[code]
                flags = []
                if perm['is_dangerous']:
                    flags.append("⚠️ DANGEROUS")
                if perm['requires_mfa']:
                    flags.append("MFA")
                if perm['requires_approval']:
                    flags.append("✅ APPROVAL")
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                report.append(f"    - {code}: {perm['description']}{flag_str}")
        
        # Protected endpoints
        report.append(f"\nProtected Endpoints:")
        for endpoint in sorted(self.discovered_endpoints, key=lambda x: x['path']):
            methods_str = ','.join(endpoint['methods'])
            perms_str = ', '.join(endpoint['permissions'])
            any_of_str = " (ANY)" if endpoint.get('any_of') else " (ALL)"
            report.append(f"  {methods_str} {endpoint['path']}")
            report.append(f"    Requires: {perms_str}{any_of_str}")
            report.append(f"    Scope: {endpoint['scope']}")
        
        report.append("=" * 80)
        return '\n'.join(report)