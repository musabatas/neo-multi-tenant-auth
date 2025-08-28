"""Cache priority value object.

ONLY priority levels - priority levels for cache eviction with influence
on eviction algorithms and per-namespace priority policies.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from enum import IntEnum


class PriorityLevel(IntEnum):
    """Cache priority levels for eviction decisions.
    
    Higher numeric values indicate higher priority (less likely to be evicted).
    """
    
    LOW = 1       # Low priority - first to be evicted
    MEDIUM = 5    # Medium priority - standard caching
    HIGH = 10     # High priority - protected from eviction
    CRITICAL = 20 # Critical priority - almost never evicted


@dataclass(frozen=True)
class CachePriority:
    """Cache priority value object.
    
    Priority levels for cache eviction with influence on eviction algorithms
    and per-namespace priority policies.
    
    Features:
    - Numeric priority values for algorithm compatibility
    - Predefined priority levels for consistency
    - Comparison operations for sorting
    - Eviction resistance calculation
    """
    
    level: PriorityLevel
    
    @classmethod
    def low(cls) -> "CachePriority":
        """Create low priority (first to be evicted)."""
        return cls(PriorityLevel.LOW)
    
    @classmethod
    def medium(cls) -> "CachePriority":
        """Create medium priority (standard caching)."""
        return cls(PriorityLevel.MEDIUM)
    
    @classmethod
    def high(cls) -> "CachePriority":
        """Create high priority (protected from eviction)."""
        return cls(PriorityLevel.HIGH)
    
    @classmethod
    def critical(cls) -> "CachePriority":
        """Create critical priority (almost never evicted)."""
        return cls(PriorityLevel.CRITICAL)
    
    @classmethod
    def from_int(cls, value: int) -> "CachePriority":
        """Create priority from integer value."""
        # Find closest matching priority level
        levels = list(PriorityLevel)
        closest = min(levels, key=lambda x: abs(x.value - value))
        return cls(closest)
    
    def get_numeric_value(self) -> int:
        """Get numeric priority value."""
        return self.level.value
    
    def get_eviction_resistance(self) -> float:
        """Get eviction resistance as percentage (0.0 to 1.0)."""
        # Map priority levels to resistance percentages
        max_priority = max(level.value for level in PriorityLevel)
        return self.level.value / max_priority
    
    def is_low(self) -> bool:
        """Check if priority is low."""
        return self.level == PriorityLevel.LOW
    
    def is_medium(self) -> bool:
        """Check if priority is medium."""
        return self.level == PriorityLevel.MEDIUM
    
    def is_high(self) -> bool:
        """Check if priority is high."""
        return self.level == PriorityLevel.HIGH
    
    def is_critical(self) -> bool:
        """Check if priority is critical."""
        return self.level == PriorityLevel.CRITICAL
    
    def should_evict_before(self, other: "CachePriority") -> bool:
        """Check if this priority should be evicted before other."""
        return self.level.value < other.level.value
    
    def can_replace(self, other: "CachePriority") -> bool:
        """Check if this priority can replace other in cache."""
        return self.level.value >= other.level.value
    
    def __lt__(self, other: "CachePriority") -> bool:
        """Less than comparison for sorting."""
        return self.level.value < other.level.value
    
    def __le__(self, other: "CachePriority") -> bool:
        """Less than or equal comparison."""
        return self.level.value <= other.level.value
    
    def __gt__(self, other: "CachePriority") -> bool:
        """Greater than comparison."""
        return self.level.value > other.level.value
    
    def __ge__(self, other: "CachePriority") -> bool:
        """Greater than or equal comparison."""
        return self.level.value >= other.level.value
    
    def __str__(self) -> str:
        """String representation."""
        return self.level.name.lower()
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"CachePriority({self.level.name}, {self.level.value})"