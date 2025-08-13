#!/usr/bin/env python3
"""
CLI Client for NeoMultiTenant Deployment API
Interactive command-line interface for deployment and migration management
"""

import click
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
import time

console = Console()

# Default API URL
DEFAULT_API_URL = "http://localhost:8000"


class DeploymentAPIClient:
    """Client for interacting with the Deployment API"""
    
    def __init__(self, base_url: str = DEFAULT_API_URL):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        return self._request('GET', '/health')
    
    def check_services(self) -> list:
        """Check all services health"""
        return self._request('GET', '/health/services')
    
    def deploy(self, services: list, regions: list, skip_migrations: bool = False) -> Dict:
        """Deploy infrastructure"""
        data = {
            "services": services,
            "regions": regions,
            "skip_migrations": skip_migrations
        }
        return self._request('POST', '/api/v1/deploy', json=data)
    
    def get_deployment(self, deployment_id: str) -> Dict:
        """Get deployment status"""
        return self._request('GET', f'/api/v1/deploy/{deployment_id}')
    
    def list_deployments(self, status: Optional[str] = None, limit: int = 10) -> list:
        """List deployments"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._request('GET', '/api/v1/deployments', params=params)
    
    def apply_migrations(self, scope: str = "all", batch_size: int = 10) -> Dict:
        """Apply migrations"""
        data = {
            "scope": scope,
            "batch_size": batch_size
        }
        return self._request('POST', '/api/v1/migrations/apply', json=data)
    
    def get_migration_dashboard(self) -> Dict:
        """Get migration dashboard"""
        return self._request('GET', '/api/v1/migrations/status')
    
    def get_migration_status(self, database: str, schema: str = "public") -> Dict:
        """Get specific migration status"""
        return self._request('GET', f'/api/v1/migrations/status/{database}/{schema}')
    
    def migrate_tenant(self, tenant_id: str, tenant_slug: str, database: str, schema: str) -> Dict:
        """Migrate tenant schema"""
        data = {
            "tenant_id": tenant_id,
            "tenant_slug": tenant_slug,
            "database": database,
            "schema": schema,
            "create_schema": True
        }
        return self._request('POST', f'/api/v1/tenants/{tenant_id}/migrate', json=data)
    
    def rollback_migration(self, database: str, schema: str, target_version: str, dry_run: bool = True) -> Dict:
        """Rollback migration"""
        data = {
            "database": database,
            "schema": schema,
            "target_version": target_version,
            "dry_run": dry_run
        }
        return self._request('POST', '/api/v1/migrations/rollback', json=data)


# CLI Commands

@click.group()
@click.option('--api-url', default=DEFAULT_API_URL, envvar='NEO_API_URL', help='API base URL')
@click.pass_context
def cli(ctx, api_url):
    """NeoMultiTenant Deployment CLI"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = DeploymentAPIClient(api_url)


@cli.command()
@click.pass_context
def health(ctx):
    """Check API and services health"""
    client = ctx.obj['client']
    
    # Check API health
    console.print(Panel.fit("🏥 Health Check", style="bold blue"))
    
    try:
        api_health = client.health_check()
        console.print(f"[green]✅ API Status: {api_health['status']}[/green]")
        console.print(f"   Version: {api_health['version']}")
        console.print(f"   Time: {api_health['timestamp']}")
    except:
        console.print("[red]❌ API is not responding[/red]")
        return
    
    # Check services
    console.print("\n[bold]Service Health:[/bold]")
    
    try:
        services = client.check_services()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Health", style="green")
        table.add_column("Message")
        
        for service in services:
            health_icon = "✅" if service['healthy'] else "❌"
            table.add_row(
                service['service'],
                service['status'],
                health_icon,
                service.get('message', '')
            )
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error checking services: {e}[/red]")


@cli.command()
@click.option('--services', '-s', multiple=True, default=['postgres', 'redis'], help='Services to deploy')
@click.option('--regions', '-r', multiple=True, default=['us-east', 'eu-west'], help='Regions to deploy')
@click.option('--skip-migrations', is_flag=True, help='Skip running migrations')
@click.option('--watch', '-w', is_flag=True, help='Watch deployment progress')
@click.pass_context
def deploy(ctx, services, regions, skip_migrations, watch):
    """Deploy infrastructure services"""
    client = ctx.obj['client']
    
    console.print(Panel.fit("🚀 Deploying Infrastructure", style="bold blue"))
    console.print(f"Services: {', '.join(services)}")
    console.print(f"Regions: {', '.join(regions)}")
    console.print(f"Skip Migrations: {skip_migrations}")
    
    try:
        deployment = client.deploy(list(services), list(regions), skip_migrations)
        console.print(f"\n[green]✅ Deployment started[/green]")
        console.print(f"Deployment ID: {deployment['deployment_id']}")
        
        if watch:
            # Watch deployment progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Deploying...", total=None)
                
                while True:
                    status = client.get_deployment(deployment['deployment_id'])
                    
                    if status['status'] in ['completed', 'failed', 'rolled_back']:
                        break
                    
                    progress.update(task, description=f"Status: {status['status']}")
                    time.sleep(2)
            
            # Final status
            if status['status'] == 'completed':
                console.print(f"[green]✅ Deployment completed successfully[/green]")
            else:
                console.print(f"[red]❌ Deployment {status['status']}[/red]")
                if status.get('errors'):
                    for error in status['errors']:
                        console.print(f"   - {error}")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--status', '-s', help='Filter by status')
@click.option('--limit', '-l', default=10, help='Number of deployments to show')
@click.pass_context
def deployments(ctx, status, limit):
    """List deployments"""
    client = ctx.obj['client']
    
    console.print(Panel.fit("📋 Deployments", style="bold blue"))
    
    try:
        deployments = client.list_deployments(status, limit)
        
        if not deployments:
            console.print("[yellow]No deployments found[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="yellow")
        table.add_column("Started", style="green")
        table.add_column("Completed")
        table.add_column("Services")
        
        for deployment in deployments:
            completed = deployment.get('completed_at', '-')
            if completed != '-':
                completed = datetime.fromisoformat(completed).strftime('%Y-%m-%d %H:%M:%S')
            
            services = ', '.join(deployment.get('services_deployed', []))
            
            table.add_row(
                deployment['deployment_id'][:8],
                deployment['status'],
                datetime.fromisoformat(deployment['started_at']).strftime('%Y-%m-%d %H:%M:%S'),
                completed,
                services or '-'
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--scope', '-s', default='all', type=click.Choice(['all', 'admin', 'regional', 'tenant', 'single']))
@click.option('--database', '-d', help='Database name (for single scope)')
@click.option('--schema', default='public', help='Schema name (for single scope)')
@click.option('--batch-size', '-b', default=10, help='Batch size for tenant migrations')
@click.option('--watch', '-w', is_flag=True, help='Watch migration progress')
@click.pass_context
def migrate(ctx, scope, database, schema, batch_size, watch):
    """Apply database migrations"""
    client = ctx.obj['client']
    
    console.print(Panel.fit("🔄 Applying Migrations", style="bold blue"))
    console.print(f"Scope: {scope}")
    
    if scope == 'single':
        if not database:
            console.print("[red]Database required for single migration[/red]")
            return
        console.print(f"Database: {database}")
        console.print(f"Schema: {schema}")
    
    try:
        migration = client.apply_migrations(scope, batch_size)
        console.print(f"\n[green]✅ Migration started[/green]")
        console.print(f"Migration ID: {migration['migration_id']}")
        
        if watch:
            # Watch migration progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Migrating...", total=None)
                
                while migration['status'] in ['pending', 'in_progress']:
                    time.sleep(2)
                    # In real implementation, would fetch status from API
                    progress.update(task, description=f"Status: {migration['status']}")
            
            # Final status
            if migration['status'] == 'completed':
                console.print(f"[green]✅ Migration completed[/green]")
                console.print(f"   Databases: {migration.get('databases_migrated', 0)}")
                console.print(f"   Schemas: {migration.get('schemas_migrated', 0)}")
            else:
                console.print(f"[red]❌ Migration failed[/red]")
                if migration.get('errors'):
                    for error in migration['errors']:
                        console.print(f"   - {error}")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--database', '-d', help='Specific database')
@click.option('--schema', '-s', default='public', help='Specific schema')
@click.pass_context
def status(ctx, database, schema):
    """Show migration status"""
    client = ctx.obj['client']
    
    console.print(Panel.fit("📊 Migration Status", style="bold blue"))
    
    try:
        if database:
            # Get specific status
            status = client.get_migration_status(database, schema)
            
            console.print(f"\n[bold]Database:[/bold] {status['database']}")
            console.print(f"[bold]Schema:[/bold] {status['schema']}")
            console.print(f"[bold]Current Version:[/bold] {status['current_version']}")
            console.print(f"[bold]Pending Migrations:[/bold] {len(status['pending_migrations'])}")
            console.print(f"[bold]Status:[/bold] {status['status']}")
            
            if status['last_migration_date']:
                console.print(f"[bold]Last Migration:[/bold] {status['last_migration_date']}")
            
            if status['pending_migrations']:
                console.print("\n[bold]Pending Migrations:[/bold]")
                for migration in status['pending_migrations']:
                    console.print(f"   - {migration}")
        else:
            # Get dashboard
            dashboard = client.get_migration_dashboard()
            
            console.print(f"\n[bold]Total Databases:[/bold] {dashboard['total_databases']}")
            console.print(f"[bold]Pending Migrations:[/bold] {dashboard['pending_migrations']}")
            console.print(f"[bold]Active Migrations:[/bold] {dashboard['active_migrations']}")
            
            if dashboard['recent_migrations']:
                console.print("\n[bold]Recent Migrations:[/bold]")
                
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Database", style="cyan")
                table.add_column("Schema", style="yellow")
                table.add_column("Status", style="green")
                table.add_column("Completed")
                
                for migration in dashboard['recent_migrations']:
                    completed = migration.get('completed_at', '-')
                    if completed != '-':
                        completed = datetime.fromisoformat(completed).strftime('%Y-%m-%d %H:%M:%S')
                    
                    table.add_row(
                        migration['database_name'],
                        migration['schema_name'],
                        migration['status'],
                        completed
                    )
                
                console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.argument('tenant_id')
@click.option('--slug', '-s', required=True, help='Tenant slug')
@click.option('--database', '-d', required=True, help='Database name')
@click.option('--schema', required=True, help='Schema name')
@click.pass_context
def migrate_tenant(ctx, tenant_id, slug, database, schema):
    """Migrate a tenant schema"""
    client = ctx.obj['client']
    
    console.print(Panel.fit(f"Migrating Tenant: {slug}", style="bold blue"))
    
    try:
        result = client.migrate_tenant(tenant_id, slug, database, schema)
        console.print(f"[green]✅ Tenant migration started[/green]")
        console.print(f"Migration ID: {result['migration_id']}")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--database', '-d', required=True, help='Database name')
@click.option('--schema', '-s', default='public', help='Schema name')
@click.option('--version', '-v', required=True, help='Target version')
@click.option('--execute', is_flag=True, help='Execute rollback (default is dry run)')
@click.pass_context
def rollback(ctx, database, schema, version, execute):
    """Rollback migration to specific version"""
    client = ctx.obj['client']
    
    mode = "EXECUTE" if execute else "DRY RUN"
    console.print(Panel.fit(f"⏪ Rollback Migration ({mode})", style="bold yellow"))
    console.print(f"Database: {database}")
    console.print(f"Schema: {schema}")
    console.print(f"Target Version: {version}")
    
    if execute:
        if not click.confirm("\n⚠️  This will rollback the database. Are you sure?"):
            console.print("[yellow]Rollback cancelled[/yellow]")
            return
    
    try:
        result = client.rollback_migration(database, schema, version, dry_run=not execute)
        
        if result['status'] == 'success':
            console.print(f"[green]✅ {result['message']}[/green]")
        else:
            console.print(f"[red]❌ Rollback failed[/red]")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.pass_context
def interactive(ctx):
    """Interactive mode"""
    console.print(Panel.fit("🎮 Interactive Mode", style="bold blue"))
    console.print("Type 'help' for available commands, 'exit' to quit\n")
    
    client = ctx.obj['client']
    
    commands = {
        'health': lambda: ctx.invoke(health),
        'deploy': lambda: ctx.invoke(deploy),
        'migrate': lambda: ctx.invoke(migrate),
        'status': lambda: ctx.invoke(status),
        'deployments': lambda: ctx.invoke(deployments),
        'help': lambda: console.print("""
Available commands:
  health      - Check health status
  deploy      - Deploy infrastructure
  migrate     - Apply migrations
  status      - Show migration status
  deployments - List deployments
  exit        - Exit interactive mode
        """.strip())
    }
    
    while True:
        try:
            command = console.input("[bold cyan]neo>[/bold cyan] ").strip().lower()
            
            if command == 'exit':
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if command in commands:
                commands[command]()
            elif command:
                console.print(f"[red]Unknown command: {command}[/red]")
                console.print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == '__main__':
    cli()