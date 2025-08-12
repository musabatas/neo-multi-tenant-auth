# Neo-Chain Agent System

## Overview

Neo-Chain is a systematic and sequential agent system designed for AI-driven feature development. It provides a clear, structured approach to building software through 8 specialized agents working in perfect coordination.

## What is Neo-Chain?

Neo-Chain consists of 8 specialized agents, each with a specific role in the development process:

1. **Neo-Visioner** - Strategic thinking and creative exploration
2. **Neo-Investigator** - Codebase and database analysis
3. **Neo-Planner** - Detailed implementation planning
4. **Neo-Builder** - Code implementation
5. **Neo-Reviewer** - Quality and security review
6. **Neo-Fixer** - Automated issue resolution
7. **Neo-Tester** - Comprehensive testing
8. **Neo-Documenter** - Documentation creation

## Key Features

### Sequential Excellence
- Each agent builds upon previous work
- Clear handoffs between phases
- No gaps in information transfer
- Complete traceability

### File-Based Coordination
- JSON for state tracking
- XML for detailed reports
- Central manifest for file management
- Clear audit trail

### Practical Focus
- Designed for real development tasks
- Clear, actionable outputs
- Minimal conceptual overhead
- Evidence-based progress

### Systematic Approach
- Strategic vision before implementation
- Thorough investigation before planning
- Quality gates at each phase
- Comprehensive documentation

## How to Use Neo-Chain

### Starting an Operation

#### Standard Flow (Recommended)
Begin with the Neo-Visioner to establish strategic direction:

```bash
Task(
    description="Implement [feature name]",
    prompt="Explore strategic approaches and create a vision for [detailed feature description]",
    subagent_type="neo-visioner"
)
```

#### Flexible Starting (Advanced)
You can start from any agent based on your needs:
- **neo-investigator**: When vision is already clear
- **neo-planner**: When you have requirements ready
- **neo-builder**: When you have a plan to implement
- **neo-reviewer**: For reviewing existing code
- **neo-tester**: For testing existing features
- **neo-documenter**: For documenting existing systems

The first agent will automatically:
- Generate operation ID
- Create directory structure
- Initialize tracking files
- Create git branch: `neo-chain/[OPERATION_ID]`

### The Sequential Flow

Each agent automatically triggers the next in sequence:

1. **Vision Phase** → Strategic exploration and approach selection
2. **Investigation Phase** → Discovery of existing patterns and components
3. **Planning Phase** → Detailed task breakdown and sequencing
4. **Building Phase** → Actual code implementation
5. **Review Phase** → Quality, security, and performance validation
6. **Fixing Phase** → Automated resolution of identified issues
7. **Testing Phase** → Comprehensive test coverage
8. **Documentation Phase** → Complete documentation package

### Operation Naming Convention

**IMPORTANT**: Always use time-mcp to get current timestamps and dates when creating reports, branch names, or any time-based identifiers.

Operations follow the pattern: `NC-YYYYMMDD-TYPE-NNN`

Where:
- `NC` = Neo-Chain
- `YYYYMMDD` = Date
- `TYPE` = FEAT|BUG|REFACTOR|PERF|SEC
- `NNN` = Sequential number

Examples:
- `NC-20250130-FEAT-001` - Feature implementation
- `NC-20250130-BUG-002` - Bug fix
- `NC-20250130-REFACTOR-003` - Code refactoring

## File Coordination Structure

### Master Operations File
```json
// .coordination/neo-chain/operations.json
{
  "version": "1.0",
  "active_operation": "NC-20250130-FEAT-001",
  "operations": {
    "NC-20250130-FEAT-001": {
      "type": "feature",
      "description": "User profile management",
      "status": "in_progress",
      "current_phase": "fixing",
      "phases": {
        "vision": { "status": "complete", "duration": "25m" },
        "investigation": { "status": "complete", "duration": "30m" },
        "planning": { "status": "complete", "duration": "20m" },
        "building": { "status": "complete", "duration": "2h" },
        "review": { "status": "complete", "duration": "30m" },
        "fixing": { "status": "in_progress", "started": "2025-01-30T14:00:00Z" }
      }
    }
  }
}
```

### Operation Manifest
```json
// .coordination/neo-chain/active/NC-*/manifest.json
{
  "operation_id": "NC-20250130-FEAT-001",
  "current_agent": "neo-planner",
  "files": {
    "tracked": ["src/features/users/models.py"],
    "modified": [],
    "created": [],
    "locked": []
  },
  "progress": {
    "estimated_effort": "8h",
    "actual_effort": "2h",
    "completion": 28
  }
}
```

## Example Workflows

### Feature Implementation
```bash
# Start with strategic vision
Task(
    description="Implement notification system",
    prompt="Create strategic vision for a scalable notification system supporting email, SMS, and push notifications",
    subagent_type="neo-visioner"
)

# The chain automatically continues:
# Visioner � explores architectures (pub/sub, queue-based, etc.)
# Investigator � finds existing messaging components
# Planner � creates phased implementation plan
# Builder � implements the code
# Reviewer � ensures quality and security
# Tester � validates all scenarios
# Documenter � creates comprehensive docs
```

### Bug Fix
```bash
Task(
    description="Fix memory leak in Redis cache",
    prompt="Analyze and create a strategy to fix the memory leak in our Redis caching layer",
    subagent_type="neo-visioner"
)
```

### API Development
```bash
Task(
    description="Build REST API for user management",
    prompt="Design and implement a comprehensive REST API for user management with CRUD operations",
    subagent_type="neo-visioner"
)
```

## Agent Outputs

### 1. Vision Report (XML)
```xml
<vision>
  <approaches>
    <approach name="Microservices">
      <pros>Scalability, isolation</pros>
      <cons>Complexity, overhead</cons>
    </approach>
  </approaches>
  <recommendation>Monolithic with modular design</recommendation>
  <risks>Performance under high load</risks>
</vision>
```

### 2. Investigation Report (XML)
```xml
<investigation>
  <findings>
    <components>
      <component path="src/features/users">
        <reusability>high</reusability>
      </component>
    </components>
    <database>
      <table name="users">Existing user table</table>
    </database>
  </findings>
</investigation>
```

### 3. Implementation Plan (XML)
```xml
<implementation_plan>
  <phases>
    <phase number="1" name="Foundation">
      <tasks>
        <task id="T001">
          <title>Create profile model</title>
          <effort>2h</effort>
        </task>
      </tasks>
    </phase>
  </phases>
</implementation_plan>
```

## Monitoring Operations

### Check Active Operation
```bash
cat .coordination/neo-chain/operations.json | grep active_operation
```

### View Current Progress
```bash
cat .coordination/neo-chain/active/*/manifest.json | grep current_agent
```

### List All Reports
```bash
ls .coordination/neo-chain/active/*/reports/
```

## Best Practices

### DO
- Start with vision for new features
- Let each agent complete its work
- Review reports before proceeding
- Trust the sequential process
- Use appropriate operation types

### DON'T
- Skip the visioner phase
- Manually edit coordination files
- Interrupt operations in progress
- Mix operation types
- Bypass agent recommendations

## Troubleshooting

### Common Issues

**Agent seems stuck**
- Check the manifest.json for current status
- Review the last report for blocking issues
- Ensure previous agent completed successfully

**Files locked**
- Check manifest.json "locked" array
- Wait for current agent to complete
- Use emergency unlock if needed

**Operation failed**
- Review error in latest report
- Check handoff notes for issues
- Restart from last successful phase

## Integration with Other Systems

### Version Control

#### Branch Management
- **Automatic Creation**: First agent creates branch automatically
- **Naming Convention**: `neo-chain/[OPERATION_ID]`
- **Example**: `neo-chain/NC-20250130-FEAT-001`

```bash
# Neo-Chain creates branches automatically
git checkout -b neo-chain/NC-20250130-FEAT-001

# After each phase
git add -A
git commit -m "[agent]: Phase complete (NC-20250130-FEAT-001)"

# After documentation completes
git commit -m "feat: implement user profiles (NC-20250130-FEAT-001)"
```

### CI/CD
- Vision includes deployment considerations
- Planner includes CI/CD tasks
- Builder follows CI/CD patterns
- Tester includes pipeline tests

## Why Neo-Chain?

### Advantages
- **Systematic**: Never miss important steps
- **Traceable**: Complete history of decisions
- **Quality-Focused**: Multiple validation gates
- **Practical**: Designed for real development
- **Clear**: Simple coordination model

### When to Use
- New feature development
- Complex bug fixes
- System refactoring
- API development
- Any task requiring systematic approach

### Comparison with Other Systems

**Neo-Chain vs DevChain**
- Neo-Chain: Simpler, practical focus
- DevChain: Enterprise-grade, more formal

**Neo-Chain vs SOC**
- Neo-Chain: Development-specific
- SOC: Military-grade, any operation type

**Neo-Chain vs SDEAS**
- Neo-Chain: Sequential only
- SDEAS: Supports parallel execution

## Success Metrics

Operations are measured by:
- **Completion Rate**: % of operations finished
- **Quality Score**: Issues found in review/testing
- **Time Efficiency**: Actual vs estimated effort
- **Documentation Quality**: Completeness score
- **Reusability**: Components discovered and reused

Remember: Neo-Chain is about **systematic excellence**. By following the chain, you ensure nothing is missed, quality is maintained, and knowledge is preserved. Let the agents guide you to successful implementation.