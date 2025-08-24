"""Connection pool optimization based on saturation metrics and performance data.

This module provides intelligent pool optimization using performance metrics,
machine learning algorithms, and adaptive sizing strategies.
"""

import asyncio
import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import math

from ..entities.protocols import ConnectionRegistry, ConnectionManager
from ..entities.database_connection import DatabaseConnection
from .connection_manager import PoolMetrics

logger = logging.getLogger(__name__)


class OptimizationStrategy(str, Enum):
    """Pool optimization strategies."""
    CONSERVATIVE = "conservative"  # Slow, safe changes
    BALANCED = "balanced"  # Moderate optimization
    AGGRESSIVE = "aggressive"  # Fast adaptation
    PERFORMANCE = "performance"  # Optimize for speed
    COST = "cost"  # Optimize for resource usage


@dataclass
class OptimizationTarget:
    """Optimization targets and constraints."""
    max_response_time_ms: float = 100.0  # Target response time
    min_success_rate: float = 99.0  # Minimum success rate
    max_saturation_level: float = 0.8  # Maximum saturation before scaling
    target_efficiency: float = 0.7  # Target pool efficiency
    max_pool_size: int = 50  # Hard limit on pool size
    min_pool_size: int = 2  # Minimum pool size
    cost_per_connection: float = 1.0  # Cost weight for connections
    performance_weight: float = 0.7  # Performance vs cost weight


@dataclass
class PoolOptimizationDecision:
    """Pool optimization decision with reasoning."""
    connection_name: str
    current_pool_size: int
    recommended_pool_size: int
    confidence: float  # 0.0 to 1.0
    reasoning: List[str]
    expected_improvement: Dict[str, float]
    risk_level: str  # low, medium, high
    estimated_cost_impact: float  # Cost change percentage
    should_apply: bool = True


@dataclass
class PerformanceHistory:
    """Historical performance data for trend analysis."""
    timestamps: List[datetime] = field(default_factory=list)
    response_times: List[float] = field(default_factory=list)
    saturation_levels: List[float] = field(default_factory=list) 
    pool_sizes: List[int] = field(default_factory=list)
    success_rates: List[float] = field(default_factory=list)
    queries_per_second: List[float] = field(default_factory=list)
    
    def add_sample(self, metrics: PoolMetrics, pool_size: int):
        """Add performance sample to history."""
        now = datetime.utcnow()
        self.timestamps.append(now)
        self.response_times.append(metrics.avg_response_time_ms)
        self.saturation_levels.append(metrics.saturation_level)
        self.pool_sizes.append(pool_size)
        self.success_rates.append(metrics.query_success_rate)
        self.queries_per_second.append(metrics.queries_per_second)
        
        # Keep last 100 samples (about 50 minutes of 30-second intervals)
        max_samples = 100
        if len(self.timestamps) > max_samples:
            self.timestamps = self.timestamps[-max_samples:]
            self.response_times = self.response_times[-max_samples:]
            self.saturation_levels = self.saturation_levels[-max_samples:]
            self.pool_sizes = self.pool_sizes[-max_samples:]
            self.success_rates = self.success_rates[-max_samples:]
            self.queries_per_second = self.queries_per_second[-max_samples:]


class ConnectionPoolOptimizer:
    """Intelligent connection pool optimizer using performance metrics."""
    
    def __init__(self, 
                 connection_manager: ConnectionManager,
                 connection_registry: ConnectionRegistry,
                 optimization_interval: int = 300,  # 5 minutes
                 strategy: OptimizationStrategy = OptimizationStrategy.BALANCED):
        """Initialize pool optimizer.
        
        Args:
            connection_manager: Connection manager for pool access
            connection_registry: Registry for connection information  
            optimization_interval: Seconds between optimization runs
            strategy: Optimization strategy to use
        """
        self.connection_manager = connection_manager
        self.connection_registry = connection_registry
        self.optimization_interval = optimization_interval
        self.strategy = strategy
        
        # Optimization state
        self.targets = OptimizationTarget()
        self.performance_history: Dict[str, PerformanceHistory] = {}
        self.last_optimization: Dict[str, datetime] = {}
        self.optimization_lock = asyncio.Lock()
        
        # Monitoring
        self._optimization_task: Optional[asyncio.Task] = None
        self._stop_optimization = False
        
        # Statistics
        self.optimizations_applied = 0
        self.total_optimizations_considered = 0
        self.performance_improvements = 0
        
    async def start_optimization(self) -> None:
        """Start continuous pool optimization."""
        if self._optimization_task is not None:
            return
        
        self._stop_optimization = False
        self._optimization_task = asyncio.create_task(self._optimization_loop())
        logger.info(f"Started connection pool optimization with {self.strategy.value} strategy")
    
    async def stop_optimization(self) -> None:
        """Stop pool optimization."""
        self._stop_optimization = True
        
        if self._optimization_task and not self._optimization_task.done():
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped connection pool optimization")
    
    async def _optimization_loop(self) -> None:
        """Main optimization loop."""
        while not self._stop_optimization:
            try:
                await self._run_optimization_cycle()
                await asyncio.sleep(self.optimization_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pool optimization loop: {e}")
                await asyncio.sleep(min(self.optimization_interval, 60))
    
    async def _run_optimization_cycle(self) -> None:
        """Run a single optimization cycle for all pools."""
        async with self.optimization_lock:
            try:
                # Get all active connections
                connections = await self.connection_registry.list_connections(active_only=True)
                
                optimization_results = []
                
                for connection in connections:
                    try:
                        # Get pool metrics
                        pool = await self.connection_manager.get_pool(connection.connection_name)
                        metrics = await pool.get_stats()
                        
                        # Update performance history
                        await self._update_performance_history(connection.connection_name, metrics, pool.size)
                        
                        # Analyze and optimize pool
                        decision = await self._analyze_pool_optimization(connection, metrics)
                        
                        if decision and decision.should_apply:
                            await self._apply_optimization(decision)
                            optimization_results.append(decision)
                        
                        self.total_optimizations_considered += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to optimize pool {connection.connection_name}: {e}")
                        continue
                
                if optimization_results:
                    logger.info(f"Applied {len(optimization_results)} pool optimizations")
                    
            except Exception as e:
                logger.error(f"Error in optimization cycle: {e}")
    
    async def _update_performance_history(self, connection_name: str, metrics: PoolMetrics, pool_size: int) -> None:
        """Update performance history for trend analysis."""
        if connection_name not in self.performance_history:
            self.performance_history[connection_name] = PerformanceHistory()
        
        self.performance_history[connection_name].add_sample(metrics, pool_size)
    
    async def _analyze_pool_optimization(self, connection: DatabaseConnection, metrics: PoolMetrics) -> Optional[PoolOptimizationDecision]:
        """Analyze pool performance and recommend optimization."""
        current_size = metrics.total_connections
        connection_name = connection.connection_name
        
        # Initialize decision
        decision = PoolOptimizationDecision(
            connection_name=connection_name,
            current_pool_size=current_size,
            recommended_pool_size=current_size,
            confidence=0.0,
            reasoning=[],
            expected_improvement={},
            risk_level="low",
            estimated_cost_impact=0.0
        )
        
        # Analyze current performance
        performance_issues = await self._identify_performance_issues(metrics)
        capacity_analysis = await self._analyze_capacity_requirements(connection_name, metrics)
        trend_analysis = await self._analyze_performance_trends(connection_name)
        
        # Determine optimization strategy
        if performance_issues:
            decision = await self._optimize_for_performance(decision, metrics, performance_issues)
        elif capacity_analysis.get("underutilized", False):
            decision = await self._optimize_for_cost(decision, metrics, capacity_analysis)
        elif trend_analysis.get("growth_trend", False):
            decision = await self._optimize_for_growth(decision, metrics, trend_analysis)
        else:
            # No optimization needed
            decision.should_apply = False
            decision.reasoning.append("Performance within acceptable parameters")
        
        return decision
    
    async def _identify_performance_issues(self, metrics: PoolMetrics) -> List[str]:
        """Identify current performance issues."""
        issues = []
        
        # High response time
        if metrics.avg_response_time_ms > self.targets.max_response_time_ms:
            issues.append(f"High response time: {metrics.avg_response_time_ms:.1f}ms > {self.targets.max_response_time_ms}ms")
        
        # High saturation
        if metrics.saturation_level > self.targets.max_saturation_level:
            issues.append(f"High saturation: {metrics.saturation_level:.2f} > {self.targets.max_saturation_level}")
        
        # Low success rate
        if metrics.query_success_rate < self.targets.min_success_rate:
            issues.append(f"Low success rate: {metrics.query_success_rate:.1f}% < {self.targets.min_success_rate}%")
        
        # High acquisition timeouts
        if metrics.acquisition_timeouts > 0:
            issues.append(f"Connection acquisition timeouts: {metrics.acquisition_timeouts}")
        
        # Poor efficiency
        if metrics.pool_efficiency < 0.3 and metrics.total_connections > self.targets.min_pool_size:
            issues.append(f"Low pool efficiency: {metrics.pool_efficiency:.2f}")
        
        return issues
    
    async def _analyze_capacity_requirements(self, connection_name: str, metrics: PoolMetrics) -> Dict[str, Any]:
        """Analyze capacity requirements and utilization."""
        analysis = {
            "current_utilization": metrics.pool_efficiency,
            "peak_utilization": 0.0,
            "underutilized": False,
            "overloaded": False,
            "optimal_size": metrics.total_connections
        }
        
        # Check historical utilization if available
        if connection_name in self.performance_history:
            history = self.performance_history[connection_name]
            
            if len(history.saturation_levels) >= 5:
                recent_saturation = history.saturation_levels[-10:]  # Last 10 samples
                avg_saturation = statistics.mean(recent_saturation)
                peak_saturation = max(recent_saturation)
                
                analysis["peak_utilization"] = peak_saturation
                
                # Underutilized if consistently low saturation
                if avg_saturation < 0.3 and metrics.total_connections > self.targets.min_pool_size:
                    analysis["underutilized"] = True
                    # Recommend 25% reduction, but keep minimum
                    analysis["optimal_size"] = max(
                        self.targets.min_pool_size,
                        int(metrics.total_connections * 0.75)
                    )
                
                # Overloaded if frequently high saturation
                elif avg_saturation > 0.8 or peak_saturation > 0.9:
                    analysis["overloaded"] = True
                    # Recommend 25-50% increase based on severity
                    multiplier = 1.25 if peak_saturation < 0.95 else 1.5
                    analysis["optimal_size"] = min(
                        self.targets.max_pool_size,
                        int(metrics.total_connections * multiplier)
                    )
        
        return analysis
    
    async def _analyze_performance_trends(self, connection_name: str) -> Dict[str, Any]:
        """Analyze performance trends for predictive optimization."""
        trends = {
            "growth_trend": False,
            "degradation_trend": False,
            "stable": True,
            "predicted_load": 1.0
        }
        
        if connection_name not in self.performance_history:
            return trends
        
        history = self.performance_history[connection_name]
        
        # Need at least 10 samples for trend analysis
        if len(history.queries_per_second) < 10:
            return trends
        
        # Analyze query load trend
        recent_qps = history.queries_per_second[-10:]
        older_qps = history.queries_per_second[-20:-10] if len(history.queries_per_second) >= 20 else recent_qps
        
        if older_qps:
            recent_avg = statistics.mean(recent_qps)
            older_avg = statistics.mean(older_qps)
            
            growth_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            
            # Significant growth trend (>20% increase)
            if growth_rate > 0.2:
                trends["growth_trend"] = True
                trends["stable"] = False
                trends["predicted_load"] = 1 + growth_rate
            
            # Performance degradation trend
            recent_response_times = history.response_times[-10:]
            older_response_times = history.response_times[-20:-10] if len(history.response_times) >= 20 else recent_response_times
            
            if older_response_times:
                recent_rt_avg = statistics.mean(recent_response_times)
                older_rt_avg = statistics.mean(older_response_times)
                
                rt_degradation = (recent_rt_avg - older_rt_avg) / older_rt_avg if older_rt_avg > 0 else 0
                
                if rt_degradation > 0.3:  # >30% response time increase
                    trends["degradation_trend"] = True
                    trends["stable"] = False
        
        return trends
    
    async def _optimize_for_performance(self, decision: PoolOptimizationDecision, metrics: PoolMetrics, issues: List[str]) -> PoolOptimizationDecision:
        """Optimize pool for performance improvement."""
        current_size = decision.current_pool_size
        
        # Calculate size increase based on issues severity
        size_multiplier = 1.0
        
        # High response time or saturation - increase pool size
        if metrics.avg_response_time_ms > self.targets.max_response_time_ms * 2:
            size_multiplier = 1.5  # Significant increase
            decision.risk_level = "medium"
        elif metrics.saturation_level > 0.9:
            size_multiplier = 1.4  # Moderate increase
            decision.risk_level = "medium"
        elif metrics.acquisition_timeouts > 0:
            size_multiplier = 1.3  # Conservative increase
            decision.risk_level = "low"
        else:
            size_multiplier = 1.2  # Small increase
        
        # Apply strategy modifiers
        if self.strategy == OptimizationStrategy.CONSERVATIVE:
            size_multiplier = min(size_multiplier, 1.2)
        elif self.strategy == OptimizationStrategy.AGGRESSIVE:
            size_multiplier *= 1.2
        
        # Calculate new size
        new_size = min(self.targets.max_pool_size, int(current_size * size_multiplier))
        
        decision.recommended_pool_size = new_size
        decision.confidence = 0.8 if len(issues) >= 2 else 0.6
        decision.reasoning = issues + [f"Increasing pool size {current_size} → {new_size} for performance"]
        decision.estimated_cost_impact = ((new_size - current_size) / current_size) * 100
        
        # Expected improvements
        decision.expected_improvement = {
            "response_time_reduction": 20.0,  # % reduction
            "saturation_reduction": 15.0,
            "success_rate_increase": 2.0
        }
        
        return decision
    
    async def _optimize_for_cost(self, decision: PoolOptimizationDecision, metrics: PoolMetrics, analysis: Dict[str, Any]) -> PoolOptimizationDecision:
        """Optimize pool for cost reduction."""
        current_size = decision.current_pool_size
        optimal_size = analysis["optimal_size"]
        
        # Only reduce if it won't impact performance significantly
        if optimal_size < current_size:
            decision.recommended_pool_size = optimal_size
            decision.confidence = 0.7
            decision.reasoning = [
                f"Pool underutilized (efficiency: {metrics.pool_efficiency:.2f})",
                f"Reducing pool size {current_size} → {optimal_size} for cost savings"
            ]
            decision.estimated_cost_impact = -((current_size - optimal_size) / current_size) * 100
            decision.risk_level = "low"
            
            decision.expected_improvement = {
                "cost_reduction": abs(decision.estimated_cost_impact),
                "efficiency_increase": 10.0
            }
        else:
            decision.should_apply = False
            decision.reasoning = ["Pool size already optimal"]
        
        return decision
    
    async def _optimize_for_growth(self, decision: PoolOptimizationDecision, metrics: PoolMetrics, trends: Dict[str, Any]) -> PoolOptimizationDecision:
        """Optimize pool for predicted growth."""
        current_size = decision.current_pool_size
        predicted_load = trends["predicted_load"]
        
        # Proactively increase pool size based on predicted load
        size_multiplier = min(predicted_load * 1.1, 1.5)  # Add 10% buffer, max 50% increase
        new_size = min(self.targets.max_pool_size, int(current_size * size_multiplier))
        
        decision.recommended_pool_size = new_size
        decision.confidence = 0.6  # Lower confidence for predictive changes
        decision.reasoning = [
            f"Growth trend detected (load increase: {(predicted_load-1)*100:.1f}%)",
            f"Proactively increasing pool size {current_size} → {new_size}"
        ]
        decision.estimated_cost_impact = ((new_size - current_size) / current_size) * 100
        decision.risk_level = "medium"
        
        decision.expected_improvement = {
            "future_performance_protection": 25.0,
            "growth_accommodation": predicted_load * 100
        }
        
        return decision
    
    async def _apply_optimization(self, decision: PoolOptimizationDecision) -> None:
        """Apply optimization decision to the pool."""
        try:
            connection_name = decision.connection_name
            new_size = decision.recommended_pool_size
            
            # Get the connection configuration
            connection = await self.connection_registry.get_connection_by_name(connection_name)
            if not connection:
                logger.error(f"Connection {connection_name} not found for optimization")
                return
            
            # Update pool configuration
            connection.pool_max_size = new_size
            # Also adjust min_size proportionally, but keep reasonable ratio
            min_ratio = 0.3  # Minimum 30% of max
            connection.pool_min_size = max(
                self.targets.min_pool_size,
                int(new_size * min_ratio)
            )
            
            # Update the connection in registry
            await self.connection_registry.update_connection(connection)
            
            # Record optimization
            self.optimizations_applied += 1
            self.last_optimization[connection_name] = datetime.utcnow()
            
            logger.info(
                f"Applied pool optimization: {connection_name} "
                f"size: {decision.current_pool_size} → {new_size} "
                f"(confidence: {decision.confidence:.1f}, "
                f"cost impact: {decision.estimated_cost_impact:+.1f}%)"
            )
            
        except Exception as e:
            logger.error(f"Failed to apply optimization for {decision.connection_name}: {e}")
    
    async def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        report = {
            "strategy": self.strategy.value,
            "total_pools_monitored": len(self.performance_history),
            "optimizations_applied": self.optimizations_applied,
            "optimizations_considered": self.total_optimizations_considered,
            "success_rate": (self.optimizations_applied / max(self.total_optimizations_considered, 1)) * 100,
            "last_optimization_cycle": datetime.utcnow().isoformat(),
            "targets": {
                "max_response_time_ms": self.targets.max_response_time_ms,
                "min_success_rate": self.targets.min_success_rate,
                "max_saturation_level": self.targets.max_saturation_level,
                "target_efficiency": self.targets.target_efficiency
            },
            "pool_status": {}
        }
        
        # Add per-pool status
        connections = await self.connection_registry.list_connections(active_only=True)
        
        for connection in connections:
            try:
                pool = await self.connection_manager.get_pool(connection.connection_name)
                metrics = await pool.get_stats()
                
                history = self.performance_history.get(connection.connection_name)
                
                report["pool_status"][connection.connection_name] = {
                    "current_size": metrics.total_connections,
                    "saturation_level": metrics.saturation_level,
                    "avg_response_time_ms": metrics.avg_response_time_ms,
                    "success_rate": metrics.query_success_rate,
                    "efficiency": metrics.pool_efficiency,
                    "health_score": metrics.health_score,
                    "last_optimization": self.last_optimization.get(connection.connection_name),
                    "samples_collected": len(history.timestamps) if history else 0
                }
                
            except Exception as e:
                report["pool_status"][connection.connection_name] = {"error": str(e)}
        
        return report
    
    async def force_optimization(self, connection_name: Optional[str] = None) -> List[PoolOptimizationDecision]:
        """Force immediate optimization for specific connection or all connections."""
        async with self.optimization_lock:
            decisions = []
            
            if connection_name:
                # Optimize specific connection
                connection = await self.connection_registry.get_connection_by_name(connection_name)
                if connection:
                    try:
                        pool = await self.connection_manager.get_pool(connection_name)
                        metrics = await pool.get_stats()
                        
                        decision = await self._analyze_pool_optimization(connection, metrics)
                        if decision and decision.should_apply:
                            await self._apply_optimization(decision)
                            decisions.append(decision)
                            
                    except Exception as e:
                        logger.error(f"Failed to force optimize {connection_name}: {e}")
            else:
                # Optimize all connections
                await self._run_optimization_cycle()
                # Return empty list since we don't track individual decisions in the full cycle
            
            return decisions