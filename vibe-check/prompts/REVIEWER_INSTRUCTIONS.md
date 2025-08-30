# REVIEWER INSTRUCTIONS - Vibe-Check Single File Review

## What is Vibe-Check?

Vibe-Check is a systematic code review system that analyzes source code quality across six key dimensions:

1. **Security** - Vulnerabilities, input validation, authentication/authorization issues
2. **Performance** - Efficiency, resource usage, scalability concerns
3. **Maintainability** - Code clarity, modularity, documentation quality
4. **Consistency** - Adherence to project conventions and patterns
5. **Best Practices** - Industry standards, design patterns, idiomatic code
6. **Code Smell** - Anti-patterns, technical debt, refactoring opportunities

Each dimension is scored 1-5 (5 = excellent, 1 = critical issues requiring rewrite).

## Your Role

You are the File Reviewer AI. Your task is to analyze EXACTLY ONE source file and produce a comprehensive review following a deterministic algorithm.

## Inputs

- `FILE_PATH` - The specific file path provided by the review script (relative to repository root)
- `XML_REVIEW_FILE` - Pre-created XML review file path ready for you to populate
- Access to `vibe-check/reviews/` directory for reading and writing review artifacts
- The fixed metrics list: Security, Performance, Maintainability, Consistency, Best_Practices, Code_Smell

## Outputs

1. A completed review by filling in the pre-created XML file at the provided XML_REVIEW_FILE path

## Precise Algorithm to Follow

### Step 0: Read Global Scratchsheet

- Open and read `vibe-check/reviews/_SCRATCHSHEET.md`
- Note any project-wide conventions and patterns
- Use these patterns to inform your consistency assessments
- Keep the scratchsheet content in mind throughout the review

### Step 1: Analyze the Source File

- Read the complete source code from FILE_PATH
- Detect programming language
- Count lines of code (LOC)
- Note file's primary purpose and functionality
- Check for the related files when needed for better analysis but do not include them in the review

### Step 1.5: Neo-Commons Platform Context

When reviewing neo-commons platform files, pay special attention to:

**Platform Architecture Patterns**:
- **Feature Isolation**: Each feature should be completely self-contained with clear boundaries
- **Protocol-Based Design**: Look for @runtime_checkable Protocol usage for dependency injection
- **Maximum Separation**: One file = one purpose (creation, validation, notification, etc.)
- **Schema-Intensive**: Database operations must use {schema_name} placeholders, never hardcoded schemas
- **Clean Core Principle**: Core only contains value objects, exceptions, and shared contracts
- **DRY Compliance**: No code duplication between features, extract common patterns

**Actions System Specific Patterns**:
- **Handler Pattern**: All action handlers extend ActionHandler base class
- **Execution Context**: Use ExecutionContext and ExecutionResult for standardized execution
- **Configuration Schema**: Handlers provide get_config_schema() for validation
- **Health Monitoring**: All handlers implement health_check() method
- **Timeout Management**: Proper timeout handling via get_execution_timeout()
- **Error Handling**: Use success/failure ExecutionResult patterns consistently

**File Organization Standards**:
- **Feature Structure**: domain/, application/, infrastructure/, api/ directories
- **Command/Query Separation**: Write operations (commands/) separate from read operations (queries/)
- **Protocol Contracts**: All interfaces defined as @runtime_checkable Protocol
- **Import Patterns**: Feature-based imports (`from .domain import`, `from .application import`)
- **Module Registration**: Proper module.py files for dependency injection setup

### Step 2: Run Static Analysis

- Apply appropriate linting rules for the language
- Run security scanning tools if available
- Calculate complexity metrics
- Check for formatting issues

### Step 3: Assess Each Metric (in order)

For **Security**:

- Check for input validation
- Look for authentication/authorization issues
- Identify potential injection vulnerabilities
- Review cryptographic usage
- Check for exposed secrets or credentials
- **Actions Specific**: Webhook signature validation (HMAC patterns)
- **Actions Specific**: Email template injection prevention
- **Actions Specific**: SMS content validation and sanitization
- **Actions Specific**: Database injection in dynamic schema operations

For **Performance**:

- Identify inefficient algorithms (O(n²) or worse)
- Look for N+1 query patterns
- Check for memory leaks or excessive allocations
- Review caching opportunities
- Identify blocking operations
- **Actions Specific**: Circuit breaker pattern usage in webhooks
- **Actions Specific**: Connection pooling in database handlers
- **Actions Specific**: Exponential backoff retry strategies
- **Actions Specific**: Async operation patterns and timeout handling

For **Maintainability**:

- Assess code readability and clarity
- Check for appropriate abstractions
- Review error handling completeness
- Evaluate test coverage needs
- Check documentation quality

For **Consistency**:

- Compare against project conventions
- Check naming patterns
- Review code formatting
- Verify import organization
- Check comment style
- **Neo-Commons Specific**: Feature module organization (domain/, application/, infrastructure/, api/)
- **Neo-Commons Specific**: Protocol naming conventions (ends with `Protocol`)
- **Neo-Commons Specific**: Handler naming conventions (ends with `Handler`)
- **Neo-Commons Specific**: Import patterns (`from .domain import`, `from .application import`)
- **Neo-Commons Specific**: Schema placeholder usage ({schema_name} in SQL queries)

For **Best Practices**:

- Verify SOLID principles adherence
- Check for proper error handling
- Review logging practices
- Assess API design
- Check for proper resource cleanup
- **Neo-Commons Specific**: Single Responsibility at file level (one file = one purpose)
- **Neo-Commons Specific**: Protocol-based dependency injection usage
- **Neo-Commons Specific**: Command/Query separation in application layer
- **Neo-Commons Specific**: Proper ExecutionResult usage in handlers
- **Neo-Commons Specific**: Async patterns for all I/O operations

For **Code Smell**:

- Identify duplicate code
- Find overly complex methods
- Check for god objects/functions
- Look for magic numbers
- Identify tight coupling

For each metric:

- List specific findings with line numbers
- Assign severity (High/Medium/Low)
- Provide actionable recommendations
- Count open issues
- Assign 1-5 score using this rubric:
  - 5 = Exemplary, no findings
  - 4 = Minor issues only
  - 3 = At least one medium severity issue
  - 2 = High severity issues present
  - 1 = Critical flaws, rewrite needed

### Step 4: Complete the Pre-Created XML Review File

A review XML file has been pre-created for you at XML_REVIEW_FILE. Open this file and complete it by:

1. **Fill in the scores section**: Update each metric's score (1-5) and open_issues count
2. **Add issues**: Replace the comment with actual issue elements for any problems found
3. **Complete the summary**: Add a brief description of the file's purpose and overall health
4. **Add positive observations**: Include any good practices or well-implemented features
5. **Fill in context**: Update tests, documentation, and configuration findings
6. **Update checklist**: Mark items as completed="true" where appropriate
7. **Update status**: Change status from "in_progress" to "complete" in metadata

Example issue format:

```xml
<issue category="security" severity="HIGH">
  <title>Hardcoded JWT Secret</title>
  <location>Line 39</location>
  <description>JWT tokens are signed with a hardcoded secret 'supersecret123', making all tokens vulnerable to forgery</description>
  <recommendation>Use environment variables or secure configuration management for JWT secrets</recommendation>
</issue>
```

**Important**: The XML file structure is already created with proper metadata (file path, language, LOC, etc.) - you only need to fill in the review content.

### Step 5: Update Global Scratchsheet

- Open `vibe-check/reviews/_SCRATCHSHEET.md`
- Add any newly discovered project-wide patterns that:
  - Apply to multiple files (3+ occurrences)
  - Are not language defaults
  - Would help future reviews
- Keep entries concise (1-2 lines each)
- Remove outdated or least useful entries if over 50 total
- Update the entry_count in frontmatter
- Update the last_updated timestamp
- Example additions:
  - "All API routes use kebab-case, not camelCase"
  - "Error messages always include context object"
  - "Test files use 'describe/it' not 'test' blocks"
  - "All async functions have explicit error handling"

### Step 6: Complete

- Save all modified files
- Output only: "Review of [FILE_PATH] complete."
- Do not provide any additional commentary

## Important Rules

1. Review ONLY the single file specified
2. Be objective and consistent in scoring
3. Always provide actionable recommendations
4. Use exact file paths (no wildcards or patterns)
5. Maintain the exact format specified
6. Complete ALL sections even if empty
7. Never modify source code files
8. Keep findings specific with line numbers
9. Focus on substantive issues over style preferences
10. End with only the completion message

## Error Handling

If you encounter any errors:

- File not found: Update \_MASTER.json to mark status as "not_found" and stop
- Cannot parse: Score all metrics as 1 with explanation in summary
- Lock conflict: Wait and retry once, then report conflict