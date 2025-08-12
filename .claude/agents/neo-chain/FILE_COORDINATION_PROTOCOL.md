# Neo-Chain Quick Reference

A concise reference for developers using the Neo-Chain coordination system.

> **For complete protocol details, see [COORDINATION_PROTOCOL.md](./COORDINATION_PROTOCOL.md)**

## File Structure at a Glance

```
.coordination/neo-chain/
├── operations.json              # Master operations tracker
├── active/
│   └── NC-*/                   # Active operation
│       ├── manifest.json       # Operation state
│       ├── reports/*.xml       # Agent outputs
│       └── handoffs/*.json     # Transitions
└── completed/                   # Archived operations
```

## Essential Files

| File | Purpose | Updated By |
|------|---------|------------|
| `operations.json` | Tracks all operations & current status | All agents |
| `manifest.json` | Operation state, files, progress | Current agent |
| `reports/*.xml` | Agent work outputs | Each agent |
| `handoffs/*.json` | Agent transition records | Completing agent |

## Report Sequence

1. `00-vision.xml` → Strategic approaches (neo-visioner)
2. `01-investigation.xml` → Codebase findings (neo-investigator)
3. `02-plan.xml` → Implementation tasks (neo-planner)
4. `03-build.xml` → Code changes (neo-builder)
5. `04-review.xml` → Quality issues (neo-reviewer)
6. `05-fix.xml` → Fixes applied (neo-fixer)
7. `06-tests.xml` → Test results (neo-tester)
8. `07-documentation.xml` → Docs created (neo-documenter)

## Quick Commands

```bash
# Current operation
grep active_operation .coordination/neo-chain/operations.json

# Current phase
jq .current_phase .coordination/neo-chain/active/*/manifest.json

# View reports
ls -la .coordination/neo-chain/active/*/reports/

# Check locks
jq .files.locked .coordination/neo-chain/active/*/manifest.json
```

## Key Rules

✅ **DO**: Let agents manage all coordination files  
✅ **DO**: Check file locks before manual edits  
✅ **DO**: Review previous reports before starting  

❌ **DON'T**: Manually edit coordination files  
❌ **DON'T**: Skip phases without documentation  
❌ **DON'T**: Modify locked files  

---
*For schemas, protocols, error handling, and detailed specifications → [COORDINATION_PROTOCOL.md](./COORDINATION_PROTOCOL.md)*