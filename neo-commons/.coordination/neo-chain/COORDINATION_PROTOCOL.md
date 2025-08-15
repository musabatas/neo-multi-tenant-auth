# Neo-Chain Coordination Protocol

## Overview
Neo-Chain is a multi-agent system for complex software development operations requiring coordination between specialized agents.

## Agent Chain Structure
1. **neo-visioner**: Strategic analysis and direction setting
2. **neo-investigator**: Codebase analysis and component discovery (THIS AGENT)
3. **neo-planner**: Implementation strategy and task planning
4. **neo-builder**: Code implementation and integration

## Coordination Files
- `.coordination/neo-chain/active/[OPERATION_ID]/manifest.json` - Operation tracking
- `.coordination/neo-chain/active/[OPERATION_ID]/operations.json` - Progress tracking  
- `.coordination/neo-chain/active/[OPERATION_ID]/reports/` - Agent reports

## Agent Communication
Each agent creates an XML report with findings and passes context to the next agent in the chain.

## Operation ID Format
`NC-YYYYMMDD-TYPE-NNN` where:
- NC = Neo-Chain
- YYYYMMDD = Date
- TYPE = Operation type (INVESTIGATE, MIGRATE, REFACTOR, etc.)
- NNN = Sequential number

## File Tracking
All agents must update manifest.json with discovered/modified files for coordination across the chain.