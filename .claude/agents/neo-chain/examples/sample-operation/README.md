# Sample Neo-Chain Operation: User Profile Management

This example demonstrates a complete Neo-Chain operation for implementing a user profile management feature.

## Operation Details

- **Operation ID**: NC-20250130-FEAT-001
- **Type**: Feature Implementation
- **Description**: Add user profile management with bio, avatar, and preferences
- **Duration**: ~6 hours (simulated)

## Phase Progression

### 1. Vision Phase (neo-visioner)
- **Duration**: 25 minutes
- **Output**: `00-vision.xml`
- **Key Decisions**:
  - Chose JSONB storage for flexibility
  - Decided on extending existing user model
  - Planned for future social features

### 2. Investigation Phase (neo-investigator)
- **Duration**: 30 minutes
- **Output**: `01-investigation.xml`
- **Key Findings**:
  - Existing user model in `src/features/users/models.py`
  - Repository pattern already implemented
  - Redis caching available

### 3. Planning Phase (neo-planner)
- **Duration**: 20 minutes
- **Output**: `02-plan.xml`
- **Tasks Created**: 8 tasks across 3 phases
- **Estimated Effort**: 5 hours

### 4. Building Phase (neo-builder)
- **Duration**: 2 hours
- **Output**: `03-build.xml`
- **Files Created**:
  - `src/features/users/models/profile.py`
  - `src/features/users/services/profile_service.py`
  - `src/features/users/routers/profile.py`

### 5. Review Phase (neo-reviewer)
- **Duration**: 30 minutes
- **Output**: `04-review.xml`
- **Issues Found**: 1 critical, 2 high, 2 medium, 3 low
- **Security Score**: 7/10

### 6. Fixing Phase (neo-fixer)
- **Duration**: 45 minutes
- **Output**: `05-fix.xml`
- **Issues Fixed**: 1 critical, 2 high, 1 medium
- **Fix Rate**: 75%

### 7. Testing Phase (neo-tester)
- **Duration**: 1 hour
- **Output**: `06-tests.xml`
- **Coverage**: 94%
- **Tests**: 25 unit, 10 integration, 3 E2E

### 8. Documentation Phase (neo-documenter)
- **Duration**: 45 minutes
- **Output**: `07-documentation.xml`
- **Docs Created**:
  - API documentation
  - User guide
  - Architecture decision record

## File Structure

```
sample-operation/
├── README.md                    # This file
├── manifest.json               # Operation tracking
├── operations.json             # Master operations file
├── reports/
│   ├── 00-vision.xml          # Strategic vision
│   ├── 01-investigation.xml   # Investigation findings
│   ├── 02-plan.xml           # Implementation plan
│   ├── 03-build.xml          # Build report
│   ├── 04-review.xml         # Review findings
│   ├── 05-fix.xml            # Fix report
│   ├── 06-tests.xml          # Test results
│   └── 07-documentation.xml  # Documentation report
└── handoffs/
    ├── 20250130-102500-visioner-to-investigator.json
    ├── 20250130-105500-investigator-to-planner.json
    ├── 20250130-111500-planner-to-builder.json
    ├── 20250130-131500-builder-to-reviewer.json
    ├── 20250130-141500-reviewer-to-fixer.json
    ├── 20250130-144500-fixer-to-tester.json
    └── 20250130-154500-tester-to-documenter.json
```

## Key Learnings

1. **Vision First**: Starting with strategic thinking prevented rework
2. **Investigation Value**: Found 80% of needed components already existed
3. **Planning Accuracy**: Actual effort within 10% of estimates
4. **Quality Gates**: Review caught critical security issue
5. **Auto-Fixing**: Fixer resolved 75% of issues automatically
6. **Test Coverage**: Achieved 94% coverage with minimal effort

## How to Use This Example

1. Study the report progression to understand agent outputs
2. Review handoff files to see information transfer
3. Check manifest.json for file tracking patterns
4. Use as template for your own operations

## Running a Similar Operation

```bash
Task(
    description="Implement user profile management",
    prompt="Create a strategic vision for user profile management including bio, avatar, and preferences",
    subagent_type="neo-visioner"
)
```

The system will automatically progress through all phases, creating similar artifacts.