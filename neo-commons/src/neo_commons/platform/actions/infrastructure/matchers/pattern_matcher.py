"""Event pattern matching engine for action subscriptions."""

import re
import fnmatch
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class PatternMatcher(ABC):
    """Abstract base class for pattern matching."""
    
    @abstractmethod
    async def matches(self, pattern: str, event_type: str) -> bool:
        """Check if a pattern matches an event type."""
        pass


class GlobPatternMatcher(PatternMatcher):
    """Glob-style pattern matcher using fnmatch."""
    
    async def matches(self, pattern: str, event_type: str) -> bool:
        """
        Check if a glob pattern matches an event type.
        
        Supports wildcards:
        - * matches any sequence of characters
        - ? matches any single character
        - [seq] matches any character in seq
        - [!seq] matches any character not in seq
        
        Examples:
        - 'users.*' matches 'users.created', 'users.updated'
        - 'users.create?' matches 'users.created', 'users.created1'
        - 'users.[cu]*' matches 'users.created', 'users.updated'
        """
        try:
            return fnmatch.fnmatch(event_type.lower(), pattern.lower())
        except Exception:
            return False


class RegexPatternMatcher(PatternMatcher):
    """Regex pattern matcher for advanced patterns."""
    
    def __init__(self):
        self._compiled_patterns: Dict[str, re.Pattern] = {}
    
    async def matches(self, pattern: str, event_type: str) -> bool:
        """
        Check if a regex pattern matches an event type.
        
        Supports full regex syntax with anchoring:
        - '^users\\.(created|updated)$' matches exactly 'users.created' or 'users.updated'
        - 'users\\..*' matches anything starting with 'users.'
        """
        try:
            # Get or compile pattern
            compiled_pattern = self._get_compiled_pattern(pattern)
            return bool(compiled_pattern.match(event_type))
        except Exception:
            return False
    
    def _get_compiled_pattern(self, pattern: str) -> re.Pattern:
        """Get compiled regex pattern, using cache."""
        if pattern not in self._compiled_patterns:
            # Add anchors if not present
            if not pattern.startswith('^'):
                pattern = '^' + pattern
            if not pattern.endswith('$'):
                pattern = pattern + '$'
            
            self._compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE)
        
        return self._compiled_patterns[pattern]


class ConditionMatcher:
    """Matcher for JSONB conditions on event data."""
    
    async def matches(self, conditions: Optional[Dict[str, Any]], event_data: Dict[str, Any]) -> bool:
        """
        Check if event data matches the given conditions.
        
        Supports basic condition matching:
        - {"user_type": "premium"} - exact match
        - {"age": {"$gte": 18}} - comparison operators
        - {"$and": [{"status": "active"}, {"verified": true}]} - logical operators
        """
        if not conditions:
            return True
        
        try:
            return await self._evaluate_condition(conditions, event_data)
        except Exception:
            return False
    
    async def _evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate a single condition against data."""
        for key, value in condition.items():
            if key.startswith('$'):
                # Logical operators
                if not await self._evaluate_logical_operator(key, value, data):
                    return False
            else:
                # Field conditions
                if not await self._evaluate_field_condition(key, value, data):
                    return False
        
        return True
    
    async def _evaluate_logical_operator(self, operator: str, value: Any, data: Dict[str, Any]) -> bool:
        """Evaluate logical operators."""
        if operator == '$and':
            if not isinstance(value, list):
                return False
            return all(await self._evaluate_condition(cond, data) for cond in value)
        
        elif operator == '$or':
            if not isinstance(value, list):
                return False
            return any(await self._evaluate_condition(cond, data) for cond in value)
        
        elif operator == '$not':
            return not await self._evaluate_condition(value, data)
        
        return False
    
    async def _evaluate_field_condition(self, field: str, condition: Any, data: Dict[str, Any]) -> bool:
        """Evaluate field-level conditions."""
        # Get field value from data (support nested fields with dot notation)
        field_value = self._get_nested_value(data, field)
        
        if isinstance(condition, dict) and any(k.startswith('$') for k in condition.keys()):
            # Comparison operators
            return await self._evaluate_comparison_operators(field_value, condition)
        else:
            # Exact match
            return field_value == condition
    
    async def _evaluate_comparison_operators(self, field_value: Any, operators: Dict[str, Any]) -> bool:
        """Evaluate comparison operators."""
        for op, target_value in operators.items():
            if op == '$eq':
                if field_value != target_value:
                    return False
            elif op == '$ne':
                if field_value == target_value:
                    return False
            elif op == '$gt':
                if not (field_value is not None and field_value > target_value):
                    return False
            elif op == '$gte':
                if not (field_value is not None and field_value >= target_value):
                    return False
            elif op == '$lt':
                if not (field_value is not None and field_value < target_value):
                    return False
            elif op == '$lte':
                if not (field_value is not None and field_value <= target_value):
                    return False
            elif op == '$in':
                if not isinstance(target_value, list) or field_value not in target_value:
                    return False
            elif op == '$nin':
                if not isinstance(target_value, list) or field_value in target_value:
                    return False
            elif op == '$exists':
                if bool(field_value is not None) != bool(target_value):
                    return False
            elif op == '$regex':
                if not isinstance(field_value, str):
                    return False
                try:
                    if not re.search(target_value, field_value, re.IGNORECASE):
                        return False
                except re.error:
                    return False
        
        return True
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value


class EventActionMatcher:
    """Main event-action matching engine."""
    
    def __init__(self):
        self.glob_matcher = GlobPatternMatcher()
        self.regex_matcher = RegexPatternMatcher()
        self.condition_matcher = ConditionMatcher()
    
    async def find_matching_actions(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        subscriptions: List,
        actions: List
    ) -> List:
        """
        Find actions that match an event based on subscriptions.
        
        Args:
            event_type: Type of the event
            event_data: Event payload data
            subscriptions: List of EventActionSubscription entities
            actions: List of Action entities
            
        Returns:
            List of matching Action entities sorted by priority
        """
        matching_actions = []
        
        # Create lookup map for actions
        action_map = {action.id: action for action in actions}
        
        for subscription in subscriptions:
            # Check if action exists and is active
            action = action_map.get(subscription.action_id)
            if not action or not action.is_active or not action.is_healthy:
                continue
            
            # Check event pattern matching
            pattern_matches = False
            for pattern in subscription.event_patterns:
                if await self._matches_pattern(pattern, event_type):
                    pattern_matches = True
                    break
            
            if not pattern_matches:
                continue
            
            # Check additional conditions
            if not await self.condition_matcher.matches(subscription.conditions, event_data):
                continue
            
            matching_actions.append(action)
        
        # Sort by priority (higher priority first)
        return sorted(matching_actions, key=lambda a: a.priority, reverse=True)
    
    async def _matches_pattern(self, pattern: str, event_type: str) -> bool:
        """Check if a pattern matches an event type."""
        # Determine pattern type and use appropriate matcher
        if self._is_regex_pattern(pattern):
            return await self.regex_matcher.matches(pattern, event_type)
        else:
            return await self.glob_matcher.matches(pattern, event_type)
    
    def _is_regex_pattern(self, pattern: str) -> bool:
        """
        Determine if a pattern is a regex pattern.
        
        Heuristics:
        - Contains regex special characters (not covered by glob)
        - Starts with ^ or ends with $
        - Contains character classes like \d, \w, \s
        """
        regex_indicators = [
            pattern.startswith('^'),
            pattern.endswith('$'),
            '\\d' in pattern,
            '\\w' in pattern,
            '\\s' in pattern,
            '\\.' in pattern,
            '+' in pattern,
            '{' in pattern and '}' in pattern,
            '(' in pattern and ')' in pattern
        ]
        
        return any(regex_indicators)