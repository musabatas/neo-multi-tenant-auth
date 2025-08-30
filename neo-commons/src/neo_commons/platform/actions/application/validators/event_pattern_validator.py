"""Event pattern validator."""

import re
from typing import List
from dataclasses import dataclass


@dataclass
class PatternValidationResult:
    """Result of pattern validation."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    normalized_pattern: str = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class EventPatternValidator:
    """Validator for event patterns used in action subscriptions."""
    
    # Valid pattern formats
    EXACT_PATTERN = r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)*$'  # users.created
    WILDCARD_PATTERN = r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)*(\.\*|\*)$'  # users.*, tenants.created.*
    SINGLE_CHAR_PATTERN = r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)*\?$'  # users.create?
    
    def validate_pattern(self, pattern: str) -> PatternValidationResult:
        """
        Validate an event pattern.
        
        Args:
            pattern: Event pattern to validate
            
        Returns:
            PatternValidationResult with validation details
        """
        errors = []
        warnings = []
        normalized = pattern.strip() if pattern else ""
        
        # Basic validation
        if not pattern:
            errors.append("Event pattern cannot be empty")
            return PatternValidationResult(False, errors, warnings)
        
        if not isinstance(pattern, str):
            errors.append("Event pattern must be a string")
            return PatternValidationResult(False, errors, warnings)
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', '', pattern).lower()
        
        # Length validation
        if len(normalized) > 255:
            errors.append("Event pattern too long (max 255 characters)")
        
        # Validate pattern format
        self._validate_pattern_format(normalized, errors, warnings)
        
        # Check for common mistakes
        self._check_common_mistakes(normalized, errors, warnings)
        
        return PatternValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_pattern=normalized if len(errors) == 0 else None
        )
    
    def validate_patterns(self, patterns: List[str]) -> List[PatternValidationResult]:
        """
        Validate a list of event patterns.
        
        Args:
            patterns: List of patterns to validate
            
        Returns:
            List of validation results
        """
        results = []
        seen_patterns = set()
        
        for pattern in patterns:
            result = self.validate_pattern(pattern)
            
            # Check for duplicates
            if result.normalized_pattern and result.normalized_pattern in seen_patterns:
                result.warnings.append("Duplicate pattern detected")
            elif result.normalized_pattern:
                seen_patterns.add(result.normalized_pattern)
            
            results.append(result)
        
        return results
    
    def _validate_pattern_format(self, pattern: str, errors: List[str], warnings: List[str]):
        """Validate pattern format against allowed formats."""
        # Check if it's an exact match pattern
        if re.match(self.EXACT_PATTERN, pattern):
            return
        
        # Check if it's a wildcard pattern
        if re.match(self.WILDCARD_PATTERN, pattern):
            # Warn about overly broad patterns
            if pattern == "*" or pattern.endswith(".*"):
                warnings.append("Very broad pattern may match too many events")
            return
        
        # Check if it's a single character wildcard
        if re.match(self.SINGLE_CHAR_PATTERN, pattern):
            return
        
        # If none match, it's invalid
        errors.append("Invalid pattern format. Use format: 'domain.action' with optional wildcards (* or ?)")
    
    def _check_common_mistakes(self, pattern: str, errors: List[str], warnings: List[str]):
        """Check for common pattern mistakes."""
        # Check for invalid characters
        if re.search(r'[^a-z0-9._*?]', pattern):
            errors.append("Pattern contains invalid characters. Only lowercase letters, numbers, dots, *, and ? allowed")
        
        # Check for double dots
        if '..' in pattern:
            errors.append("Pattern cannot contain consecutive dots")
        
        # Check for leading/trailing dots
        if pattern.startswith('.') or pattern.endswith('.'):
            errors.append("Pattern cannot start or end with a dot")
        
        # Check for mixing wildcards
        if '*' in pattern and '?' in pattern:
            warnings.append("Mixing * and ? wildcards may be confusing")
        
        # Check for multiple wildcards
        if pattern.count('*') > 1:
            warnings.append("Multiple * wildcards may be overly broad")
        
        # Check for uppercase (should be normalized to lowercase)
        if pattern != pattern.lower():
            warnings.append("Pattern should be lowercase")
        
        # Check for very short patterns
        if len(pattern) < 3 and '*' not in pattern:
            warnings.append("Very short patterns may be too broad")
        
        # Check for reserved words
        reserved_words = ['admin', 'system', 'internal', 'debug']
        parts = pattern.split('.')
        for part in parts:
            if part in reserved_words:
                warnings.append(f"Pattern uses reserved word: {part}")
    
    def test_pattern_match(self, pattern: str, event_type: str) -> bool:
        """
        Test if a pattern matches an event type.
        
        Args:
            pattern: Event pattern with optional wildcards
            event_type: Event type to test against
            
        Returns:
            True if pattern matches event type
        """
        # Normalize inputs
        pattern = pattern.lower().strip()
        event_type = event_type.lower().strip()
        
        # Exact match
        if pattern == event_type:
            return True
        
        # Wildcard matching
        if '*' in pattern:
            # Convert pattern to regex
            regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
            regex_pattern = f'^{regex_pattern}$'
            return re.match(regex_pattern, event_type) is not None
        
        # Single character wildcard
        if '?' in pattern:
            regex_pattern = pattern.replace('.', r'\.').replace('?', '.')
            regex_pattern = f'^{regex_pattern}$'
            return re.match(regex_pattern, event_type) is not None
        
        return False
    
    def suggest_patterns(self, event_types: List[str]) -> List[str]:
        """
        Suggest patterns that would match the given event types.
        
        Args:
            event_types: List of event types to create patterns for
            
        Returns:
            List of suggested patterns
        """
        suggestions = []
        
        if not event_types:
            return suggestions
        
        # Group by domain
        domains = {}
        for event_type in event_types:
            parts = event_type.split('.')
            if len(parts) >= 2:
                domain = parts[0]
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(event_type)
        
        # Generate suggestions
        for domain, events in domains.items():
            if len(events) == 1:
                # Single event - exact match
                suggestions.append(events[0])
            elif len(events) <= 3:
                # Few events - list them individually
                suggestions.extend(events)
            else:
                # Many events - suggest wildcard
                suggestions.append(f"{domain}.*")
        
        return list(set(suggestions))  # Remove duplicates