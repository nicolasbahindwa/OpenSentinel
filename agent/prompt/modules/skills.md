# Skills

Skills are loaded from `/skills/` via `SkillsMiddleware`.

## Usage Pattern

- At runtime, use the discovered skill list (name + description + path).
- Read a skill's `SKILL.md` only when the task requires it.
- Follow the skill workflow exactly once selected.

## Objective

Use skills to keep responses consistent while minimizing prompt token usage.

