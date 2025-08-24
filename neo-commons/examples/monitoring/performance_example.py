"""Performance monitoring examples and usage patterns.

This module demonstrates how to apply performance monitoring decorators
to existing neo-commons code for bottleneck identification.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from neo_commons.infrastructure.monitoring import (
    critical_performance, high_performance, medium_performance,
    performance_timer, get_performance_monitor
)


# Example: Database operation monitoring
@critical_performance(name="database.query_execution", include_args=True)
async def execute_database_query(query: str, params: tuple = ()) -> list:
    """Example database query with critical performance monitoring."""
    # Simulate database query execution
    await asyncio.sleep(0.05)  # 50ms simulation
    return [{"id": 1, "name": "test"}]


# Example: Business logic monitoring
@high_performance(name="business.permission_check")
async def check_user_permissions(user_id: str, resource: str, action: str) -> bool:
    """Example permission checking with high performance monitoring."""
    # Simulate permission checking logic
    await asyncio.sleep(0.02)  # 20ms simulation
    return True


# Example: Service method monitoring  
@medium_performance(name="service.organization_service")
async def create_organization(name: str, email: str) -> dict:
    """Example organization creation with medium performance monitoring."""
    # Simulate organization creation
    await asyncio.sleep(0.01)  # 10ms simulation
    return {"id": "org-123", "name": name, "email": email}


# Example: Context manager usage
async def complex_operation_example():
    """Example of using performance timer context manager."""
    
    with performance_timer("complex.multi_step_operation"):
        # Step 1: Database lookup
        with performance_timer("complex.step1_db_lookup"):
            await asyncio.sleep(0.03)
        
        # Step 2: Business logic
        with performance_timer("complex.step2_business_logic"):
            await asyncio.sleep(0.02)
        
        # Step 3: External API call
        with performance_timer("complex.step3_api_call"):
            await asyncio.sleep(0.04)


# Example: Repository pattern with performance monitoring
class MonitoredOrganizationRepository:
    """Example repository with performance monitoring decorators."""
    
    @critical_performance(name="repo.organization.create")
    async def create(self, organization_data: dict) -> dict:
        """Create organization with performance monitoring."""
        await asyncio.sleep(0.08)  # 80ms database operation
        return {"id": "new-org", **organization_data}
    
    @critical_performance(name="repo.organization.get_by_id")
    async def get_by_id(self, org_id: str) -> dict:
        """Get organization by ID with performance monitoring."""
        await asyncio.sleep(0.03)  # 30ms database query
        return {"id": org_id, "name": "Example Org"}
    
    @medium_performance(name="repo.organization.list")
    async def list_organizations(self, limit: int = 50) -> list:
        """List organizations with performance monitoring."""
        await asyncio.sleep(0.02)  # 20ms query
        return [{"id": f"org-{i}", "name": f"Org {i}"} for i in range(limit)]


# Example: Service layer with performance monitoring
class MonitoredOrganizationService:
    """Example service with comprehensive performance monitoring."""
    
    def __init__(self):
        self.repository = MonitoredOrganizationRepository()
    
    @high_performance(name="service.organization.create_with_validation")
    async def create_organization(self, org_data: dict) -> dict:
        """Create organization with validation and monitoring."""
        
        # Validation step
        with performance_timer("service.validation.organization_data"):
            await self._validate_organization_data(org_data)
        
        # Repository operation
        result = await self.repository.create(org_data)
        
        # Post-creation tasks
        with performance_timer("service.post_creation.notifications"):
            await self._send_creation_notifications(result)
        
        return result
    
    @medium_performance(name="service.validation.organization_data")
    async def _validate_organization_data(self, data: dict) -> None:
        """Validate organization data."""
        await asyncio.sleep(0.01)  # 10ms validation
    
    @medium_performance(name="service.notifications.send_creation")
    async def _send_creation_notifications(self, org_data: dict) -> None:
        """Send creation notifications."""
        await asyncio.sleep(0.015)  # 15ms notification sending


async def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring capabilities."""
    print("🚀 Starting performance monitoring demonstration...")
    
    monitor = get_performance_monitor()
    
    # Test different operations
    await execute_database_query("SELECT * FROM users", ("param1",))
    await check_user_permissions("user-123", "organizations", "read")
    await create_organization("Test Org", "test@example.com")
    await complex_operation_example()
    
    # Test service operations
    service = MonitoredOrganizationService()
    await service.create_organization({"name": "New Organization", "email": "new@org.com"})
    
    # Get performance statistics
    print("\n📊 Performance Statistics:")
    print("-" * 50)
    
    stats = monitor.get_stats()
    for operation_name, stat in stats.items():
        print(f"Operation: {operation_name}")
        print(f"  Calls: {stat.call_count}")
        print(f"  Avg Time: {stat.avg_time_ms:.2f}ms")
        print(f"  Min/Max: {stat.min_time_ms:.2f}ms / {stat.max_time_ms:.2f}ms")
        print(f"  Threshold Violations: {stat.threshold_violations}")
        print()
    
    # Check for bottlenecks
    bottlenecks = monitor.get_bottlenecks()
    if bottlenecks:
        print("🐌 Identified Bottlenecks:")
        print("-" * 30)
        for bottleneck in bottlenecks[:3]:  # Top 3 bottlenecks
            print(f"  {bottleneck.operation_name}: {bottleneck.avg_time_ms:.2f}ms avg")
    
    # Performance summary
    summary = monitor.get_summary()
    print(f"\n📈 Monitoring Summary:")
    print(f"  Total Operations: {summary['total_operations']}")
    print(f"  Total Calls: {summary['total_calls']}")
    print(f"  Threshold Violations: {summary['threshold_violations']}")
    print(f"  Identified Bottlenecks: {summary['bottlenecks']}")


if __name__ == "__main__":
    asyncio.run(demonstrate_performance_monitoring())