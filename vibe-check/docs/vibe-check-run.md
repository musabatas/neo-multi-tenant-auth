# Vibe-Check Usage Guide

## Overview

Vibe-Check is an AI-powered code review and automated fixing system that analyzes your codebase for issues across six key dimensions: Security, Performance, Maintainability, Consistency, Best Practices, and Code Smell. Each file gets scored 1-5 (5 = excellent, 1 = critical issues).

## Available Commands

### 1. Setup and Population

#### Populate File List
```bash
# Scan entire repository
./vibe-check/scripts/vibe-check populate

# Scan specific directories only
./vibe-check/scripts/vibe-check populate src tests
./vibe-check/scripts/vibe-check populate src/features

# Scan without git (filesystem only)
./vibe-check/scripts/vibe-check populate --no-git
```

### 2. Code Review Commands

#### Review Single File
```bash
# Review next unreviewed file
./vibe-check/scripts/vibe-check review
```

#### Review All Files
```bash
# Review all files with 5-second delay between reviews
./vibe-check/scripts/vibe-check review-all

# Custom delay between reviews (in seconds)
./vibe-check/scripts/vibe-check review-all --delay 10
```

#### Check Review Status
```bash
# Show review progress and statistics
./vibe-check/scripts/vibe-check status

# **NEW: Show fix progress and statistics**
./vibe-check/scripts/vibe-check fix-status
```

### 3. Analysis and Synthesis

#### Generate Synthesis Reports
```bash
# Analyze medium+ severity issues across all categories
./vibe-check/scripts/vibe-check synthesize

# Focus on high severity issues only
./vibe-check/scripts/vibe-check synthesize --severity high

# Focus on specific categories
./vibe-check/scripts/vibe-check synthesize --category security
./vibe-check/scripts/vibe-check synthesize --category performance
./vibe-check/scripts/vibe-check synthesize --category maintainability

# Low severity issues (includes all severity levels)
./vibe-check/scripts/vibe-check synthesize --severity low
```

### 4. **NEW: Automated Code Fixing**

#### Fix Issues by Severity
```bash
# Fix medium+ severity issues (default)
./vibe-check/scripts/vibe-check fix

# Fix only high severity issues
./vibe-check/scripts/vibe-check fix --severity high

# Fix all issues including low severity
./vibe-check/scripts/vibe-check fix --severity low
```

#### Fix Issues by Category
```bash
# Fix security issues only
./vibe-check/scripts/vibe-check fix --category security

# Fix performance issues only
./vibe-check/scripts/vibe-check fix --category performance

# Fix maintainability issues
./vibe-check/scripts/vibe-check fix --category maintainability

# Fix consistency issues
./vibe-check/scripts/vibe-check fix --category consistency

# Fix best practices violations
./vibe-check/scripts/vibe-check fix --category best_practices

# Fix code smell issues
./vibe-check/scripts/vibe-check fix --category code_smell
```

#### Fix Specific Files
```bash
# Fix all issues in a specific file
./vibe-check/scripts/vibe-check fix --file src/common/code_quality.py

# Fix only high severity security issues in specific file
./vibe-check/scripts/vibe-check fix --severity high --category security --file src/api/v1/router.py

# Fix performance issues in specific file
./vibe-check/scripts/vibe-check fix --category performance --file src/core/cache/manager.py
```

#### Backup Control
```bash
# Fix without creating backups (dangerous!)
./vibe-check/scripts/vibe-check fix --no-backup

# Normal fix with automatic backups (default)
./vibe-check/scripts/vibe-check fix
```

## Typical Workflows

### Initial Setup and Complete Review
```bash
# 1. Set up vibe-check (if not already done)
# Follow VIBE_CHECK_SETUP.md instructions

# 2. Populate file list
./vibe-check/scripts/vibe-check populate

# 3. Review all files (this will take time!)
./vibe-check/scripts/vibe-check review-all

# 4. Check completion status
./vibe-check/scripts/vibe-check status

# 5. Generate insights
./vibe-check/scripts/vibe-check synthesize
```

### Security-Focused Workflow
```bash
# 1. Review high-priority security issues
./vibe-check/scripts/vibe-check synthesize --severity high --category security

# 2. Fix critical security issues first
./vibe-check/scripts/vibe-check fix --severity high --category security

# 3. Fix remaining security issues
./vibe-check/scripts/vibe-check fix --category security
```

### Performance Optimization Workflow
```bash
# 1. Identify performance bottlenecks
./vibe-check/scripts/vibe-check synthesize --category performance

# 2. Fix high-impact performance issues
./vibe-check/scripts/vibe-check fix --severity high --category performance

# 3. Address remaining performance issues
./vibe-check/scripts/vibe-check fix --category performance
```

### File-Specific Workflow
```bash
# 1. Focus on a problematic file
./vibe-check/scripts/vibe-check synthesize --severity high

# 2. Fix issues in that specific file
./vibe-check/scripts/vibe-check fix --file src/problematic/file.py

# 3. Verify fixes by re-reviewing (if needed)
# Note: Currently requires manual re-population to re-review
```

### Code Quality Improvement Workflow
```bash
# 1. Address code smells and maintainability
./vibe-check/scripts/vibe-check fix --category code_smell
./vibe-check/scripts/vibe-check fix --category maintainability

# 2. Improve consistency
./vibe-check/scripts/vibe-check fix --category consistency

# 3. Enforce best practices
./vibe-check/scripts/vibe-check fix --category best_practices
```

## Safety Features

### Automatic Backups
- **Default Behavior**: Every fix operation creates timestamped backups
- **Backup Location**: `vibe-check/backups/`
- **Backup Format**: `filename.YYYYMMDD_HHMMSS.backup`
- **Disable**: Use `--no-backup` flag (not recommended)

### **NEW: Smart Issue Tracking**
- **Prevents Re-fixing**: Issues are marked as "fixed" in XML files after successful fixes
- **Fix Timestamps**: Each fix includes an ISO timestamp for tracking
- **Skip Fixed Issues**: Subsequent fix runs automatically skip already-fixed issues
- **Fix Status Tracking**: Use `./vibe-check/scripts/vibe-check fix-status` to see progress

### What Gets Fixed

The fixer understands and applies these types of fixes:

#### Security Fixes
- Add input validation
- Fix SQL injection vulnerabilities
- Implement proper authentication/authorization
- Use environment variables for secrets

#### Performance Fixes
- Replace inefficient algorithms
- Add caching where appropriate
- Fix memory leaks
- Optimize database queries

#### Maintainability Fixes
- Extract long methods into smaller functions
- Add missing documentation
- Improve error handling
- Add comprehensive type hints

#### Consistency Fixes
- Fix import organization
- Apply consistent naming conventions
- Standardize code formatting
- Unify comment styles

#### Best Practices Fixes
- Add proper error handling with custom exceptions
- Implement structured logging
- Add missing type annotations
- Ensure proper resource cleanup

#### Code Smell Fixes
- Remove duplicate code
- Extract magic numbers to constants
- Split god objects/functions
- Reduce tight coupling

## Output Structure

After running commands, you'll find:

```
vibe-check/
├── reviews/
│   ├── _MASTER.json          # Master tracking file
│   ├── _SCRATCHSHEET.md      # Global patterns and conventions
│   └── modules/              # XML review files (mirror repo structure)
├── synthesis/                # Generated analysis reports
│   └── synthesis_medium_20240715_143022.md
├── backups/                  # **NEW: Automatic backups before fixes**
│   ├── code_quality.py.20240715_150123.backup
│   └── router.py.20240715_150145.backup
├── logs/                     # Detailed operation logs
│   ├── review_20240715_142001.log
│   ├── synthesis_20240715_143022.log
│   └── fix_20240715_150123.log      # **NEW: Fix operation logs**
└── prompts/                  # AI instruction templates
    ├── REVIEWER_INSTRUCTIONS.md
    ├── SYNTHESIS_INSTRUCTIONS.md
    └── FIXER_INSTRUCTIONS.md        # **NEW: Fix instruction template**
```

## Important Notes

### Cost Considerations
- **Claude Code Subscription Recommended**: Using API keys can be extremely costly on large projects
- **Token Usage**: Each fix operation processes file content + issues + project context
- **Batch Operations**: Consider fixing by category to group related changes

### Integration with Claude Code
- **Optimized for Claude Code CLI**: The system is specifically designed for use with Claude Code subscriptions
- **Project Context Aware**: Automatically reads `CLAUDE.md` to understand your project's patterns
- **Codebase Conventions**: Follows your established coding patterns and architecture

### Best Practices
1. **Start Small**: Begin with high-severity issues in critical files
2. **Category by Category**: Fix one category at a time for coherent changes
3. **Review Changes**: Always review the fixes applied before committing
4. **Test After Fixes**: Run your test suite after applying fixes
5. **Incremental Approach**: Don't fix everything at once; work in manageable batches

### Limitations
- **Manual Re-review**: Currently requires manual re-population to re-review fixed files
- **Context Dependent**: Some fixes may require manual adjustment based on specific business logic
- **Backup Responsibility**: While automatic backups are created, you should ensure your code is committed to version control

## Getting Help

```bash
# Get general help
./vibe-check/scripts/vibe-check --help

# Get help for specific commands
./vibe-check/scripts/vibe-check fix --help
./vibe-check/scripts/vibe-check fix-status --help
./vibe-check/scripts/vibe-check synthesize --help
./vibe-check/scripts/vibe-check review --help
```

## Example: Complete Security Audit and Fix

```bash
# 1. Generate security-focused analysis
./vibe-check/scripts/vibe-check synthesize --category security

# 2. Fix critical security issues first
./vibe-check/scripts/vibe-check fix --severity high --category security

# 3. **NEW: Check fix progress**
./vibe-check/scripts/vibe-check fix-status

# 4. Review what was fixed (check backups and logs)
ls -la vibe-check/backups/
cat vibe-check/logs/fix_*.log | tail -50

# 5. Fix remaining security issues
./vibe-check/scripts/vibe-check fix --category security

# 6. **NEW: Verify all security issues are fixed**
./vibe-check/scripts/vibe-check fix-status

# 7. Generate updated security report
./vibe-check/scripts/vibe-check synthesize --category security

# 8. Test your application
make test  # or your test command

# 9. Commit changes
git add .
git commit -m "Apply automated security fixes from vibe-check"
```

This enhanced vibe-check system now provides end-to-end code quality management: review, analyze, fix, and verify.