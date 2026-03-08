# OpenSentinel Skills

Skills are loaded from `/skills/` by DeepAgents `SkillsMiddleware`.

## Loading Model

- Startup: only skill metadata (name, description, path) is loaded.
- Runtime: full instructions are read only when the agent selects a skill.

## Required Layout

Each skill must be a directory containing `SKILL.md`:

```text
agent/skills/
  mood-skill/
    SKILL.md
  reflection-skill/
    SKILL.md
```

## Why This Exists

This keeps prompt tokens low while preserving discoverability of all skills.

