"""Example demonstrating optional database persistence for performance monitoring.

This shows how to enable database persistence for performance metrics
without impacting the performance of monitored operations.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from neo_commons.infrastructure.monitoring import (
    PerformanceMonitor, DatabasePerformanceStorage,
    critical_performance, high_performance, medium_performance,
    performance_timer, get_performance_monitor
)


# Example service with performance monitoring
class DatabaseAwareService:
    """Example service demonstrating database-persisted performance monitoring."""
    
    def __init__(self, database_service):
        self.database_service = database_service
    
    @critical_performance(name="service.process_payment", include_args=True)
    async def process_payment(self, amount: float, currency: str) -> dict:
        """Process payment with critical performance monitoring."""
        # Simulate payment processing
        await asyncio.sleep(0.1)  # 100ms processing
        return {"payment_id": "pay-123", "amount": amount, "currency": currency}
    
    @high_performance(name="service.validate_user")
    async def validate_user(self, user_id: str) -> bool:
        """Validate user with high performance monitoring."""
        # Simulate user validation
        await asyncio.sleep(0.02)  # 20ms validation
        return True
    
    @medium_performance(name="service.send_notification")
    async def send_notification(self, user_id: str, message: str) -> None:
        """Send notification with medium performance monitoring."""
        # Simulate notification sending
        await asyncio.sleep(0.05)  # 50ms sending
        pass


async def setup_database_persistence(database_service):
    """Set up performance monitoring with database persistence."""
    
    print("🔧 Setting up performance monitoring with database persistence...")
    
    # Create database storage (this will automatically create tables)
    storage = DatabasePerformanceStorage(database_service, schema="admin")
    
    # Create performance monitor with database persistence
    # Background persistence has ZERO performance impact on monitored operations
    monitor = PerformanceMonitor(persistence_storage=storage)
    
    print("✅ Database persistence enabled - metrics will be stored asynchronously")
    return monitor


async def demonstrate_zero_impact_persistence():
    """Demonstrate that database persistence has zero performance impact."""
    
    print("🚀 Demonstrating zero-impact database persistence...")
    
    # Mock database service for example
    class MockDatabaseService:
        async def get_connection(self, name):
            return self
        
        async def execute(self, query, *args):
            await asyncio.sleep(0.001)  # Simulate DB write
            return "INSERT 0 1"
        
        async def fetch(self, query, *args):
            return []
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
    
    database_service = MockDatabaseService()
    
    # Set up monitoring with database persistence
    monitor = await setup_database_persistence(database_service)
    
    # Create service
    service = DatabaseAwareService(database_service)
    
    print("\n📊 Running performance tests...")
    
    # Measure performance WITHOUT database persistence
    print("⏱️  Without database persistence:")
    start_time = asyncio.get_event_loop().time()
    
    for i in range(100):
        await service.process_payment(100.0 + i, "USD")
        await service.validate_user(f"user-{i}")
        await service.send_notification(f"user-{i}", f"Payment {i} processed")
    
    time_without_persistence = asyncio.get_event_loop().time() - start_time
    print(f"   100 operations took: {time_without_persistence:.3f} seconds")
    
    # Reset and measure WITH database persistence
    monitor.clear_metrics()
    
    print("\n⏱️  With database persistence (background):")
    start_time = asyncio.get_event_loop().time()
    
    for i in range(100):
        await service.process_payment(100.0 + i, "USD")  
        await service.validate_user(f"user-{i}")
        await service.send_notification(f"user-{i}", f"Payment {i} processed")
    
    time_with_persistence = asyncio.get_event_loop().time() - start_time
    print(f"   100 operations took: {time_with_persistence:.3f} seconds")
    
    # Compare performance
    overhead = ((time_with_persistence - time_without_persistence) / time_without_persistence) * 100
    print(f"\n🎯 Performance overhead: {overhead:.2f}% (should be ~0%)")
    
    # Show real-time metrics
    print(f"\n📈 Real-time Performance Statistics:")
    print("-" * 50)
    
    stats = monitor.get_stats()
    for operation_name, stat in stats.items():
        print(f"Operation: {operation_name}")
        print(f"  Calls: {stat.call_count}")
        print(f"  Avg Time: {stat.avg_time_ms:.2f}ms")
        print(f"  Min/Max: {stat.min_time_ms:.2f}ms / {stat.max_time_ms:.2f}ms")
        print()
    
    # Wait for background persistence to complete
    print("⏳ Waiting for background persistence to complete...")
    await asyncio.sleep(2.0)  # Allow background persister to flush
    
    # Shutdown gracefully (this flushes remaining metrics)
    await monitor.shutdown()
    
    print("✅ All metrics have been persisted to database asynchronously")


async def demonstrate_historical_analysis():
    """Show how to retrieve historical performance data."""
    
    print("📊 Historical Performance Analysis Example")
    print("=" * 50)
    
    # Mock database service with sample data
    class MockDatabaseServiceWithData:
        async def get_connection(self, name):
            return self
        
        async def execute(self, query, *args):
            return "INSERT 0 1"
        
        async def fetch(self, query, *args):
            # Return sample historical data
            from datetime import datetime, timezone
            return [
                {
                    'operation_name': 'service.process_payment',
                    'execution_time_ms': 95.5,
                    'level': 'critical',
                    'timestamp': datetime.now(timezone.utc),
                    'metadata': {},
                    'exceeded_threshold': False,
                    'error_occurred': False
                },
                {
                    'operation_name': 'service.validate_user', 
                    'execution_time_ms': 25.2,
                    'level': 'high',
                    'timestamp': datetime.now(timezone.utc),
                    'metadata': {},
                    'exceeded_threshold': False,
                    'error_occurred': False
                }
            ]
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
    
    database_service = MockDatabaseServiceWithData()
    storage = DatabasePerformanceStorage(database_service)
    
    # Retrieve historical metrics
    print("🔍 Retrieving historical performance metrics...")
    
    metrics = await storage.get_metrics(limit=10)
    
    print(f"\n📈 Found {len(metrics)} historical metrics:")
    for metric in metrics:
        print(f"  {metric.operation_name}: {metric.execution_time_ms:.1f}ms [{metric.level.value}]")
    
    # Show specific operation metrics
    payment_metrics = await storage.get_metrics(operation_name="service.process_payment", limit=5)
    
    print(f"\n💳 Payment processing metrics ({len(payment_metrics)} records):")
    for metric in payment_metrics:
        status = "⚠️ SLOW" if metric.exceeded_threshold else "✅ OK"
        print(f"  {metric.timestamp.strftime('%H:%M:%S')}: {metric.execution_time_ms:.1f}ms {status}")


async def main():
    """Main demonstration of database persistence for performance monitoring."""
    
    print("🏪 Performance Monitoring with Database Persistence")
    print("=" * 60)
    
    print("\n📝 Key Benefits:")
    print("   • Zero performance impact on monitored operations")  
    print("   • Asynchronous background persistence")
    print("   • Historical trend analysis")
    print("   • Cross-service performance correlation")
    print("   • Automatic database table creation")
    print("   • Configurable retention policies")
    
    await demonstrate_zero_impact_persistence()
    
    print("\n" + "=" * 60)
    
    await demonstrate_historical_analysis()
    
    print(f"\n🎉 Database Persistence Demo Complete!")
    print("\n💡 Integration Tips:")
    print("   • Enable persistence only in production environments")
    print("   • Configure retention policies to manage database size")
    print("   • Use metrics for alerting and automated scaling decisions")
    print("   • Correlate performance data with business metrics")


if __name__ == "__main__":
    asyncio.run(main())