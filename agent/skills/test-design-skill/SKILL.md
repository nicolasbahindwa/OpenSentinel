---
name: test-design-skill
description: Design focused tests and edge cases that validate expected behavior, catch regressions, and expose hidden assumptions
---

# Test Design Skill

Use this skill when adding or reviewing tests for behavior changes.

## Workflow

1. Define the expected behavior.
2. Cover the happy path.
3. Add edge cases and failure modes.
4. Include at least one regression-oriented case when fixing a bug.
5. Prefer tests that validate user-visible behavior over implementation details.

## Rules

- Keep tests minimal but high-signal.
- Avoid redundant cases that do not increase confidence.
- Name tests after the behavior they protect.

End of Skill.
