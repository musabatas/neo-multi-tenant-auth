---
title: Global Project Patterns
entry_count: 5
last_updated: 2025-08-10
---

1. All services use async patterns (async/await) for I/O operations
2. Project requires UUIDv7 for all UUID generation (time-ordered IDs)
3. Function length limit is 50 lines per project standards
4. Router registration uses dual pattern (with and without API prefix)
5. Production flag controls API documentation endpoint visibility
