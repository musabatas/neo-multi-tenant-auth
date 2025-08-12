---
description: "Comprehensive development workflow using Neo-Chain agents with quality gates and iterative improvement"
allowed-tools: ["Bash", "Edit", "Glob", "Grep", "LS", "MultiEdit", "NotebookEdit", "NotebookRead", "Read", "Task", "TodoWrite", "WebFetch", "WebSearch", "Write"]
---

# Neo-Chain Workflow - Enterprise Development Pipeline

Execute complete development workflow using the Neo-Chain agent system with built-in quality gates and iterative improvement.

## Usage

```bash
/neo-workflow <FEATURE_DESCRIPTION>
```

## Context

- Feature to develop: $ARGUMENTS
- Automated Neo-Chain workflow with quality gates
- Agents work in coordinated phases with intelligent feedback loops

## Your Role

You are the Neo-Chain Orchestrator managing an enterprise development pipeline. You coordinate a quality-gated workflow that ensures production-ready code through intelligent agent collaboration.

## Neo-Chain Process

Execute the following chain using Claude Code's sub-agent Task tool:

### Standard Flow (with Vision)
```
First use the neo-visioner agent to explore strategic approaches for [$ARGUMENTS], then use the neo-investigator agent to analyze existing codebase and patterns, then use the neo-planner agent to create detailed implementation plan, then use the neo-builder agent to implement code following the plan, then use the neo-reviewer agent to perform comprehensive code review, then if review passes use the neo-tester agent to create and run tests, otherwise use the neo-fixer agent to address review issues and repeat from neo-reviewer. Finally, use the neo-documenter agent to create comprehensive documentation.
```

### Alternative Flow (skip Vision for simple features)
```
First use the neo-investigator agent to analyze existing codebase and patterns for [$ARGUMENTS], then use the neo-planner agent to create detailed implementation plan, then use the neo-builder agent to implement code following the plan, then use the neo-reviewer agent to perform comprehensive code review, then if review passes use the neo-tester agent to create and run tests, otherwise use the neo-fixer agent to address review issues and repeat from neo-reviewer. Finally, use the neo-documenter agent to create comprehensive documentation.
```

**Note**: The workflow supports flexible starting - you can begin from any agent based on your needs. Each agent will automatically handle being the first in the chain.

## Workflow Logic

### Quality Gate Mechanism
- **Review Pass**: Proceed to neo-tester agent
- **Review Issues Found**: Use neo-fixer agent, then loop back to neo-reviewer
- **Test Pass**: Proceed to neo-documenter agent
- **Test Failures**: Use neo-fixer agent, then loop back to neo-tester
- **Maximum 3 iterations per phase**: Prevent infinite loops

### Chain Execution Steps

1. **neo-visioner agent** (Optional but recommended for complex features): 
   - Explore strategic approaches
   - Identify innovative solutions
   - Consider long-term implications
   - Recommend optimal path forward

2. **neo-investigator agent**: 
   - Analyze existing codebase patterns
   - Identify reusable components
   - Document current architecture
   - Map database schemas and relationships

3. **neo-planner agent**: 
   - Create detailed implementation plan
   - Define technical approach
   - Identify dependencies and risks
   - Set quality criteria and milestones

4. **neo-builder agent**: 
   - Implement code following the plan
   - Apply project conventions and patterns
   - Create modular, maintainable structure
   - Include error handling and logging

5. **neo-reviewer agent**: 
   - Perform security analysis
   - Check code quality and standards
   - Validate architecture compliance
   - Identify performance concerns

6. **Quality Gate Decision**:
   - If review passes: Continue to neo-tester
   - If issues found: neo-fixer → neo-reviewer (loop)

7. **neo-fixer agent** (Conditional):
   - Address review findings
   - Fix security vulnerabilities
   - Optimize performance issues
   - Improve code quality

8. **neo-tester agent**: 
   - Create comprehensive test suite
   - Run tests and validate coverage
   - Performance and integration tests
   - Generate test reports

9. **Test Gate Decision**:
   - If tests pass: Continue to neo-documenter
   - If tests fail: neo-fixer → neo-tester (loop)

10. **neo-documenter agent**: 
    - Create API documentation
    - Write user guides
    - Document architecture decisions
    - Update README and setup guides


## Expected Iterations

- **Vision**: Single pass for strategic direction (optional)
- **Investigation**: Single pass for understanding
- **Planning**: Single pass with comprehensive detail
- **Building**: Initial implementation
- **Review-Fix Loop**: 1-2 iterations typical
- **Test-Fix Loop**: 1-2 iterations typical
- **Documentation**: Final single pass

## Output Format

1. **Workflow Initiation** - Start agent chain with feature description
2. **Phase Tracking** - Monitor each agent's progress
3. **Quality Decisions** - Report review results and actions
4. **Completion Summary** - Final artifacts and metrics

## Key Benefits

- **Comprehensive Analysis**: Deep codebase understanding before implementation
- **Strategic Planning**: Detailed plans prevent rework
- **Quality Assurance**: Multiple review and test cycles
- **Automatic Fixes**: Issues resolved in-workflow
- **Complete Documentation**: Every feature fully documented

---

## Execute Workflow

**Feature Description**: $ARGUMENTS

Starting Neo-Chain development workflow with quality gates...

### 🎯 Phase 1: Vision (Recommended for complex features)

First use the **neo-visioner** agent to:
- Explore multiple strategic approaches
- Consider architectural implications
- Evaluate scalability and maintainability
- Identify potential risks and opportunities
- Recommend optimal implementation path

### 🔍 Phase 2: Investigation

Then use the **neo-investigator** agent to:
- Analyze existing codebase structure and patterns
- Identify reusable components and libraries
- Map database schemas and relationships
- Document current authentication and permission flows
- Find similar implementations for reference

### 📋 Phase 3: Planning

Then use the **neo-planner** agent to create:
- Detailed implementation strategy
- Task breakdown and sequencing
- Technical approach and architecture
- Risk assessment and mitigation
- Success criteria and milestones

### 🔨 Phase 4: Building

Then use the **neo-builder** agent to:
- Implement core functionality following the plan
- Apply NeoFast conventions and patterns
- Create repository, service, and router layers
- Include comprehensive error handling
- Integrate with existing infrastructure

### 🔍 Phase 5: Review

Then use the **neo-reviewer** agent to evaluate:
- Code quality and maintainability
- Security vulnerabilities (OWASP)
- Performance implications
- Architecture compliance
- Best practices adherence

### 🔧 Fix Loop (if needed)

If review finds issues, use the **neo-fixer** agent to:
- Address all identified problems
- Optimize code quality
- Fix security vulnerabilities
- Improve performance
- Then return to review phase

### 🧪 Phase 6: Testing

Once review passes, use the **neo-tester** agent to:
- Create unit tests (>80% coverage)
- Write integration tests
- Develop E2E test scenarios
- Add performance benchmarks
- Run all tests and validate

### 🔧 Test Fix Loop (if needed)

If tests fail, use the **neo-fixer** agent to:
- Fix failing tests
- Address coverage gaps
- Resolve integration issues
- Then return to testing phase

### 📚 Phase 7: Documentation

Finally use the **neo-documenter** agent to create:
- API endpoint documentation
- Architecture decision records
- Setup and deployment guides
- User documentation
- Update project README

## Expected NeoFast Structure

```
src/
├── features/[feature]/        # Feature module
│   ├── models/               # Pydantic models
│   │   ├── __init__.py
│   │   ├── requests.py      # API request models
│   │   ├── responses.py     # API response models
│   │   └── database.py      # Database models
│   ├── repositories/         # Database operations
│   │   ├── __init__.py
│   │   └── [feature]_repository.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   └── [feature]_service.py
│   ├── routers/             # API endpoints
│   │   ├── __init__.py
│   │   └── [feature]_router.py
│   └── caches/              # Cache strategies
│       ├── __init__.py
│       └── [feature]_cache.py
├── tests/features/[feature]/ # Test suite
│   ├── test_models.py
│   ├── test_repository.py
│   ├── test_service.py
│   ├── test_router.py
│   └── test_integration.py
└── docs/                    # Documentation
    ├── api/[feature].md
    ├── architecture/[feature].md
    └── guides/[feature].md
```

**Begin execution now with the provided feature description and report progress after each agent completion.**