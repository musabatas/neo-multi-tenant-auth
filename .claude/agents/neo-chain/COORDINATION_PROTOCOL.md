# Neo-Chain Coordination Protocol

> **Quick Start?** See [FILE_COORDINATION_PROTOCOL.md](./FILE_COORDINATION_PROTOCOL.md) for a concise reference guide.

## Overview

This document defines the complete coordination protocol for Neo-Chain agents, ensuring smooth handoffs, consistent state management, and reliable operation tracking. It serves as the authoritative specification for all coordination behaviors.

**IMPORTANT**: Always use time-mcp to get current timestamps and dates when creating reports, branch names, or any time-based identifiers.

## Core Principles

1. **Sequential Execution**: Each agent completes before the next begins
2. **Flexible Starting**: Any agent can be the first in the chain
3. **State Persistence**: All state stored in files (JSON/XML)
4. **Atomic Operations**: Changes are tracked and can be rolled back
5. **Evidence-Based**: Every decision and action is documented
6. **Zero Information Loss**: Complete handoffs between agents
7. **Branch Management**: Each operation creates its own git branch

## File Structure

### Coordination Root
```
.coordination/neo-chain/
├── operations.json              # Master operations list
├── active/                      # Currently active operations
│   └── NC-YYYYMMDD-TYPE-NNN/   # Specific operation
│       ├── manifest.json        # Operation state and tracking
│       ├── reports/             # Agent reports (XML)
│       │   ├── 00-vision.xml
│       │   ├── 01-investigation.xml
│       │   ├── 02-plan.xml
│       │   ├── 03-build.xml
│       │   ├── 04-review.xml
│       │   ├── 05-fix.xml
│       │   ├── 06-tests.xml
│       │   └── 07-documentation.xml
│       └── handoffs/            # Agent handoff records
│           └── TIMESTAMP-from-to.json
└── completed/                   # Archived operations
    └── NC-YYYYMMDD-TYPE-NNN/   # Completed operation files
```

## State Management

### Operations Master File
```json
{
  "version": "1.0",
  "schema": "neo-chain-operations-v1",
  "updated": "2025-01-30T12:00:00Z",
  "active_operation": "NC-20250130-FEAT-001",
  "operations": {
    "NC-20250130-FEAT-001": {
      "type": "feature",
      "description": "User profile management",
      "status": "in_progress",
      "created": "2025-01-30T10:00:00Z",
      "updated": "2025-01-30T12:00:00Z",
      "current_phase": "planning",
      "current_agent": "neo-planner",
      "phases": {
        "vision": {
          "agent": "neo-visioner",
          "status": "complete",
          "started": "2025-01-30T10:00:00Z",
          "completed": "2025-01-30T10:25:00Z",
          "duration": "25m",
          "report": "reports/00-vision.xml"
        },
        "investigation": {
          "agent": "neo-investigator",
          "status": "complete",
          "started": "2025-01-30T10:25:00Z",
          "completed": "2025-01-30T10:55:00Z",
          "duration": "30m",
          "report": "reports/01-investigation.xml"
        },
        "planning": {
          "agent": "neo-planner",
          "status": "in_progress",
          "started": "2025-01-30T10:55:00Z",
          "progress": 65
        }
      }
    }
  }
}
```

### Operation Manifest
```json
{
  "operation_id": "NC-20250130-FEAT-001",
  "version": "1.0",
  "schema": "neo-chain-manifest-v1",
  "current_agent": "neo-planner",
  "current_phase": 2,
  "total_phases": 8,
  "branch": "neo-chain/NC-20250130-FEAT-001",
  "status": "active",
  "metadata": {
    "created": "2025-01-30T10:00:00Z",
    "updated": "2025-01-30T12:00:00Z",
    "estimated_completion": "2025-01-30T18:00:00Z"
  },
  "files": {
    "tracked": [
      {
        "path": "src/features/users/models.py",
        "status": "existing",
        "last_modified": "2025-01-29T15:00:00Z",
        "planned_changes": ["add profile model"]
      }
    ],
    "locked": [],
    "modified": [],
    "created": []
  },
  "progress": {
    "tasks_total": 15,
    "tasks_completed": 0,
    "estimated_effort": "8h",
    "actual_effort": "1.5h"
  },
  "risks": [
    {
      "id": "R001",
      "description": "Database migration complexity",
      "severity": "medium",
      "mitigation": "Phased rollout"
    }
  ]
}
```

## Agent Handoff Protocol

### Handoff Structure
```json
{
  "handoff_id": "HO-20250130-120000-planner-to-builder",
  "timestamp": "2025-01-30T12:00:00Z",
  "from_agent": "neo-planner",
  "to_agent": "neo-builder",
  "operation_id": "NC-20250130-FEAT-001",
  "status": "ready",
  "artifacts": {
    "reports": ["reports/02-plan.xml"],
    "updated_files": ["manifest.json"]
  },
  "summary": {
    "completed": "Created implementation plan with 15 tasks",
    "key_decisions": [
      "Use repository pattern for data access",
      "Implement caching for profile queries"
    ],
    "next_actions": [
      "Implement profile model",
      "Create repository class",
      "Add API endpoints"
    ]
  },
  "validation": {
    "prerequisites_met": true,
    "reports_complete": true,
    "manifest_updated": true
  }
}
```

## Flexible Starting Mode

### Starting from Any Agent
The Neo-Chain system supports flexible starting, allowing any agent to be the first in the chain:

1. **First Agent Responsibilities**
   - Generate operation ID if not provided
   - Create directory structure (`.coordination/neo-chain/active/[OPERATION_ID]/`)
   - Initialize manifest.json with basic structure
   - Create operations.json entry
   - Create git branch: `git checkout -b neo-chain/[OPERATION_ID]`
   - Document that this is the starting point

2. **Missing Context Handling**
   - Document which previous reports are missing
   - Make reasonable assumptions based on available information
   - Note limitations due to missing context
   - Proceed with user requirements as primary guide

3. **Common Starting Points**
   - **Neo-Investigator**: When vision is already clear
   - **Neo-Planner**: When investigation was done manually
   - **Neo-Builder**: When plan exists from previous work
   - **Neo-Reviewer**: For existing code review
   - **Neo-Tester**: For testing existing implementation
   - **Neo-Documenter**: For documenting existing systems

## Phase Transitions

### Entry Criteria
Each agent verifies before starting:

1. **Check if First Agent**
   - Look for existing reports in operation directory
   - If no reports exist, initialize as first agent
   - If reports exist, proceed with normal flow

2. **Previous Phase Complete** (if not first agent)
   - Check `operations.json` for phase status
   - Verify report file exists if expected
   - Validate handoff record if available

3. **Resources Available**
   - Required files accessible
   - No file locks blocking work
   - Dependencies resolved

4. **Context Loaded**
   - Read coordination protocols
   - Read previous reports if available
   - Load operation manifest
   - Understand current state

### Exit Criteria
Each agent ensures before handoff:

1. **Work Complete**
   - All assigned tasks done
   - Report generated (XML)
   - Manifest updated

2. **State Consistent**
   - File tracking accurate
   - Progress metrics updated
   - Risks documented

3. **Handoff Ready**
   - Create handoff record
   - Update operations.json
   - Clear any locks

## File Locking

### Lock Management
```json
// In manifest.json
"files": {
  "locked": [
    {
      "path": "src/features/users/models.py",
      "locked_by": "neo-builder",
      "locked_at": "2025-01-30T12:30:00Z",
      "reason": "Adding profile model"
    }
  ]
}
```

### Lock Rules
1. Only current agent can lock files
2. Locks released on phase completion
3. Emergency unlock after timeout (1 hour)
4. No nested locks allowed

## Error Handling

### Failure Scenarios

1. **Agent Failure**
   ```json
   {
     "error": {
       "agent": "neo-builder",
       "timestamp": "2025-01-30T13:00:00Z",
       "type": "execution_error",
       "message": "Failed to create file",
       "recovery": "retry|skip|abort"
     }
   }
   ```

2. **Validation Failure**
   - Mark phase as "failed"
   - Document failure reason
   - Suggest recovery action
   - Update operations.json

3. **Resource Conflict**
   - File already locked
   - Dependency missing
   - Permission denied

### Recovery Procedures

1. **Retry**: Attempt operation again
2. **Rollback**: Revert to last stable state
3. **Skip**: Continue with next phase
4. **Abort**: Stop operation entirely

## Progress Tracking

### Metrics Collection
```json
{
  "metrics": {
    "phase_duration": {
      "vision": "25m",
      "investigation": "30m"
    },
    "tokens_used": {
      "vision": 15000,
      "investigation": 22000
    },
    "files_analyzed": 45,
    "components_found": 12,
    "tasks_created": 15
  }
}
```

### Progress Reporting
- **CRITICAL**: Real-time updates are MANDATORY, not optional
- Update manifest.json immediately after each significant step
- Update operations.json frequently
- Percentage complete must be updated frequently (not just at completion)
- Include brief status messages with each update
- Example update frequencies by agent:
  - **Investigator**: After each directory/component analyzed
  - **Builder**: After EACH task completion
  - **Reviewer**: After each file reviewed or 10 issues found
  - **Tester**: After each test suite completion
- Estimated time remaining should be recalculated with each update
- Bottleneck identification with immediate reporting

## Quality Gates

### Phase Validation
1. **Vision** (neo-visioner): At least 2 approaches explored
2. **Investigation** (neo-investigator): Key components identified
3. **Planning** (neo-planner): All tasks have estimates
4. **Building** (neo-builder): Code passes linting
5. **Review** (neo-reviewer): Issues categorized by severity
6. **Fixing** (neo-fixer): Critical issues resolved
7. **Testing** (neo-tester): >90% coverage
8. **Documentation** (neo-documenter): All sections complete

### Checkpoint Protocol
```json
{
  "checkpoint": {
    "phase": "building",
    "timestamp": "2025-01-30T14:00:00Z",
    "progress": 50,
    "health": "green|yellow|red",
    "issues": [],
    "next_checkpoint": "2025-01-30T15:00:00Z"
  }
}
```

## Communication Standards

### Report Naming
- `00-vision.xml` - Strategic vision (neo-visioner)
- `01-investigation.xml` - Findings (neo-investigator)
- `02-plan.xml` - Implementation plan (neo-planner)
- `03-build.xml` - Build report (neo-builder)
- `04-review.xml` - Review findings (neo-reviewer)
- `05-fix.xml` - Fix report (neo-fixer)
- `06-tests.xml` - Test results (neo-tester)
- `07-documentation.xml` - Docs created (neo-documenter)

### Status Values
- `pending` - Not started
- `in_progress` - Currently active
- `complete` - Successfully finished
- `failed` - Error occurred
- `skipped` - Bypassed
- `blocked` - Waiting on dependency

## Emergency Procedures

### Manual Intervention
1. Stop current agent
2. Update operations.json
3. Clear file locks
4. Document reason
5. Resume or abort

### State Recovery
```bash
# Check current state
cat .coordination/neo-chain/operations.json

# View manifest
cat .coordination/neo-chain/active/*/manifest.json

# Emergency unlock
echo '{"locked": []}' > temp.json
jq '.files.locked = []' manifest.json > temp.json && mv temp.json manifest.json
```

## Best Practices

1. **Atomic Updates**: Complete all file changes before updating state
2. **Validation First**: Check prerequisites before starting work
3. **Document Everything**: Every decision and action in reports
4. **Clean Handoffs**: Ensure next agent has everything needed
5. **Regular Checkpoints**: Update progress frequently (MANDATORY)
   - Update coordination files after EACH significant action
   - Don't wait until task completion to update progress
   - Include intermediate findings and blockers immediately
   - Use incremental progress percentages (5%, 10%, 15%, etc.)

## Integration Points

### With Git

#### Branch Management
- **Naming Convention**: `neo-chain/[OPERATION_ID]`
- **Creation**: First agent creates branch
- **Example**: `neo-chain/NC-20250130-FEAT-001`
- **Storage**: Branch name stored in manifest.json

#### Commit Strategy
- Commit after each phase completion
- Commit message format: `[AGENT]: Phase description (OPERATION_ID)`
- Example: `neo-builder: Implemented user profile feature (NC-20250130-FEAT-001)`
- Tag completed operations with operation ID

### With CI/CD
- Trigger on phase completion
- Run tests after build phase
- Deploy after documentation

### With Monitoring
- Track operation metrics
- Alert on failures
- Dashboard for progress

This protocol ensures reliable, traceable, and efficient coordination between Neo-Chain agents, enabling systematic development with confidence.